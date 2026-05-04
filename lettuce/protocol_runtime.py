from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable

from .handlers import HandlerDefinition, discover_handlers, handlers_for_stream


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_HANDLER_COMMAND_ENV = "LETTUCE_HANDLER_COMMAND"
_HANDLER_TIMEOUT_ENV = "LETTUCE_HANDLER_TIMEOUT_SECONDS"
_DEFAULT_PROVIDER_COMMAND = "python3 -m lettuce.provider_adapter"
_DEFAULT_HANDLER_TIMEOUT_SECONDS = 240
_HANDLER_TEMPLATE_TYPES = {
    "lens": "lens",
    "router": "router",
    "handler": "handler",
}
_HANDLER_TEMPLATE_DIRS = {
    "lens": "lenses",
    "router": "routers",
    "handler": "helpers",
}
_AGENT_INSTRUCTIONS_FILENAME = "LETTUCE_AGENT.md"


@dataclass(frozen=True)
class StreamEvent:
    stream: str
    id: str
    timestamp: str
    frontmatter: dict[str, Any]
    body: str
    path: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "stream": self.stream,
            "id": self.id,
            "timestamp": self.timestamp,
            "frontmatter": dict(self.frontmatter),
            "body": self.body,
        }


@dataclass(frozen=True)
class PublishResult:
    stream: str
    path: str
    title: str
    status: str = "published"
    review_id: str | None = None
    target_stream: str | None = None


@dataclass(frozen=True)
class ReviewRecord:
    id: str
    status: str
    path: str
    target_stream: str
    title: str
    handler_id: str
    source_event: str
    body: str
    frontmatter: dict[str, Any]


@dataclass(frozen=True)
class HandlerRunResult:
    handler_id: str
    event_id: str
    skipped: bool
    publishes: list[PublishResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    committed: bool = False
    duration_ms: int = 0


@dataclass(frozen=True)
class RunOnceResult:
    repo: str
    stream: str
    handlers: int
    events: int
    runs: list[HandlerRunResult]


@dataclass(frozen=True)
class RuntimeStatus:
    repo: str
    identity: RepoIdentity
    handlers: int
    streams: dict[str, int]
    checkpoints: dict[str, int]
    log_entries: int
    agent_instructions_path: str | None = None
    sources: dict[str, Any] = field(default_factory=dict)
    onboarding: dict[str, Any] = field(default_factory=dict)
    last_log: dict[str, Any] | None = None
    freshness: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceImportResult:
    source_type: str
    event_path: str
    title: str
    source: str


@dataclass(frozen=True)
class DirectIngestResult:
    event_path: str
    title: str
    source: str
    consent_basis: str


@dataclass(frozen=True)
class EmailIngestResult:
    event_path: str
    title: str
    source: str
    consent_basis: str


@dataclass(frozen=True)
class SourceConfigResult:
    source_type: str
    source_id: str
    config_path: str
    stream: str
    status: str
    access_status: str
    access_owner: str


@dataclass(frozen=True)
class SubscriptionConfigResult:
    subscription_path: str
    remote: str
    stream: str
    status: str


@dataclass(frozen=True)
class RepoIdentity:
    repo_type: str
    org: str
    owner_kind: str
    operator: str
    role_agent_id: str | None
    permission_basis: str
    visibility: str


@dataclass(frozen=True)
class ExportedStream:
    stream: str
    description: str
    sensitivity: str
    owner: str
    allowed_readers: list[str]
    allowed_writers: list[str]
    review_required: bool


@dataclass(frozen=True)
class SourceRecord:
    id: str
    source_type: str
    name: str
    stream: str
    access_status: str
    poll: str
    sample_policy: str
    privacy_notes: str
    setup_next_action: str
    path: str
    body: str


@dataclass(frozen=True)
class SubscriptionRecord:
    id: str
    remote: str
    stream: str
    local_stream: str
    policy: str
    path: str
    body: str


@dataclass(frozen=True)
class HandlerInvocation:
    system: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class HandlerInvoker:
    command: str | None = None

    def invoke(self, handler: HandlerDefinition, event: StreamEvent, repo: Path) -> dict[str, Any]:
        invocation = _handler_invocation(handler, event, repo)
        return self._invoke_command(invocation)

    def _invoke_command(self, invocation: HandlerInvocation) -> dict[str, Any]:
        timeout_seconds = _handler_timeout_seconds()
        try:
            completed = subprocess.run(
                self.command,
                input=json.dumps({"system": invocation.system, "payload": invocation.payload}),
                text=True,
                shell=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"handler command timed out after {timeout_seconds}s") from exc
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"handler command exited {completed.returncode}")
        return json.loads(completed.stdout)


def _handler_timeout_seconds() -> int:
    raw = os.environ.get(_HANDLER_TIMEOUT_ENV, "").strip()
    if not raw:
        return _DEFAULT_HANDLER_TIMEOUT_SECONDS
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_HANDLER_TIMEOUT_SECONDS


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:72].strip("-") or "event"


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"null", "Null", "NULL", "~", "None"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",")]
    return value.strip("\"'")


def _parse_simple_frontmatter(frontmatter: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = _parse_scalar(value)
    return data


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _parse_simple_frontmatter(path.read_text(encoding="utf-8"))


def _require_lettuce_repo(repo: Path) -> None:
    if not (repo / "lettuce.yml").exists():
        raise FileNotFoundError(f"not a Lettuce repo: {repo}. Run lettuce init first.")


def _format_frontmatter_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _render_markdown_event(frontmatter: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {_format_frontmatter_value(value)}")
    lines.extend(["---", "", body.strip(), ""])
    return "\n".join(lines)


def _repo_relative_path(repo: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo.resolve()))


def _timestamp_for_filename(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H-%M-%SZ")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _validate_relative_stream_path(path: str, *, field_name: str) -> str:
    value = path.strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    if value.startswith("/") or value.startswith("../") or "/../" in value or value == "..":
        raise ValueError(f"{field_name} must stay within the Lettuce repo")
    normalized = Path(value)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"{field_name} must stay within the Lettuce repo")
    return value


def _validate_subscription_local_stream(path: str) -> str:
    value = _validate_relative_stream_path(path, field_name="subscription local_stream")
    if not value.startswith("streams/shared/"):
        raise ValueError("subscription local_stream must stay under streams/shared/")
    return value


def _validate_subscription_policy(policy: str) -> str:
    value = policy.strip()
    if not value:
        raise ValueError("subscription policy is required")
    if value.startswith("allow_streams="):
        allowed = value.split("=", 1)[1].strip()
        if not allowed:
            raise ValueError("subscription allow_streams policy requires a path")
        if allowed != "streams/shared/*":
            raise ValueError("subscription allow_streams policy must stay within streams/shared/*")
    return value


def _resolve_local_subscription_remote(remote: str) -> Path | None:
    stripped = remote.strip()
    if not stripped:
        return None
    candidate = Path(stripped).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if stripped.startswith(".") or stripped.startswith(".."):
        return candidate.resolve()
    return None


def _parse_lettuce_yaml(text: str) -> dict[str, Any]:
    config: dict[str, Any] = {}
    exports: list[dict[str, Any]] = []
    current_export: dict[str, Any] | None = None
    in_exports = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if stripped == "exports:":
            in_exports = True
            config["exports"] = exports
            current_export = None
            continue
        if indent == 0:
            in_exports = False
            current_export = None
            if ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            config[key.strip()] = _parse_scalar(value)
            continue
        if not in_exports:
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            current_export = {}
            exports.append(current_export)
            if item:
                if ":" not in item:
                    raise ValueError("invalid export entry in lettuce.yml")
                key, value = item.split(":", 1)
                current_export[key.strip()] = _parse_scalar(value)
            continue
        if current_export is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        current_export[key.strip()] = _parse_scalar(value)
    if "exports" not in config and "exports: []" in text:
        config["exports"] = []
    return config


def _read_lettuce_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _parse_lettuce_yaml(path.read_text(encoding="utf-8"))


_VALID_REPO_TYPES = {"personal", "company_hub"}
_VALID_OWNER_KINDS = {"human_operator", "role_agent"}
_VALID_PERMISSION_BASES = {"github-user", "github-app", "machine-user"}


def _normalize_repo_identity(config: dict[str, Any]) -> RepoIdentity:
    repo_type = str(config.get("type") or "personal").strip() or "personal"
    owner_kind = str(config.get("owner_kind") or "human_operator").strip() or "human_operator"
    operator = str(config.get("operator") or "").strip()
    role_agent_raw = config.get("role_agent_id")
    role_agent_id = None if role_agent_raw is None else str(role_agent_raw).strip() or None
    permission_basis = str(config.get("permission_basis") or "github-user").strip() or "github-user"
    visibility = str(config.get("visibility") or "private").strip() or "private"
    org = str(config.get("org") or "").strip()

    if repo_type not in _VALID_REPO_TYPES:
        raise ValueError(f"invalid lettuce.yml type: {repo_type}")
    if owner_kind not in _VALID_OWNER_KINDS:
        raise ValueError(f"invalid lettuce.yml owner_kind: {owner_kind}")
    if permission_basis not in _VALID_PERMISSION_BASES:
        raise ValueError(f"invalid lettuce.yml permission_basis: {permission_basis}")
    if owner_kind == "role_agent" and not role_agent_id:
        raise ValueError("role_agent repos must set role_agent_id in lettuce.yml")
    if owner_kind == "human_operator":
        role_agent_id = None
    return RepoIdentity(
        repo_type=repo_type,
        org=org,
        owner_kind=owner_kind,
        operator=operator,
        role_agent_id=role_agent_id,
        permission_basis=permission_basis,
        visibility=visibility,
    )


def _validate_export_stream_path(path: str) -> str:
    value = _validate_relative_stream_path(path, field_name="export stream")
    if not value.startswith("streams/shared/"):
        raise ValueError("export stream must stay under streams/shared/")
    return value


def _normalize_exported_streams(config: dict[str, Any]) -> list[ExportedStream]:
    raw_exports = config.get("exports") or []
    if not isinstance(raw_exports, list):
        raise ValueError("lettuce.yml exports must be a list")

    def _as_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and not value.strip():
            return []
        return [str(value).strip()]

    exports: list[ExportedStream] = []
    for index, item in enumerate(raw_exports, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"lettuce.yml export #{index} must be a mapping")
        exports.append(
            ExportedStream(
                stream=_validate_export_stream_path(str(item.get("stream") or "")),
                description=str(item.get("description") or "").strip(),
                sensitivity=str(item.get("sensitivity") or "").strip(),
                owner=str(item.get("owner") or "").strip(),
                allowed_readers=_as_string_list(item.get("allowed_readers")),
                allowed_writers=_as_string_list(item.get("allowed_writers")),
                review_required=bool(item.get("review_required", False)),
            )
        )
    return exports


def read_repo_identity(repo_path: str | Path) -> RepoIdentity:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    return _normalize_repo_identity(_read_lettuce_yaml(repo / "lettuce.yml"))


def read_exported_streams(repo_path: str | Path) -> list[ExportedStream]:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    config = _read_lettuce_yaml(repo / "lettuce.yml")
    _normalize_repo_identity(config)
    return _normalize_exported_streams(config)


def _verify_remote_export_policy(remote: str, stream: str) -> None:
    remote_repo = _resolve_local_subscription_remote(remote)
    if remote_repo is None:
        return

    def _policy_error(reason: str) -> ValueError:
        return ValueError(
            f"subscription denied by remote export policy: remote_repo={remote_repo} stream={stream} reason={reason}"
        )

    if not remote_repo.exists():
        raise _policy_error("remote repo path does not exist")
    if not remote_repo.is_dir():
        raise _policy_error("remote repo path is not a directory")

    config_path = remote_repo / "lettuce.yml"
    if not config_path.exists():
        raise _policy_error("missing lettuce.yml")

    try:
        exports = read_exported_streams(remote_repo)
    except (FileNotFoundError, ValueError) as exc:
        raise _policy_error(str(exc)) from exc

    if not any(export.stream == stream for export in exports):
        raise _policy_error("stream is not explicitly exported")


def _render_lettuce_config(
    *,
    org: str,
    operator: str,
    default_model: str,
    created_at: str,
    repo_type: str,
    owner_kind: str,
    role_agent_id: str | None,
    permission_basis: str,
    visibility: str,
    exports: list[dict[str, Any]] | None,
) -> str:
    identity = _normalize_repo_identity(
        {
            "type": repo_type,
            "org": org,
            "owner_kind": owner_kind,
            "operator": operator,
            "role_agent_id": role_agent_id,
            "permission_basis": permission_basis,
            "visibility": visibility,
        }
    )
    normalized_exports = _normalize_exported_streams({"exports": exports or []})
    lines = [
        "lettuce_version: 0.1.0",
        f"type: {identity.repo_type}",
        f"owner_kind: {identity.owner_kind}",
        f"operator: {identity.operator}",
        f"org: {identity.org}",
        f"role_agent_id: {identity.role_agent_id if identity.role_agent_id is not None else 'null'}",
        f"permission_basis: {identity.permission_basis}",
        f"visibility: {identity.visibility}",
        f"created_at: {created_at}",
        f"default_model: {default_model}",
    ]
    if not normalized_exports:
        lines.append("exports: []")
        return "\n".join(lines) + "\n"
    lines.append("exports:")
    for export in normalized_exports:
        lines.append(f"  - stream: {export.stream}")
        lines.append(f"    description: {export.description}")
        lines.append(f"    sensitivity: {export.sensitivity}")
        lines.append(f"    owner: {export.owner}")
        lines.append(f"    allowed_readers: {_format_frontmatter_value(export.allowed_readers)}")
        lines.append(f"    allowed_writers: {_format_frontmatter_value(export.allowed_writers)}")
        lines.append(f"    review_required: {_format_frontmatter_value(export.review_required)}")
    return "\n".join(lines) + "\n"


def _default_exports_for_repo_type(repo_type: str) -> list[dict[str, Any]]:
    if repo_type != "company_hub":
        return []
    return [
        {
            "stream": "streams/shared/decisions",
            "description": "Accepted company decisions and policy updates curated for shared reuse.",
            "sensitivity": "internal",
            "owner": "company-hub",
            "allowed_readers": [],
            "allowed_writers": [],
            "review_required": True,
        },
        {
            "stream": "streams/shared/customers",
            "description": "Curated customer and account summaries safe to share across operators and agents.",
            "sensitivity": "internal",
            "owner": "company-hub",
            "allowed_readers": [],
            "allowed_writers": [],
            "review_required": True,
        },
        {
            "stream": "streams/shared/incidents",
            "description": "Accepted incident summaries, impact notes, and follow-up status.",
            "sensitivity": "internal",
            "owner": "company-hub",
            "allowed_readers": [],
            "allowed_writers": [],
            "review_required": True,
        },
        {
            "stream": "streams/shared/projects",
            "description": "Curated project updates, milestones, and cross-team status worth sharing.",
            "sensitivity": "internal",
            "owner": "company-hub",
            "allowed_readers": [],
            "allowed_writers": [],
            "review_required": True,
        },
    ]


def _hub_scaffold_files() -> dict[str, str]:
    return {
        "streams/shared/decisions/.gitkeep": "",
        "streams/shared/customers/.gitkeep": "",
        "streams/shared/incidents/.gitkeep": "",
        "streams/shared/projects/.gitkeep": "",
        "docs/company-hub/README.md": """# Company Hub Convention

This optional repo is the org-level coordination point for curated shared context.

Use it for:

- exported shared streams under `streams/shared/*`
- accepted company decisions and durable facts
- stream discovery metadata and ownership/policy notes
- approved summaries that help multiple operators or role agents

Do not use it for:

- every operator's raw inbox or transcripts
- direct mirrors into `brain/*`
- a centralized all-seeing company dump

Shared pulls and mirrors must only write under `streams/shared/*`.
""",
        "docs/company-hub/stream-catalog.md": """# Shared Stream Catalog

Use this file to document what the company hub intentionally shares, who curates it, and any extra policy notes.

## Shared Streams

- `streams/shared/decisions`: accepted company decisions, policy changes, and durable org-level facts
- `streams/shared/customers`: curated customer/account summaries and cross-functional relationship context
- `streams/shared/incidents`: accepted incident summaries, impact, mitigation, and follow-up status
- `streams/shared/projects`: curated project updates, milestones, risks, and owner-visible status

Each stream should stay curated and provenance-preserving. Raw inbox or transcript dumps do not belong here by default.
""",
        "docs/company-hub/owners-and-policies.md": """# Owners And Policies

Record stream owners, review expectations, and any narrow sharing rules here.

Suggested reminders:

- keep hub streams curated rather than exhaustive
- preserve provenance on imported or mirrored events
- require review for accepted org-level decisions and facts unless the operator explicitly narrows that rule
- keep remote pulls scoped to `streams/shared/*`
""",
    }


def _default_handler_md(handler_id: str, name: str, handler_type: str, subscribes: str, publishes: str, body: str) -> str:
    return f"""---
id: {handler_id}
name: {name}
type: {handler_type}
version: 0.1.0
subscribes:
  - stream: {subscribes}
publishes:
  - stream: {publishes}
    mode: append
triggers:
  - on: new-event
batch: false
timeout: 60s
---

{body.strip()}
"""


def add_handler(
    repo_path: str | Path,
    template: str,
    *,
    handler_id: str | None = None,
    name: str | None = None,
    subscribes: str = "streams/inbox/direct",
    publishes: str | None = None,
    body: str | None = None,
    model: str = "",
    commit: bool = False,
) -> Path:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    handler_type = _HANDLER_TEMPLATE_TYPES.get(template.strip().lower())
    if handler_type is None:
        known = ", ".join(sorted(_HANDLER_TEMPLATE_TYPES))
        raise ValueError(f"unknown handler template: {template}. Expected one of: {known}")
    resolved_id = _slugify(handler_id or f"custom-{handler_type}")
    resolved_name = name or resolved_id.replace("-", " ").title()
    resolved_publishes = publishes or ("brain/general" if handler_type != "router" else "brain/decisions")
    resolved_body = body or (
        f"You are {resolved_name}. Read the event and return JSON with publish actions only when this {handler_type} finds useful signal. "
        'Return {"skip": true, "notes": ["why"]} when nothing should be published.'
    )
    text = _default_handler_md(resolved_id, resolved_name, handler_type, subscribes, resolved_publishes, resolved_body)
    if model.strip():
        text = text.replace("timeout: 60s\n---", f"timeout: 60s\nmodel: {model.strip()}\n---")
    path = repo / "handlers" / _HANDLER_TEMPLATE_DIRS[handler_type] / f"{resolved_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"handler already exists: {path}")
    path.write_text(text, encoding="utf-8")
    parse_check = discover_handlers(path.parent)
    if not any(handler.id == resolved_id for handler in parse_check):
        path.unlink(missing_ok=True)
        raise ValueError(f"created handler could not be parsed: {path}")
    if commit:
        _git_commit(repo, [path], f"handler: {resolved_id}")
    return path


def init_repo(
    repo_path: str | Path,
    *,
    org: str,
    operator: str,
    default_model: str = "claude-sonnet-4",
    repo_type: str = "personal",
    owner_kind: str = "human_operator",
    role_agent_id: str | None = None,
    permission_basis: str = "github-user",
    visibility: str = "private",
    exports: list[dict[str, Any]] | None = None,
    initialize_git: bool = True,
) -> list[Path]:
    repo = Path(repo_path).expanduser().resolve()
    repo.mkdir(parents=True, exist_ok=True)
    created_at = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    resolved_exports = exports if exports is not None else _default_exports_for_repo_type(repo_type)
    files: dict[str, str] = {
        "lettuce.yml": _render_lettuce_config(
            org=org,
            operator=operator,
            default_model=default_model,
            created_at=created_at,
            repo_type=repo_type,
            owner_kind=owner_kind,
            role_agent_id=role_agent_id,
            permission_basis=permission_basis,
            visibility=visibility,
            exports=resolved_exports,
        ),
        ".gitignore": ".lettuce/\n",
        "handlers/lenses/default-lens.md": _default_handler_md(
            "default-lens",
            "Default Lens",
            "lens",
            "streams/inbox/direct",
            "brain/general",
            "You surface anything notable in the incoming signal. Return JSON with publishes or {\"skip\": true}.",
        ),
        "handlers/lenses/discovery-lens.md": _default_handler_md(
            "discovery-lens",
            "Discovery Lens",
            "lens",
            "streams/inbox/direct",
            "brain/discovery",
            (
                "Look for product, market, strategy, category, or business opportunity signal. "
                "Publish only when the signal reveals a reusable discovery insight beyond one account's immediate next step. "
                "Skip pure sales follow-up, procurement, or security-review requests unless they expose a broader product/market pattern."
            ),
        ),
        "handlers/lenses/accounts-lens.md": _default_handler_md(
            "accounts-lens",
            "Accounts Lens",
            "lens",
            "streams/inbox/direct",
            "brain/customers",
            (
                "Look for named customer, prospect, account, relationship, and follow-up context. "
                "Publish only when there is a specific account, organization, person, deal, risk, or relationship action worth preserving. "
                "Skip general product feedback, aggregate design-partner themes, and onboarding UX notes that do not name a specific account or follow-up."
            ),
        ),
        "handlers/routers/brain-router.md": _default_handler_md(
            "brain-router",
            "Brain Router",
            "router",
            "brain/general",
            "brain/decisions",
            "Decide whether interpreted signal should become durable brain context. Return JSON publish actions or skip.",
        ),
        "handlers/routers/linear-router.md": _default_handler_md(
            "linear-router",
            "Linear Router",
            "router",
            "brain/general",
            "streams/outbox/linear",
            "Decide whether a brain entry should become a Linear triage issue. In v0 local runs, publish an outbox event instead of calling Linear directly.",
        ),
        "handlers/helpers/inbox-normalizer.md": _default_handler_md(
            "inbox-normalizer",
            "Inbox Normalizer",
            "handler",
            "streams/inbox/raw",
            "streams/inbox/direct",
            "Normalize raw signal into a clean inbox event for downstream lenses.",
        ),
        "brain/.gitkeep": "",
        "brain/general/.gitkeep": "",
        "brain/discovery/.gitkeep": "",
        "brain/customers/.gitkeep": "",
        "brain/decisions/.gitkeep": "",
        "reviews/pending/.gitkeep": "",
        "reviews/approved/.gitkeep": "",
        "reviews/declined/.gitkeep": "",
        "onboarding/setup/.gitkeep": "",
        "sources/.gitkeep": "",
        "subscriptions/.gitkeep": "",
        "streams/inbox/direct/.gitkeep": "",
        "streams/inbox/raw/.gitkeep": "",
        "streams/inbox/email/.gitkeep": "",
        "streams/inbox/transcripts/.gitkeep": "",
        "streams/outbox/linear/.gitkeep": "",
    }
    if repo_type == "company_hub":
        files.update(_hub_scaffold_files())
    written: list[Path] = []
    for relative_path, content in files.items():
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            written.append(path)
    state_dir = repo / ".lettuce"
    state_dir.mkdir(exist_ok=True)
    checkpoint_path = state_dir / "checkpoints.json"
    if not checkpoint_path.exists():
        checkpoint_path.write_text("{}\n", encoding="utf-8")
    log_path = state_dir / "runtime.log"
    if not log_path.exists():
        log_path.write_text("", encoding="utf-8")
    instructions_path = _write_agent_instructions(repo)
    if instructions_path not in written:
        written.append(instructions_path)
    if initialize_git:
        _ensure_git_repo(repo)
        tracked = [path for path in written if ".lettuce" not in path.parts]
        if tracked:
            _git_commit(repo, tracked, "lettuce init scaffold")
    return written


def add_stream_event(
    repo_path: str | Path,
    *,
    stream: str = "streams/inbox/direct",
    title: str,
    body: str,
    source: str = "direct",
    metadata: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
    commit: bool = False,
) -> Path:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    created_at = (timestamp or now_utc()).replace(microsecond=0)
    event_id = f"{_timestamp_for_filename(created_at)}-{_slugify(title)}"
    frontmatter = {
        "id": event_id,
        "timestamp": created_at.isoformat().replace("+00:00", "Z"),
        "source": source,
        "title": title,
    }
    for key, value in (metadata or {}).items():
        clean_key = str(key).strip()
        if clean_key and clean_key not in {"id", "timestamp", "source", "title"}:
            frontmatter[clean_key] = value
    path = repo / stream / f"{event_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown_event(frontmatter, body), encoding="utf-8")
    if commit:
        _git_commit(repo, [path], f"event: {event_id}")
    return path


def _infer_title_from_text(text: str, fallback: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title
        if line:
            return line[:80]
    return fallback


def import_source_event(
    repo_path: str | Path,
    source_type: str,
    *,
    input_path: str | Path | None = None,
    text: str | None = None,
    title: str | None = None,
    stream: str = "streams/inbox/direct",
    source: str | None = None,
    commit: bool = False,
) -> SourceImportResult:
    resolved_source_type = source_type.strip().lower()
    if resolved_source_type not in {"file", "stdin"}:
        raise ValueError("source_type must be one of: file, stdin")
    if resolved_source_type == "file":
        if input_path is None:
            raise ValueError("file source requires input_path")
        path = Path(input_path).expanduser().resolve()
        body = path.read_text(encoding="utf-8")
        resolved_title = title or _infer_title_from_text(body, path.stem)
        resolved_source = source or f"file:{path.name}"
        metadata = {
            "source_type": "file",
            "source_path": str(path),
        }
    else:
        body = text if text is not None else ""
        if not body.strip():
            raise ValueError("stdin source requires text")
        resolved_title = title or _infer_title_from_text(body, "stdin signal")
        resolved_source = source or "stdin"
        metadata = {"source_type": "stdin"}
    event_path = add_stream_event(
        repo_path,
        stream=stream,
        title=resolved_title,
        body=body,
        source=resolved_source,
        metadata=metadata,
        commit=commit,
    )
    return SourceImportResult(
        source_type=resolved_source_type,
        event_path=str(event_path),
        title=resolved_title,
        source=resolved_source,
    )


def ingest_email_signal(
    repo_path: str | Path,
    *,
    subject: str,
    body: str,
    consent_basis: str,
    source: str | None = None,
    stream: str = "streams/inbox/direct",
    title: str | None = None,
    message_id: str | None = None,
    thread_id: str | None = None,
    email_from: str | None = None,
    email_to: str | None = None,
    email_cc: str | None = None,
    email_timestamp: str | None = None,
    source_url: str | None = None,
    forwarded_by: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> EmailIngestResult:
    resolved_subject = subject.strip()
    resolved_consent = consent_basis.strip()
    if not resolved_subject:
        raise ValueError("email ingest requires subject")
    if not resolved_consent:
        raise ValueError("email ingest requires consent_basis")
    if not body.strip():
        raise ValueError("email ingest requires body")
    resolved_source = source or "openclaw.email.forwarded"
    resolved_title = title or resolved_subject
    event_metadata: dict[str, Any] = {
        "source_type": "email",
        "provenance": "operator-forwarded",
        "consent_basis": resolved_consent,
        "ingestion_boundary": "operator-selected-email",
        "external_action": False,
        "subject": resolved_subject,
    }
    optional_metadata = {
        "message_id": message_id,
        "thread_id": thread_id,
        "email_from": email_from,
        "email_to": email_to,
        "email_cc": email_cc,
        "email_timestamp": email_timestamp,
        "source_url": source_url,
        "forwarded_by": forwarded_by,
    }
    for key, value in optional_metadata.items():
        if value:
            event_metadata[key] = value
    for key, value in (metadata or {}).items():
        clean_key = str(key).strip()
        if clean_key and clean_key not in event_metadata:
            event_metadata[clean_key] = value
    event_path = add_stream_event(
        repo_path,
        stream=stream,
        title=resolved_title,
        body=body,
        source=resolved_source,
        metadata=event_metadata,
        commit=commit,
    )
    return EmailIngestResult(
        event_path=str(event_path),
        title=resolved_title,
        source=resolved_source,
        consent_basis=resolved_consent,
    )


def ingest_direct_signal(
    repo_path: str | Path,
    *,
    title: str | None = None,
    body: str,
    surface: str,
    consent_basis: str,
    source: str | None = None,
    stream: str = "streams/inbox/direct",
    observed_at: str | None = None,
    sender: str | None = None,
    thread_id: str | None = None,
    message_id: str | None = None,
    topic: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> DirectIngestResult:
    resolved_surface = surface.strip()
    resolved_consent = consent_basis.strip()
    if not resolved_surface:
        raise ValueError("direct ingest requires surface")
    if not resolved_consent:
        raise ValueError("direct ingest requires consent_basis")
    if not body.strip():
        raise ValueError("direct ingest requires body")
    resolved_source = source or f"openclaw.{_slugify(resolved_surface)}"
    resolved_title = title or _infer_title_from_text(body, "direct operator signal")
    event_metadata: dict[str, Any] = {
        "source_type": "direct",
        "surface": resolved_surface,
        "provenance": "agent-observed",
        "consent_basis": resolved_consent,
        "ingestion_boundary": "operator-provided",
        "external_action": False,
    }
    optional_metadata = {
        "observed_at": observed_at,
        "sender": sender,
        "thread_id": thread_id,
        "message_id": message_id,
        "topic": topic,
    }
    for key, value in optional_metadata.items():
        if value:
            event_metadata[key] = value
    for key, value in (metadata or {}).items():
        clean_key = str(key).strip()
        if clean_key and clean_key not in event_metadata:
            event_metadata[clean_key] = value
    event_path = add_stream_event(
        repo_path,
        stream=stream,
        title=resolved_title,
        body=body,
        source=resolved_source,
        metadata=event_metadata,
        commit=commit,
    )
    return DirectIngestResult(
        event_path=str(event_path),
        title=resolved_title,
        source=resolved_source,
        consent_basis=resolved_consent,
    )



def configure_source(
    repo_path: str | Path,
    source_type: str,
    *,
    name: str | None = None,
    stream: str | None = None,
    metadata: dict[str, Any] | None = None,
    access_status: str = "unknown",
    access_owner: str = "operator-agent",
    sample_policy: str | None = None,
    privacy_notes: str | None = None,
    setup_next_action: str | None = None,
    commit: bool = False,
) -> SourceConfigResult:
    return _configure_source(
        repo_path,
        source_type,
        name=name,
        stream=stream,
        metadata=metadata,
        access_status=access_status,
        access_owner=access_owner,
        sample_policy=sample_policy,
        privacy_notes=privacy_notes,
        setup_next_action=setup_next_action,
        commit=commit,
        allow_existing=False,
    )


def _configure_source(
    repo_path: str | Path,
    source_type: str,
    *,
    name: str | None = None,
    stream: str | None = None,
    metadata: dict[str, Any] | None = None,
    access_status: str = "unknown",
    access_owner: str = "operator-agent",
    sample_policy: str | None = None,
    privacy_notes: str | None = None,
    setup_next_action: str | None = None,
    commit: bool = False,
    allow_existing: bool = False,
) -> SourceConfigResult:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    resolved_source_type = source_type.strip().lower()
    default_streams = {
        "direct": "streams/inbox/direct",
        "telegram": "streams/inbox/direct",
        "email": "streams/inbox/email",
        "fathom": "streams/inbox/transcripts",
        "granola": "streams/inbox/transcripts",
        "transcript": "streams/inbox/transcripts",
        "zoom": "streams/inbox/transcripts",
    }
    if resolved_source_type not in default_streams:
        raise ValueError("source_type must be one of: direct, telegram, email, fathom, granola, transcript, zoom")
    resolved_access_status = access_status.strip().lower()
    valid_access_statuses = {"available_now", "needs_setup", "defer", "unknown"}
    if resolved_access_status not in valid_access_statuses:
        raise ValueError("access_status must be one of: available_now, needs_setup, defer, unknown")
    resolved_access_owner = access_owner.strip() or "operator-agent"
    resolved_name = name or resolved_source_type
    source_id = _slugify(f"{resolved_source_type}-{resolved_name}")
    resolved_stream = stream or default_streams[resolved_source_type]
    created_at = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    frontmatter = {
        "id": source_id,
        "type": resolved_source_type,
        "name": resolved_name,
        "status": "configured",
        "stream": resolved_stream,
        "created_at": created_at,
        "access_status": resolved_access_status,
        "access_owner": resolved_access_owner,
    }
    optional_fields = {
        "sample_policy": sample_policy,
        "privacy_notes": privacy_notes,
        "setup_next_action": setup_next_action,
    }
    for key, value in optional_fields.items():
        if value:
            frontmatter[key] = value
    for key, value in (metadata or {}).items():
        clean_key = str(key).strip()
        if clean_key and clean_key not in frontmatter:
            frontmatter[clean_key] = value
    body = (
        f"# {resolved_name}\n\n"
        f"This source records `{resolved_source_type}` signal intent for `{resolved_stream}`.\n\n"
        "Access and setup are agent-owned. The record exists so an operator or agent can inspect what is available, what still needs setup, what sample policy applies, and what should be skipped before any bulk ingestion.\n\n"
        "## Agent Instructions\n\n"
        "- If `access_status` is `available_now`, ingest only a small reviewed sample first.\n"
        "- If `access_status` is `needs_setup`, guide the operator through the smallest setup step listed in `setup_next_action`.\n"
        "- If `access_status` is `defer`, do not ingest until the operator reopens this source.\n"
        "- Preserve source ids, timestamps, URLs, and privacy/redaction notes on every event derived from this source.\n"
    )
    path = repo / "sources" / f"{source_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not allow_existing:
            raise FileExistsError(f"source already exists: {path}")
        existing = read_source_record(repo, path.name)
        return SourceConfigResult(
            source_type=str(existing.get("type") or resolved_source_type),
            source_id=str(existing.get("id") or source_id),
            config_path=str(path),
            stream=str(existing.get("stream") or resolved_stream),
            status=str(existing.get("status") or "configured"),
            access_status=str(existing.get("access_status") or resolved_access_status),
            access_owner=str(existing.get("access_owner") or resolved_access_owner),
        )
    path.write_text(_render_markdown_event(frontmatter, body), encoding="utf-8")
    instructions_path = _write_agent_instructions(repo)
    stream_keep = repo / resolved_stream / ".gitkeep"
    stream_keep.parent.mkdir(parents=True, exist_ok=True)
    if not stream_keep.exists():
        stream_keep.write_text("", encoding="utf-8")
    if commit:
        _git_commit(repo, [path, stream_keep, instructions_path], f"source: {source_id}")
    return SourceConfigResult(
        source_type=resolved_source_type,
        source_id=source_id,
        config_path=str(path),
        stream=resolved_stream,
        status="configured",
        access_status=resolved_access_status,
        access_owner=resolved_access_owner,
    )


def ensure_source_config(
    repo_path: str | Path,
    source_type: str,
    *,
    name: str | None = None,
    stream: str | None = None,
    metadata: dict[str, Any] | None = None,
    access_status: str = "unknown",
    access_owner: str = "operator-agent",
    sample_policy: str | None = None,
    privacy_notes: str | None = None,
    setup_next_action: str | None = None,
    commit: bool = False,
) -> SourceConfigResult:
    return _configure_source(
        repo_path,
        source_type,
        name=name,
        stream=stream,
        metadata=metadata,
        access_status=access_status,
        access_owner=access_owner,
        sample_policy=sample_policy,
        privacy_notes=privacy_notes,
        setup_next_action=setup_next_action,
        commit=commit,
        allow_existing=True,
    )


def _parse_markdown_record(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"markdown record is missing frontmatter: {path}")
    return _parse_simple_frontmatter(match.group(1)), match.group(2).strip()


def read_source_record(repo_path: str | Path, source_ref: str) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    raw_ref = source_ref.strip()
    if not raw_ref:
        raise ValueError("source_ref is required")
    candidate = Path(raw_ref).expanduser()
    if candidate.is_absolute():
        path = candidate.resolve()
    else:
        path = repo / "sources" / raw_ref
        if path.suffix != ".md":
            path = path.with_suffix(".md")
        if not path.exists():
            path = (repo / raw_ref).resolve()
            if path.suffix != ".md":
                path = path.with_suffix(".md")
    if not path.exists():
        raise FileNotFoundError(f"source record not found: {raw_ref}")
    frontmatter, _ = _parse_markdown_record(path)
    reserved = {
        "id",
        "type",
        "name",
        "status",
        "stream",
        "created_at",
        "access_status",
        "access_owner",
        "sample_policy",
        "privacy_notes",
        "setup_next_action",
    }
    return {
        "id": str(frontmatter.get("id") or path.stem),
        "type": str(frontmatter.get("type") or ""),
        "name": str(frontmatter.get("name") or path.stem),
        "status": str(frontmatter.get("status") or "configured"),
        "stream": str(frontmatter.get("stream") or ""),
        "created_at": str(frontmatter.get("created_at") or ""),
        "access_status": str(frontmatter.get("access_status") or "unknown"),
        "access_owner": str(frontmatter.get("access_owner") or "operator-agent"),
        "sample_policy": str(frontmatter.get("sample_policy") or ""),
        "privacy_notes": str(frontmatter.get("privacy_notes") or ""),
        "setup_next_action": str(frontmatter.get("setup_next_action") or ""),
        "details": {
            key: value
            for key, value in frontmatter.items()
            if key not in reserved
        },
        "path": _repo_relative_path(repo, path),
    }


def read_source_records(repo_path: str | Path) -> list[dict[str, Any]]:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    sources_dir = repo / "sources"
    if not sources_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(sources_dir.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        records.append(read_source_record(repo, path.name))
    return records


def _source_status_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_access_status: dict[str, int] = {}
    for record in records:
        access_status = str(record.get("access_status") or "unknown")
        by_access_status[access_status] = by_access_status.get(access_status, 0) + 1
    return {
        "count": len(records),
        "by_access_status": by_access_status,
        "records": records,
    }


def _onboarding_handoff_path(repo: Path) -> Path:
    return repo / "onboarding" / "setup" / "handoff.json"


def read_onboarding_handoff(repo_path: str | Path) -> dict[str, Any] | None:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    path = _onboarding_handoff_path(repo)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data.setdefault("path", _repo_relative_path(repo, path))
        return data
    return None


def _default_handoff_summary(source_plan: list[dict[str, Any]], cadence: dict[str, str], first_sample: dict[str, Any]) -> str:
    source_count = len(source_plan)
    available = len([entry for entry in source_plan if entry.get("access_status") == "available_now"])
    needs_setup = len([entry for entry in source_plan if entry.get("access_status") == "needs_setup"])
    cadence_hint = cadence.get("hint") or "manual"
    outcome = first_sample.get("outcome") or "ingested_only"
    return (
        f"{source_count} source plan entr{'y' if source_count == 1 else 'ies'} "
        f"({available} available now, {needs_setup} need setup); "
        f"cadence {cadence_hint}; first sample {outcome}."
    )


def record_onboarding_handoff(
    repo_path: str | Path,
    *,
    source_plan: list[dict[str, Any]],
    first_sample: dict[str, Any],
    cadence_hint: str | None = None,
    cadence_trigger: str | None = None,
    handoff_summary: str | None = None,
    commit: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    config = _repo_config(repo)
    path = _onboarding_handoff_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    cadence = {
        "hint": (cadence_hint or "manual-for-now").strip(),
        "trigger": (cadence_trigger or "when-asked").strip(),
    }
    payload = {
        "schema_version": 1,
        "kind": "onboarding_handoff",
        "recorded_at": now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "org": str(config.get("org") or ""),
        "operator": str(config.get("operator") or ""),
        "cadence": cadence,
        "source_plan": source_plan,
        "first_sample": first_sample,
        "summary": (handoff_summary or "").strip() or _default_handoff_summary(source_plan, cadence, first_sample),
        "path": _repo_relative_path(repo, path),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if commit:
        _git_commit(repo, [path], "onboarding: source-plan handoff")
    return payload


def configure_subscription(
    repo_path: str | Path,
    remote: str,
    *,
    stream: str,
    name: str | None = None,
    local_stream: str | None = None,
    policy: str | None = None,
    commit: bool = False,
) -> SubscriptionConfigResult:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    resolved_remote = remote.strip()
    resolved_stream = stream.strip()
    if not resolved_remote:
        raise ValueError("subscription remote is required")
    if not resolved_stream:
        raise ValueError("subscription stream is required")
    resolved_stream = _validate_relative_stream_path(resolved_stream, field_name="subscription stream")
    _verify_remote_export_policy(resolved_remote, resolved_stream)
    source_id = _slugify(name or f"{resolved_remote}-{resolved_stream}")
    created_at = now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    frontmatter = {
        "id": source_id,
        "remote": resolved_remote,
        "stream": resolved_stream,
        "status": "configured",
        "created_at": created_at,
    }
    if local_stream:
        frontmatter["local_stream"] = _validate_subscription_local_stream(local_stream)
    if policy:
        frontmatter["policy"] = _validate_subscription_policy(policy)
    body = (
        f"# {name or source_id}\n\n"
        f"Subscribe this Lettuce to `{resolved_remote}:{resolved_stream}`.\n\n"
        "Remote git fetch, trust-mode checks, policy checks, and checkpointed polling are intentionally follow-up runtime work. This record keeps the operator-owned subscription intent in markdown first.\n"
    )
    path = repo / "subscriptions" / f"{source_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"subscription already exists: {path}")
    path.write_text(_render_markdown_event(frontmatter, body), encoding="utf-8")
    if commit:
        _git_commit(repo, [path], f"subscribe: {source_id}")
    return SubscriptionConfigResult(
        subscription_path=str(path),
        remote=resolved_remote,
        stream=resolved_stream,
        status="configured",
    )


def read_stream_events(repo_path: str | Path, stream: str) -> list[StreamEvent]:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    stream_dir = repo / stream
    events: list[StreamEvent] = []
    if not stream_dir.exists():
        return events
    for path in sorted(stream_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if match:
            frontmatter = _parse_simple_frontmatter(match.group(1))
            body = match.group(2).strip()
        else:
            frontmatter = {}
            body = text.strip()
        event_id = str(frontmatter.get("id") or path.stem)
        timestamp = str(frontmatter.get("timestamp") or "")
        events.append(StreamEvent(stream=stream, id=event_id, timestamp=timestamp, frontmatter=frontmatter, body=body, path=str(path)))
    return events


def _load_checkpoints(repo: Path) -> dict[str, list[str]]:
    path = repo / ".lettuce" / "checkpoints.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(key): [str(item) for item in value] for key, value in raw.items() if isinstance(value, list)}


def _read_markdown_record(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text.strip()
    return _parse_simple_frontmatter(match.group(1)), match.group(2).strip()


def _list_source_records(repo: Path) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    for path in sorted((repo / "sources").glob("*.md")):
        frontmatter, body = _read_markdown_record(path)
        records.append(
            SourceRecord(
                id=str(frontmatter.get("id") or path.stem),
                source_type=str(frontmatter.get("type") or ""),
                name=str(frontmatter.get("name") or path.stem),
                stream=str(frontmatter.get("stream") or ""),
                access_status=str(frontmatter.get("access_status") or "unknown"),
                poll=str(frontmatter.get("poll") or ""),
                sample_policy=str(frontmatter.get("sample_policy") or ""),
                privacy_notes=str(frontmatter.get("privacy_notes") or ""),
                setup_next_action=str(frontmatter.get("setup_next_action") or ""),
                path=str(path),
                body=body,
            )
        )
    return records


def _list_subscription_records(repo: Path) -> list[SubscriptionRecord]:
    records: list[SubscriptionRecord] = []
    for path in sorted((repo / "subscriptions").glob("*.md")):
        frontmatter, body = _read_markdown_record(path)
        records.append(
            SubscriptionRecord(
                id=str(frontmatter.get("id") or path.stem),
                remote=str(frontmatter.get("remote") or ""),
                stream=str(frontmatter.get("stream") or ""),
                local_stream=str(frontmatter.get("local_stream") or ""),
                policy=str(frontmatter.get("policy") or ""),
                path=str(path),
                body=body,
            )
        )
    return records


def _mentions(value: str, *needles: str) -> bool:
    haystack = value.strip().lower()
    if not haystack:
        return False
    return any(needle in haystack for needle in needles)


def _source_modes(record: SourceRecord) -> list[str]:
    combined = " ".join(
        item
        for item in [
            record.poll,
            record.sample_policy,
            record.privacy_notes,
            record.setup_next_action,
            record.body,
        ]
        if item
    ).lower()
    modes: list[str] = []
    transcript_types = {"fathom", "granola", "transcript", "zoom"}
    if record.source_type in {"direct", "telegram"} or _mentions(combined, "manual-only", "run lettuce on this", "operator-triggered"):
        modes.append("manual")
    if _mentions(combined, "after-meeting", "after meeting"):
        modes.append("after-meeting")
    elif record.source_type in transcript_types and _mentions(combined, "meeting", "transcript"):
        modes.append("after-meeting")
    if _mentions(combined, "daily", "every morning", "every weekday", "weekday"):
        modes.append("daily")
    if record.access_status == "available_now" and "manual" not in modes and "daily" not in modes and "after-meeting" not in modes:
        modes.append("source-check")
    return modes


def _freshness_summary(
    repo: Path,
    *,
    checkpoints: dict[str, list[str]] | None = None,
    last_log: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_records = _list_source_records(repo)
    subscription_records = _list_subscription_records(repo)
    pending_reviews = list_reviews(repo, status="pending")
    all_checkpoints = checkpoints if checkpoints is not None else _load_checkpoints(repo)
    checkpoint_entries = sum(len(value) for value in all_checkpoints.values())
    modes: list[str] = []
    available_sources: list[str] = []
    blocked_sources: list[str] = []
    manual_only_sources: list[str] = []
    for record in source_records:
        record_modes = _source_modes(record)
        if record.access_status == "available_now":
            available_sources.append(record.name)
        if record.access_status == "needs_setup":
            blocked_sources.append(record.name)
        if "manual" in record_modes:
            manual_only_sources.append(record.name)
        for mode in record_modes:
            if mode not in modes:
                modes.append(mode)
    if subscription_records and "subscription-pull" not in modes:
        modes.append("subscription-pull")
    ordered_modes = [mode for mode in ["manual", "after-meeting", "daily", "source-check", "subscription-pull"] if mode in modes]
    active_modes = [mode for mode in ordered_modes if mode != "manual"]
    if pending_reviews:
        state = "pending_review"
        reason = f"{len(pending_reviews)} pending review(s) need operator approval before brain updates land."
        next_step = "Review pending proposals with `lettuce reviews`, then approve, edit, or decline them."
    elif not ordered_modes and blocked_sources:
        state = "blocked_on_setup"
        reason = "No active freshness loop is runnable yet because the configured sources still need setup."
        next_step = "Finish the smallest setup step recorded on the blocked sources before expecting recurring maintenance."
    elif ordered_modes == ["manual"] or (not active_modes and manual_only_sources):
        state = "idle_manual_only"
        reason = "Manual/direct capture is ready, but no recurring source check or subscription pull is configured yet."
        next_step = "Wait for an operator-triggered signal or add a recurring source contract if the runtime should check again later."
    elif last_log or checkpoint_entries or subscription_records:
        state = "fresh"
        reason = "At least one maintenance path is configured and the repo has inspectable runtime state."
        next_step = "Let the external runtime or cron call the existing Lettuce commands for the next configured cadence."
    else:
        state = "fresh"
        reason = "A maintenance path is configured; the runtime still owns when the next check happens."
        next_step = "Run the next configured source check through the external runtime when the cadence or trigger fires."
    return {
        "state": state,
        "reason": reason,
        "modes": ordered_modes,
        "pending_reviews": len(pending_reviews),
        "blocked_sources": blocked_sources,
        "available_sources": available_sources,
        "manual_only_sources": manual_only_sources,
        "subscription_count": len(subscription_records),
        "checkpoint_entries": checkpoint_entries,
        "last_activity_at": str((last_log or {}).get("timestamp") or ""),
        "next_step": next_step,
    }


def _save_checkpoints(repo: Path, checkpoints: dict[str, list[str]]) -> None:
    path = repo / ".lettuce" / "checkpoints.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoints, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _checkpoint_key(handler: HandlerDefinition, stream: str) -> str:
    return f"{handler.id}:{stream}"


def _append_log(repo: Path, entry: dict[str, Any]) -> None:
    path = repo / ".lettuce" / "runtime.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def _repo_config(repo: Path) -> dict[str, Any]:
    return _read_lettuce_yaml(repo / "lettuce.yml")


def _agent_instructions_path(repo: Path) -> Path:
    return repo / _AGENT_INSTRUCTIONS_FILENAME


def _source_records(repo: Path) -> list[dict[str, Any]]:
    source_dir = repo / "sources"
    records: list[dict[str, Any]] = []
    if not source_dir.exists():
        return records
    for path in sorted(source_dir.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if not match:
            continue
        frontmatter = _parse_simple_frontmatter(match.group(1))
        frontmatter["path"] = str(path.relative_to(repo))
        records.append(frontmatter)
    return records


def _cadence_summary(records: list[dict[str, Any]]) -> str:
    cadence_hints: list[str] = []
    for record in records:
        poll = str(record.get("poll") or record.get("cadence") or "").strip()
        if not poll:
            continue
        name = str(record.get("name") or record.get("id") or "source")
        cadence_hints.append(f"`{name}`: {poll}")
    if cadence_hints:
        return "Configured cadence hints: " + "; ".join(cadence_hints)
    return "Manual/agent-triggered for now. No recurring cadence is recorded in `sources/*.md` yet."


def _render_agent_instructions(repo: Path) -> str:
    config = _repo_config(repo)
    org = str(config.get("org") or "unknown-org")
    operator = str(config.get("operator") or "operator")
    repo_type = str(config.get("type") or "personal").strip() or "personal"
    records = _source_records(repo)
    if records:
        source_lines = [
            (
                f"- `{record.get('name') or record.get('id')}` "
                f"(`{record.get('type')}` -> `{record.get('stream')}`): "
                f"`{record.get('access_status') or 'unknown'}`"
                + (
                    f"; next: {record.get('setup_next_action')}"
                    if str(record.get("setup_next_action") or "").strip()
                    else ""
                )
            )
            for record in records
        ]
    else:
        source_lines = [
            "- No source records yet. Configure at least a manual/direct source and inspect `sources/*.md` before sampling anything else."
        ]
    source_summary = "\n".join(source_lines)
    if repo_type == "company_hub":
        default_trigger = (
            f"Use this repo when the operator refers to accepted `{org}` company context, shared stream curation, "
            "or asks to update the company hub."
        )
        ingestion_example = f"""```bash
lettuce add-event {repo} \\
  --stream streams/shared/decisions \\
  --title "<accepted decision>" \\
  --body-file <tmp-decision.md> \\
  --source <approved-source> \\
  --commit
```"""
        review_policy = """- Treat this repo as curated shared context, not a raw-signal inbox.
- Default to review before durable `brain/*` writes or accepted org-level facts.
- Preserve provenance on any imported or mirrored shared event.
- Shared pulls and mirrors may only write under `streams/shared/*`."""
        privacy_rules = f"""- Keep this repo scoped to accepted `{org}` company context, not personal memory and not unrelated raw signal.
- The runtime owns chat surfaces, inboxes, browser sessions, OAuth, MCP connectors, API keys, and schedules.
- Lettuce owns durable repo state such as `lettuce.yml`, `streams/*`, `brain/*`, `sources/*`, `reviews/*`, `subscriptions/*`, and `.lettuce/*`.
- Do not use this repo as a centralized dump of every operator's inbox, transcripts, or browser history.
- Keep remote imports and mirrors under `streams/shared/*`; they must not write directly into `brain/*`."""
    else:
        default_trigger = f'Use this repo when the operator refers to `{org}`-scoped work context or says "run Lettuce on this".'
        ingestion_example = f"""```bash
lettuce ingest-direct {repo} \\
  --title "<short title>" \\
  --body-file <tmp-signal.md> \\
  --source <agent.surface> \\
  --surface <surface> \\
  --consent operator-direct-request \\
  --commit
lettuce run {repo} --review --commit
lettuce reviews {repo}
```"""
        review_policy = """- Default to `--review` before durable `brain/*` writes.
- Only bypass review if the operator explicitly asks.
- Preserve provenance, consent basis, source ids, timestamps, URLs, and redaction notes on every ingested event."""
        privacy_rules = f"""- Keep this repo scoped to `{org}` work context, not personal memory and not other orgs.
- The runtime owns chat surfaces, inboxes, browser sessions, OAuth, MCP connectors, API keys, and schedules.
- Lettuce owns durable repo state such as `lettuce.yml`, `streams/*`, `brain/*`, `sources/*`, `reviews/*`, `subscriptions/*`, and `.lettuce/*`.
- Do not bulk ingest during onboarding or source setup unless the operator explicitly asks.
- Skip personal-life context and unrelated org/project signal unless the operator wants a separate Lettuce for that scope."""
    return f"""# Lettuce Repo Agent Instructions

This file is repo-local behavior for agents using this Lettuce repo. It is scoped to `{org}` and must not overwrite global agent identity, system prompts, or personal memory.

## Scope

- Org/project: `{org}`
- Operator: `{operator}`
- Default repo path: `{repo}`

## Default Trigger

{default_trigger}

## Manual/Direct Ingestion Command Shape

{ingestion_example}

## Review Policy

{review_policy}

## Source Records

Inspect `sources/*.md` before connecting or sampling a source. These records carry access status, sample policy, privacy notes, and next setup actions.

{source_summary}

## Privacy And Boundary Rules

{privacy_rules}

## Cadence

{_cadence_summary(records)}

## Runtime Notes

Runtime-specific skills, prompts, and agent wrappers should read this file first when deciding which Lettuce repo to use and how ongoing manual/direct ingestion should behave.
"""


def _write_agent_instructions(repo: Path) -> Path:
    path = _agent_instructions_path(repo)
    path.write_text(_render_agent_instructions(repo), encoding="utf-8")
    return path


def _handler_invocation(handler: HandlerDefinition, event: StreamEvent, repo: Path) -> HandlerInvocation:
    config = _repo_config(repo)
    payload = {
        "events": [event.to_payload()],
        "publishes": [
            {"stream": ref.stream, "mode": ref.mode, "key": ref.key}
            for ref in handler.publishes
        ],
        "context": {
            "operator": str(config.get("operator") or ""),
            "org": str(config.get("org") or ""),
            "handler_id": handler.id,
            "handler_name": handler.name,
            "handler_type": handler.type,
            "handler_version": handler.version,
            "model": handler.model or str(config.get("default_model") or ""),
            "repo": str(repo),
            "invoked_at": now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
    }
    return HandlerInvocation(system=handler.body, payload=payload)


def _handler_command(repo: Path) -> str | None:
    command = os.environ.get(_HANDLER_COMMAND_ENV, "").strip()
    if command:
        return command
    config_command = str(_repo_config(repo).get("handler_command") or "").strip()
    return config_command or _DEFAULT_PROVIDER_COMMAND


def _invoke_handler(handler: HandlerDefinition, event: StreamEvent, repo: Path, *, handler_command: str | None = None) -> dict[str, Any]:
    return HandlerInvoker(command=handler_command or _handler_command(repo)).invoke(handler, event, repo)


def _validate_output(output: dict[str, Any]) -> None:
    if not isinstance(output, dict):
        raise ValueError("handler output must be a JSON object")
    if output.get("skip") is True:
        return
    publishes = output.get("publishes")
    if publishes is None:
        raise ValueError("handler output must include publishes or skip=true")
    if not isinstance(publishes, list):
        raise ValueError("handler publishes must be a list")
    for publish in publishes:
        if not isinstance(publish, dict):
            raise ValueError("publish entries must be objects")
        if not str(publish.get("stream") or "").strip():
            raise ValueError("publish entries require stream")
        if not str(publish.get("body") or "").strip():
            raise ValueError("publish entries require body")


def _write_publish(repo: Path, handler: HandlerDefinition, event: StreamEvent, publish: dict[str, Any], created_at: datetime) -> PublishResult:
    stream = str(publish["stream"]).strip()
    frontmatter = publish.get("frontmatter") if isinstance(publish.get("frontmatter"), dict) else {}
    title = str(frontmatter.get("title") or f"{handler.name} publish")
    existing = _find_existing_publish(repo, stream, handler, event, title)
    if existing is not None:
        return existing
    timestamp = created_at.replace(microsecond=0)
    short_hash = hashlib.sha1(f"{handler.id}:{event.id}:{title}".encode("utf-8")).hexdigest()[:8]
    event_id = f"{_timestamp_for_filename(timestamp)}-{_slugify(title)}-{short_hash}"
    output_frontmatter = {
        **frontmatter,
        "id": event_id,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "handler": handler.id,
        "handler_version": handler.version,
        "source_event": event.id,
        "title": title,
    }
    output_path = repo / stream / f"{event_id}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_markdown_event(output_frontmatter, str(publish["body"])), encoding="utf-8")
    return PublishResult(stream=stream, path=str(output_path), title=title)


def _find_existing_publish(repo: Path, stream: str, handler: HandlerDefinition, event: StreamEvent, title: str) -> PublishResult | None:
    stream_dir = repo / stream
    if not stream_dir.exists():
        return None
    for path in sorted(stream_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if not match:
            continue
        frontmatter = _parse_simple_frontmatter(match.group(1))
        if (
            str(frontmatter.get("handler") or "") == handler.id
            and str(frontmatter.get("source_event") or "") == event.id
            and str(frontmatter.get("title") or "") == title
        ):
            return PublishResult(stream=stream, path=str(path), title=title)
    return None


def _review_id(handler: HandlerDefinition, event: StreamEvent, target_stream: str, title: str) -> str:
    short_hash = hashlib.sha1(f"{handler.id}:{event.id}:{target_stream}:{title}".encode("utf-8")).hexdigest()[:10]
    return f"{_slugify(event.id)}-{handler.id}-{short_hash}"


def _parse_review(path: Path) -> ReviewRecord:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"review file is missing frontmatter: {path}")
    frontmatter = _parse_simple_frontmatter(match.group(1))
    review_id = str(frontmatter.get("id") or path.stem)
    return ReviewRecord(
        id=review_id,
        status=str(frontmatter.get("status") or path.parent.name),
        path=str(path),
        target_stream=str(frontmatter.get("target_stream") or ""),
        title=str(frontmatter.get("title") or frontmatter.get("target_title") or review_id),
        handler_id=str(frontmatter.get("handler") or ""),
        source_event=str(frontmatter.get("source_event") or ""),
        body=match.group(2).strip(),
        frontmatter=frontmatter,
    )


def list_reviews(repo_path: str | Path, *, status: str = "pending") -> list[ReviewRecord]:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    statuses = ["pending", "approved", "declined"] if status == "all" else [status]
    known = {"pending", "approved", "declined"}
    unknown = [item for item in statuses if item not in known]
    if unknown:
        raise ValueError(f"unknown review status: {unknown[0]}")
    records: list[ReviewRecord] = []
    for item in statuses:
        for path in sorted((repo / "reviews" / item).glob("*.md")):
            if path.name == ".gitkeep":
                continue
            records.append(_parse_review(path))
    return records


def _write_review_proposal(repo: Path, handler: HandlerDefinition, event: StreamEvent, publish: dict[str, Any], created_at: datetime) -> PublishResult:
    target_stream = str(publish["stream"]).strip()
    frontmatter = publish.get("frontmatter") if isinstance(publish.get("frontmatter"), dict) else {}
    title = str(frontmatter.get("title") or f"{handler.name} publish")
    review_id = _review_id(handler, event, target_stream, title)
    review_path = repo / "reviews" / "pending" / f"{review_id}.md"
    if review_path.exists():
        return PublishResult(stream="reviews/pending", path=str(review_path), title=title, status="pending_review", review_id=review_id, target_stream=target_stream)
    timestamp = created_at.replace(microsecond=0)
    review_frontmatter = {
        **frontmatter,
        "id": review_id,
        "status": "pending",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "handler": handler.id,
        "handler_version": handler.version,
        "source_event": event.id,
        "source_stream": event.stream,
        "target_stream": target_stream,
        "title": title,
    }
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(_render_markdown_event(review_frontmatter, str(publish["body"])), encoding="utf-8")
    return PublishResult(stream="reviews/pending", path=str(review_path), title=title, status="pending_review", review_id=review_id, target_stream=target_stream)


def _find_review_target_publish(repo: Path, review: ReviewRecord) -> PublishResult | None:
    target_dir = repo / review.target_stream
    if not target_dir.exists():
        return None
    for path in sorted(target_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if not match:
            continue
        frontmatter = _parse_simple_frontmatter(match.group(1))
        if str(frontmatter.get("review_id") or "") == review.id:
            return PublishResult(stream=review.target_stream, path=str(path), title=review.title, status="published", review_id=review.id, target_stream=review.target_stream)
    return None


def _review_path(repo: Path, review_id: str, status: str = "pending") -> Path:
    path = repo / "reviews" / status / f"{review_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"review not found: {review_id}")
    return path


def approve_review(repo_path: str | Path, review_id: str, *, operator: str = "operator", commit: bool = False) -> PublishResult:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    pending_path = _review_path(repo, review_id, "pending")
    review = _parse_review(pending_path)
    if not review.target_stream:
        raise ValueError(f"review is missing target_stream: {review_id}")
    existing = _find_review_target_publish(repo, review)
    approved_path = repo / "reviews" / "approved" / f"{review.id}.md"
    approved_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now_utc().replace(microsecond=0)
    approved_frontmatter = {
        **review.frontmatter,
        "status": "approved",
        "approved_at": timestamp.isoformat().replace("+00:00", "Z"),
        "approved_by": operator,
    }
    approved_path.write_text(_render_markdown_event(approved_frontmatter, review.body), encoding="utf-8")
    if existing is None:
        output_id = f"{_timestamp_for_filename(timestamp)}-{_slugify(review.title)}-{review.id[-8:]}"
        publish_frontmatter = {
            **{key: value for key, value in review.frontmatter.items() if key not in {"id", "status", "target_stream", "source_stream", "timestamp", "review_id", "review_status"}},
            "id": output_id,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "review_id": review.id,
            "review_status": "approved",
            "handler": review.handler_id,
            "source_event": review.source_event,
            "title": review.title,
        }
        target_path = repo / review.target_stream / f"{output_id}.md"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(_render_markdown_event(publish_frontmatter, review.body), encoding="utf-8")
        result = PublishResult(stream=review.target_stream, path=str(target_path), title=review.title, status="published", review_id=review.id, target_stream=review.target_stream)
    else:
        result = existing
    pending_path.unlink()
    if commit:
        _git_commit(repo, [pending_path, approved_path, Path(result.path)], f"review approve: {review.id}")
    return result


def decline_review(repo_path: str | Path, review_id: str, *, reason: str = "", operator: str = "operator", commit: bool = False) -> ReviewRecord:
    repo = Path(repo_path).expanduser().resolve()
    _require_lettuce_repo(repo)
    pending_path = _review_path(repo, review_id, "pending")
    review = _parse_review(pending_path)
    declined_path = repo / "reviews" / "declined" / f"{review.id}.md"
    declined_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now_utc().replace(microsecond=0)
    declined_frontmatter = {
        **review.frontmatter,
        "status": "declined",
        "declined_at": timestamp.isoformat().replace("+00:00", "Z"),
        "declined_by": operator,
    }
    if reason.strip():
        declined_frontmatter["decline_reason"] = reason.strip()
    declined_path.write_text(_render_markdown_event(declined_frontmatter, review.body), encoding="utf-8")
    pending_path.unlink()
    if commit:
        _git_commit(repo, [pending_path, declined_path], f"review decline: {review.id}")
    return _parse_review(declined_path)


def _ensure_git_repo(repo: Path) -> None:
    if (repo / ".git").exists():
        return
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)


def _git_commit(repo: Path, paths: list[Path], message: str) -> bool:
    if not (repo / ".git").exists():
        return False
    relative_paths: list[str] = []
    for path in paths:
        relative_path = str(path.relative_to(repo))
        if path.exists():
            relative_paths.append(relative_path)
            continue
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", relative_path], cwd=repo, capture_output=True, text=True)
        if tracked.returncode == 0:
            relative_paths.append(relative_path)
    relative_paths = sorted(set(relative_paths))
    if not relative_paths:
        return False
    subprocess.run(["git", "add", "--", *relative_paths], cwd=repo, check=True, capture_output=True, text=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo, capture_output=True, text=True)
    if diff.returncode == 0:
        return False
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Lettuce Runtime",
            "-c",
            "user.email=lettuce@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return True


def run_once(
    repo_path: str | Path,
    *,
    stream: str = "streams/inbox/direct",
    commit: bool = False,
    review: bool = False,
    progress: Callable[[dict[str, Any]], None] | None = None,
    handler_command: str | None = None,
) -> RunOnceResult:
    repo = Path(repo_path).expanduser().resolve()
    handlers = handlers_for_stream(discover_handlers(repo), stream)
    events = read_stream_events(repo, stream)
    checkpoints = _load_checkpoints(repo)
    run_results: list[HandlerRunResult] = []
    for event in events:
        for handler in handlers:
            key = _checkpoint_key(handler, stream)
            processed = set(checkpoints.get(key, []))
            if event.id in processed:
                continue
            created_at = now_utc()
            publish_results: list[PublishResult] = []
            errors: list[str] = []
            notes: list[str] = []
            skipped = False
            committed = False
            started = time.monotonic()
            if progress is not None:
                progress(
                    {
                        "phase": "start",
                        "handler_id": handler.id,
                        "event_id": event.id,
                        "stream": stream,
                        "timestamp": created_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    }
                )
            try:
                output = _invoke_handler(handler, event, repo, handler_command=handler_command)
                _validate_output(output)
                skipped = bool(output.get("skip"))
                notes = [str(note) for note in output.get("notes", []) if str(note).strip()]
                if not skipped:
                    for publish in output.get("publishes", []):
                        if review:
                            publish_results.append(_write_review_proposal(repo, handler, event, publish, created_at))
                        else:
                            publish_results.append(_write_publish(repo, handler, event, publish, created_at))
                    if commit and publish_results:
                        prefix = "review" if review else handler.id
                        committed = _git_commit(repo, [Path(result.path) for result in publish_results], f"{prefix}: {handler.id}: {event.id}")
                checkpoints.setdefault(key, []).append(event.id)
                _save_checkpoints(repo, checkpoints)
            except Exception as exc:  # noqa: BLE001 - runtime logs every handler failure and continues.
                errors = [str(exc)]
            duration_ms = int((time.monotonic() - started) * 1000)
            if progress is not None:
                progress(
                    {
                        "phase": "finish",
                        "handler_id": handler.id,
                        "event_id": event.id,
                        "stream": stream,
                        "success": not errors,
                        "skipped": skipped,
                        "publishes": len(publish_results),
                        "duration_ms": duration_ms,
                    }
                )
            result = HandlerRunResult(
                handler_id=handler.id,
                event_id=event.id,
                skipped=skipped,
                publishes=publish_results,
                notes=notes,
                errors=errors,
                committed=committed,
                duration_ms=duration_ms,
            )
            run_results.append(result)
            _append_log(
                repo,
                {
                    "handler_id": handler.id,
                    "event_id": event.id,
                    "success": not errors,
                    "skipped": skipped,
                    "publishes": [publish.path for publish in publish_results],
                    "errors": errors,
                    "notes": notes,
                    "committed": committed,
                    "duration_ms": duration_ms,
                    "timestamp": created_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                },
            )
    return RunOnceResult(repo=str(repo), stream=stream, handlers=len(handlers), events=len(events), runs=run_results)


def read_logs(repo_path: str | Path, *, limit: int = 20) -> list[dict[str, Any]]:
    repo = Path(repo_path).expanduser().resolve()
    path = repo / ".lettuce" / "runtime.log"
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            value = {"raw": line}
        if isinstance(value, dict):
            entries.append(value)
    if limit <= 0:
        return entries
    return entries[-limit:]


def status(repo_path: str | Path) -> RuntimeStatus:
    repo = Path(repo_path).expanduser().resolve()
    identity = read_repo_identity(repo)
    handlers = discover_handlers(repo)
    streams: dict[str, int] = {}
    streams_root = repo / "streams"
    if streams_root.exists():
        for stream_dir in sorted(path for path in streams_root.rglob("*") if path.is_dir()):
            count = len(list(stream_dir.glob("*.md")))
            if count:
                streams[str(stream_dir.relative_to(repo))] = count
    checkpoint_data = _load_checkpoints(repo)
    checkpoints = {key: len(value) for key, value in checkpoint_data.items()}
    recent_logs = read_logs(repo, limit=1)
    all_logs = read_logs(repo, limit=0)
    source_records = read_source_records(repo)
    onboarding_handoff = read_onboarding_handoff(repo) or {
        "handoff_recorded": False,
        "source_plan": [],
        "cadence": {"hint": "", "trigger": ""},
        "summary": "",
    }
    onboarding_handoff.setdefault("handoff_recorded", "recorded_at" in onboarding_handoff)
    return RuntimeStatus(
        repo=str(repo),
        identity=identity,
        handlers=len(handlers),
        streams=streams,
        checkpoints=checkpoints,
        log_entries=len(all_logs),
        agent_instructions_path=str(_agent_instructions_path(repo)) if _agent_instructions_path(repo).exists() else None,
        sources=_source_status_summary(source_records),
        onboarding=onboarding_handoff,
        last_log=recent_logs[-1] if recent_logs else None,
        freshness=_freshness_summary(repo, checkpoints=checkpoint_data, last_log=recent_logs[-1] if recent_logs else None),
    )
