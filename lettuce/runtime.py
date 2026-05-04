from __future__ import annotations

import argparse
import hmac
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import LETTUCE_HOME
from . import run_signal as preview_runner

ROOT = Path(__file__).resolve().parents[1]
WEB_UI_DIR = ROOT / "apps" / "web" / "dist"
LEGACY_UI_DIR = ROOT / "apps" / "lattice-ui"
UI_DIR = WEB_UI_DIR if WEB_UI_DIR.joinpath("index.html").exists() else LEGACY_UI_DIR
SEED_PATH = Path(__file__).with_name("runtime_seed.json")
STATE_DIR = LETTUCE_HOME / "runtime"
STATE_PATH = STATE_DIR / "state.json"
RUNTIME_INPUT_DIR = STATE_DIR / "inputs"
BRAIN_MARKDOWN_DIR = STATE_DIR / "brain"
PREVIEW_TOKEN_ENV = "LETTUCE_PREVIEW_TOKEN"
PREVIEW_TOKEN_HEADER = "X-Lettuce-Preview-Token"
RUNTIME_LENS_RUNNER_ENV = "LETTUCE_RUNTIME_LENS_RUNNER"
AI_LENS_COMMAND_ENV = "LETTUCE_AI_LENS_COMMAND"

DEMO_SIGNAL_ID = "company-brain-control-problem"
DEMO_SIGNAL_MARKDOWN = """# Baschez: company brain control problem

Better organized Notion is not enough if agents are not forced, reminded, and equipped to use the context.

Decision: Lettuce should prove the source → lens → handler → direct company-context update loop with inspectable packet artifacts and git-friendly provenance.

Opportunity: teams with AI agents now have a context-control problem. They need a lightweight protocol that catches painful workflow signal, updates durable company context, and preserves optional feedback for calibration.

Risk: if the demo only increments mock metrics, it looks like a shell instead of a working operator loop.

Next action: process this sample signal into a real local packet, show fired lenses and route proposals, apply the local Company Brain update, and keep provenance under .lettuce/runtime/runs.
"""


def _make_preview_token() -> tuple[str, str]:
    configured = os.environ.get(PREVIEW_TOKEN_ENV, "").strip()
    if configured:
        return configured, "env"
    return secrets.token_urlsafe(18), "generated"


def _preview_token_hint(source: str) -> str:
    if source == "env":
        return f"using ${PREVIEW_TOKEN_ENV}"
    return f"generated for this process; set ${PREVIEW_TOKEN_ENV} to choose your own"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64].strip("-") or "signal"


def _manual_signal_title(body: str, title: str | None = None) -> str:
    clean_title = (title or "").strip()
    if clean_title:
        return clean_title[:140]
    for line in body.splitlines():
        line = line.strip().lstrip("# ").strip()
        if line:
            return line[:90]
    return "Manual pasted signal"


def load_seed() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def ensure_state() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        shutil.copyfile(SEED_PATH, STATE_PATH)
    return STATE_PATH


def load_state() -> dict[str, Any]:
    ensure_state()
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    seed = load_seed()
    for key, value in seed.items():
        state.setdefault(key, value)
    source_ids = {item.get("id") for item in state.get("sources", []) if isinstance(item, dict)}
    if "manual-paste" not in source_ids or "api-client" not in source_ids:
        state["sources"] = seed.get("sources", [])
    else:
        seed_sources = {item.get("id"): item for item in seed.get("sources", []) if isinstance(item, dict)}
        state["sources"] = [{**seed_sources.get(item.get("id"), {}), **item} for item in state.get("sources", [])]
    state.setdefault("requested_connectors", [])
    state.setdefault("requested_destinations", [])
    state.setdefault("destinations", seed.get("destinations", []))
    state.setdefault("onboarding", seed.get("onboarding", {}))
    state.setdefault("user_profile", seed.get("user_profile", {}))
    _migrate_org_state(state)
    _refresh_onboarding(state)
    return state


def _refresh_onboarding(state: dict[str, Any]) -> None:
    onboarding = state.setdefault("onboarding", {})
    user = state.get("user_profile", {}) if isinstance(state.get("user_profile"), dict) else {}
    brain = state.get("company_brain", {}) if isinstance(state.get("company_brain"), dict) else {}
    profile = brain.get("company_profile", {}) if isinstance(brain.get("company_profile"), dict) else {}
    onboarding["user_ready"] = bool(user.get("name") and user.get("role"))
    onboarding["org_ready"] = bool(state.get("organization", {}).get("name"))
    onboarding["brain_ready"] = bool(profile.get("summary") and profile.get("positioning"))
    onboarding["sources_ready"] = any(source.get("active") for source in state.get("sources", []) if isinstance(source, dict))
    onboarding["lenses_ready"] = bool(state.get("lenses"))
    onboarding["destinations_ready"] = any(destination.get("active") for destination in state.get("destinations", []) if isinstance(destination, dict))


def _migrate_org_state(state: dict[str, Any]) -> None:
    organization = state.setdefault("organization", {})
    organization.setdefault("id", organization.get("slug") or "lettuce-labs")
    organization.setdefault("slug", organization.get("id") or "lettuce-labs")
    organization.setdefault("name", "Lettuce Labs")
    state.setdefault("current_org_id", organization["id"])
    organizations = state.setdefault("organizations", [])
    if not any(org.get("id") == organization["id"] for org in organizations):
        organizations.insert(
            0,
            {
                "id": organization["id"],
                "name": organization.get("name", "Lettuce Labs"),
                "slug": organization.get("slug", organization["id"]),
                "created_at": organization.get("updated_at", "seed"),
            },
        )


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)
    write_company_brain_markdown(state)


def _md_escape(value: Any) -> str:
    return str(value or "").replace("\n", " ").strip()


def write_company_brain_markdown(state: dict[str, Any]) -> list[dict[str, str]]:
    brain = state.get("company_brain", {}) if isinstance(state.get("company_brain"), dict) else {}
    BRAIN_MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    profile = brain.get("company_profile", {}) if isinstance(brain.get("company_profile"), dict) else {}
    files: dict[str, str] = {
        "company-profile.md": "\n".join(
            [
                "# Company profile",
                "",
                f"Summary: {_md_escape(profile.get('summary'))}",
                f"Positioning: {_md_escape(profile.get('positioning'))}",
                f"Stage: {_md_escape(profile.get('current_stage'))}",
                f"Updated: {_md_escape(profile.get('updated_at'))}",
                "",
            ]
        )
    }

    sections = [
        ("people-accounts.md", "People and accounts", brain.get("people_accounts", [])),
        ("projects-products.md", "Projects and products", brain.get("projects_products", [])),
        ("decisions-defaults.md", "Decisions and defaults", brain.get("decisions_defaults", [])),
        ("open-loops-risks.md", "Open loops and risks", brain.get("open_loops_risks", [])),
        ("agent-context-changelog.md", "Agent context changelog", brain.get("agent_context_changelog", [])),
    ]
    for filename, title, items in sections:
        lines = [f"# {title}", ""]
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            heading = item.get("name") or item.get("title") or item.get("decision") or item.get("risk") or item.get("id") or "Untitled"
            body = item.get("notes") or item.get("body") or item.get("decision") or item.get("risk") or item.get("summary") or ""
            lines.extend([f"## {_md_escape(heading)}", "", _md_escape(body), ""])
        files[filename] = "\n".join(lines)

    written = []
    for filename, content in files.items():
        path = BRAIN_MARKDOWN_DIR / filename
        path.write_text(content, encoding="utf-8")
        written.append({"name": filename, "path": str(path), "content": content})
    return written


def brain_markdown_files() -> list[dict[str, str]]:
    state = load_state()
    files = write_company_brain_markdown(state)
    return [{"name": item["name"], "path": item["path"], "content": item["content"]} for item in files]


def _upsert_by_id(items: list[dict[str, Any]], item: dict[str, Any]) -> list[dict[str, Any]]:
    item_id = item.get("id")
    if not item_id:
        return [item, *items]
    existing = [entry for entry in items if entry.get("id") != item_id]
    return [item, *existing]


def upsert_org(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or payload.get("org_name") or "").strip()
    org_id = str(payload.get("id") or payload.get("org_id") or "").strip()
    if not name and not org_id:
        raise ValueError("org name or org id is required")
    state = load_state()
    existing = next((org for org in state.get("organizations", []) if org.get("id") == org_id), None) if org_id else None
    if existing and not name:
        org = existing
    else:
        slug = _slugify(name or org_id)
        org = {
            "id": org_id or slug,
            "name": name or existing.get("name") if existing else name,
            "slug": slug,
            "created_at": existing.get("created_at") if existing else _now(),
        }
    state["organizations"] = _upsert_by_id(list(state.get("organizations", [])), org)
    state["current_org_id"] = org["id"]
    state.setdefault("organization", {}).update(
        {
            "id": org["id"],
            "name": org["name"],
            "slug": org["slug"],
            "status": "workspace selected",
            "setup_stage": "Ready for brain setup",
            "updated_at": _now(),
            "summary": f"{org['name']} is selected for local Lettuce dogfooding. State is stored in runtime JSON only.",
        }
    )
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"Org selected: {org['name']}", "body": "Local first-user workspace state was saved."})
    save_state(state)
    return org


def update_user_profile(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    role = str(payload.get("role") or payload.get("title") or "").strip()
    if not name or not role:
        raise ValueError("user profile needs name and role")
    state = load_state()
    profile = {
        **(state.get("user_profile", {}) if isinstance(state.get("user_profile"), dict) else {}),
        "name": name,
        "email": email,
        "role": role,
        "updated_at": _now(),
    }
    state["user_profile"] = profile
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"User profile saved: {name}", "body": "Local account profile was saved for first-user dogfooding."})
    save_state(state)
    return profile


def update_brain_setup(payload: dict[str, Any]) -> dict[str, Any]:
    summary = str(payload.get("summary") or "").strip()
    stage = str(payload.get("stage") or payload.get("current_stage") or "").strip()
    positioning = str(payload.get("positioning") or "").strip()
    if not any([summary, stage, positioning]):
        raise ValueError("brain setup needs summary, stage, or positioning")
    state = load_state()
    now = _now()
    profile = state.setdefault("company_brain", {}).setdefault("company_profile", {})
    if summary:
        profile["summary"] = summary
        state.setdefault("organization", {})["summary"] = summary
    if stage:
        profile["current_stage"] = stage
        state.setdefault("organization", {})["setup_stage"] = stage
    if positioning:
        profile["positioning"] = positioning
    profile["updated_at"] = now
    state.setdefault("organization", {})["updated_at"] = now
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": "Company brain setup saved", "body": "Profile, positioning, and setup stage were persisted locally."})
    save_state(state)
    return profile


def save_custom_lens(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    body = str(payload.get("body") or "").strip()
    tags_value = payload.get("tags") or []
    if isinstance(tags_value, str):
        tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
    else:
        tags = [str(tag).strip() for tag in tags_value if str(tag).strip()]
    if not name or not body:
        raise ValueError("custom lens name and body are required")
    lens_id = str(payload.get("id") or _slugify(name))
    lens = {"id": lens_id, "name": name, "body": body, "tags": tags or ["custom"], "custom": True, "updated_at": _now()}
    state = load_state()
    state["lenses"] = _upsert_by_id(list(state.get("lenses", [])), lens)
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"Custom lens saved: {name}", "body": "The lens pack now includes one locally editable custom lens."})
    save_state(state)
    return lens


def save_source(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    kind = str(payload.get("kind") or payload.get("type") or "manual").strip()
    detail = str(payload.get("detail") or payload.get("description") or "").strip()
    if not name:
        raise ValueError("source name is required")
    source_id = str(payload.get("id") or _slugify(name))
    source = {
        "id": source_id,
        "icon": str(payload.get("icon") or {"manual": "✎", "openclaw": "◌", "github": "◧", "linear": "▣", "slack": "#", "email": "✉"}.get(kind, "•")),
        "name": name,
        "kind": kind,
        "detail": detail or f"{name} signal source.",
        "status": str(payload.get("status") or "Active"),
        "active": bool(payload.get("active", True)),
        "action": str(payload.get("action") or ("manual" if kind == "manual" else "active")),
        "button": str(payload.get("button") or ("Open paste form" if kind == "manual" else "Active")),
        "setup": str(payload.get("setup") or "Stored locally; connector credentials are not configured yet."),
        "updated_at": _now(),
    }
    state = load_state()
    state["sources"] = _upsert_by_id(list(state.get("sources", [])), source)
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"Source saved: {name}", "body": "Local source configuration was saved. No external credentials were stored."})
    save_state(state)
    return source


def request_destination(payload: dict[str, Any]) -> dict[str, Any]:
    destination_id = str(payload.get("id") or payload.get("destination_id") or "").strip()
    name = str(payload.get("name") or payload.get("destination") or destination_id).strip()
    if not name:
        raise ValueError("destination name is required")
    entry = {"id": destination_id or _slugify(name), "name": name, "requested_at": _now()}
    state = load_state()
    requested = [item for item in state.get("requested_destinations", []) if item.get("id") != entry["id"] and item.get("name") != name]
    requested.insert(0, entry)
    state["requested_destinations"] = requested
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"Destination requested: {name}", "body": "Stored locally. Company Brain remains the active destination today."})
    save_state(state)
    return entry


def save_destination(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    kind = str(payload.get("kind") or payload.get("type") or "company-brain").strip()
    detail = str(payload.get("detail") or payload.get("description") or "").strip()
    if not name:
        raise ValueError("destination name is required")
    destination_id = str(payload.get("id") or _slugify(name))
    destination = {
        "id": destination_id,
        "icon": str(payload.get("icon") or {"company-brain": "☘", "linear": "▣", "github": "⌘", "slack": "#", "email": "✉", "webhook": "↗"}.get(kind, "•")),
        "name": name,
        "kind": kind,
        "detail": detail or f"{name} destination.",
        "status": str(payload.get("status") or "Active"),
        "active": bool(payload.get("active", True)),
        "action": str(payload.get("action") or "active"),
        "button": str(payload.get("button") or "Active"),
        "updated_at": _now(),
    }
    state = load_state()
    state["destinations"] = _upsert_by_id(list(state.get("destinations", [])), destination)
    _refresh_onboarding(state)
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"Destination saved: {name}", "body": "Local destination configuration was saved. External writes still require explicit connector work."})
    save_state(state)
    return destination


def _packet_signal(packet: dict[str, Any]) -> dict[str, Any]:
    signal = packet.get("signal") if isinstance(packet.get("signal"), dict) else {}
    return signal or {}


def _packet_insights(packet: dict[str, Any]) -> list[dict[str, Any]]:
    insights = packet.get("insights") if isinstance(packet.get("insights"), list) else []
    return [item for item in insights if isinstance(item, dict)]


def _first_insight(packet: dict[str, Any], kind: str) -> str:
    for insight in _packet_insights(packet):
        if insight.get("kind") == kind:
            return str(insight.get("evidence") or insight.get("text") or "").strip()
    return ""


def _packet_text(packet: dict[str, Any]) -> str:
    signal = _packet_signal(packet)
    pieces = [str(signal.get("title") or ""), str(signal.get("source") or "")]
    pieces.extend(str(item.get("evidence") or item.get("text") or "") for item in _packet_insights(packet))
    return "\n".join(pieces).lower()


def _source_context(packet: dict[str, Any], *, source_name: str) -> dict[str, str]:
    text = _packet_text(packet)
    signal = _packet_signal(packet)
    title = str(signal.get("title") or "this signal").strip() or "this signal"
    source = str(signal.get("source") or source_name).strip() or source_name
    if any(token in text for token in ("saved", "external", "x-post", "tweet", "yc", "rfs", "baschez", "category", "article", "resource")):
        kind = "saved_external_category"
        owner = "Product/positioning owner"
        reviewer = "Founder/operator"
        destination = "Company Brain + Lettuce project artifact"
    elif any(token in text for token in ("customer", "buyer", "prospect", "pain", "pay", "revenue", "lead", "market")):
        kind = "customer_market_pain"
        owner = "Discovery/revenue owner"
        reviewer = "Founder/operator"
        destination = "Company Brain target segment + validation backlog"
    elif any(token in text for token in ("decision", "focus", "priority", "company-building", "mission", "cofound", "queue", "sprint")):
        kind = "company_building_note"
        owner = "Company-building operator"
        reviewer = "Founder/operator"
        destination = "Company Brain decisions/defaults + project state"
    else:
        kind = "operator_note"
        owner = "Context steward"
        reviewer = "Founder/operator"
        destination = "Company Brain changelog"
    return {"kind": kind, "title": title, "source": source, "owner": owner, "reviewer": reviewer, "destination": destination}


def _short(value: str, fallback: str, *, limit: int = 190) -> str:
    text = re.sub(r"\s+", " ", value or "").strip() or fallback
    return text[: limit - 3].rstrip() + "..." if len(text) > limit else text


def _company_changes(packet: dict[str, Any], packet_json: Path, *, source_name: str = "Demo/OpenClaw", review_note: str = "") -> list[dict[str, str]]:
    run_id = str(packet.get("run_id") or DEMO_SIGNAL_ID)
    context = _source_context(packet, source_name=source_name)
    decision = _first_insight(packet, "decision")
    opportunity = _first_insight(packet, "opportunity")
    risk = _first_insight(packet, "risk")
    open_loop = _first_insight(packet, "open_loop")
    title = context["title"]
    source_kind = context["kind"].replace("_", " ")
    edited_suffix = f" Reviewer edit: {review_note}" if review_note else ""

    profile_detail = {
        "saved_external_category": "Position Lettuce around durable company context for agents, not generic knowledge-base storage.",
        "customer_market_pain": "Keep the product promise tied to concrete customer pain, validation gates, and willingness-to-pay evidence.",
        "company_building_note": "Treat Lettuce as first-user company-building infrastructure: direct context updates must change future agent behavior.",
        "operator_note": "Preserve only the context future agents need; avoid generic memory theater.",
    }.get(context["kind"], "Preserve durable context updates with provenance.")

    segment_detail = _short(
        opportunity,
        {
            "saved_external_category": f"External category evidence from {source_name} should sharpen positioning before it creates new work.",
            "customer_market_pain": f"Customer/market pain in `{title}` should be routed to a validation owner, not buried as a summary.",
            "company_building_note": f"Company-building signal `{title}` affects how the first-user sprint should be judged.",
            "operator_note": f"Operator note `{title}` was preserved as scoped company context.",
        }.get(context["kind"], f"Signal `{title}` updated local company context."),
    )
    project_detail = _short(decision or open_loop, f"Processed {source_kind} signal `{title}` into local company context with provenance.")
    default_detail = _short(
        risk or decision,
        "Saved external posts, validation gates, and fresh instructions require scoped destinations and explicit owners.",
    )
    risk_detail = _short(
        risk or open_loop,
        "Watch for broad route proposals and template-shaped Company Brain updates; prefer packet-only when signal strength is weak.",
    )

    return [
        {
            "area": "company_profile",
            "object_id": "company_profile",
            "label": f"Positioning updated from {source_kind}",
            "detail": profile_detail,
            "owner": context["owner"],
            "reviewer": context["reviewer"],
            "destination": context["destination"],
        },
        {
            "area": "people_accounts",
            "object_id": "ai-first-teams" if context["kind"] != "customer_market_pain" else "validated-market-pain",
            "label": "Target segment evidence refreshed",
            "detail": segment_detail,
            "owner": context["owner"],
            "reviewer": context["reviewer"],
            "destination": context["destination"],
        },
        {
            "area": "projects_products",
            "object_id": "lettuce-runtime",
            "label": "Runtime proof advanced",
            "detail": project_detail,
            "owner": "Product/runtime owner",
            "reviewer": context["reviewer"],
            "destination": "Lettuce runtime project state",
        },
        {
            "area": "decisions_defaults",
            "object_id": "direct-brain-update-default",
            "label": "Routing default reinforced",
            "detail": default_detail,
            "owner": "Context steward",
            "reviewer": context["reviewer"],
            "destination": "Company Brain decisions/defaults",
        },
        {
            "area": "open_loops_risks",
            "object_id": "prove-real-state-change",
            "label": "Route specificity risk tracked",
            "detail": risk_detail,
            "owner": context["owner"],
            "reviewer": context["reviewer"],
            "destination": "Company Brain risk/open-loop list",
        },
        {
            "area": "agent_context_changelog",
            "object_id": f"signal-{run_id}",
            "label": "Agent context changed",
            "detail": f"Recorded {source_kind} packet at {packet_json}; update owner={context['owner']}; reviewer={context['reviewer']}.{edited_suffix}",
            "owner": context["owner"],
            "reviewer": context["reviewer"],
            "destination": "Company Brain changelog",
        },
    ]

def _company_brain_route_proposal(packet: dict[str, Any], packet_json: Path, *, signal_id: str, source_name: str) -> dict[str, Any]:
    return {
        "id": "company_brain:reviewed-context-update",
        "path": "company_brain/local-json",
        "action": "optional_feedback_apply",
        "reason": "The only apply-capable v0 destination is the local Company Brain object store.",
        "preview": "Apply the local Company Brain JSON update and append provenance-backed update logs. Optional feedback can correct or decline later.",
        "requires_approval": False,
        "destination": "company_brain",
        "apply_scope": "local_only",
        "safety": "No external workspace, GitHub, Linear, Slack, email, or memory writes.",
        "owner": "Context steward",
        "reviewer": "Founder/operator",
        "proposed_changes": _company_changes(packet, packet_json, source_name=source_name),
        "signal_id": signal_id,
    }


def _packet_provenance(packet: dict[str, Any], packet_json: Path, *, signal_id: str, source_name: str) -> dict[str, Any]:
    signal = packet.get("signal") or {}
    return {
        "source_name": source_name,
        "signal_id": signal_id,
        "signal_title": signal.get("title") or signal_id,
        "signal_source": signal.get("source"),
        "raw_signal_path": signal.get("input_path"),
        "run_id": packet.get("run_id") or signal_id,
        "packet_path": str(packet_json),
        "route_paths": [route.get("path") for route in packet.get("routes", []) if route.get("path")],
        "fired_lenses": [lens.get("lens") for lens in packet.get("lenses", []) if lens.get("fired") and not lens.get("skipped") and lens.get("lens")],
    }


def _update_log_entry(
    *,
    packet: dict[str, Any],
    packet_json: Path,
    signal_id: str,
    source_name: str,
    object_area: str,
    object_id: str,
    change: dict[str, str],
    now: str,
) -> dict[str, Any]:
    run_id = str(packet.get("run_id") or signal_id)
    return {
        "id": f"{run_id}:{object_area}:{object_id}",
        "time": now,
        "action": "company_brain_object_updated",
        "object_area": object_area,
        "object_id": object_id,
        "label": change.get("label"),
        "summary": change.get("detail"),
        "owner": change.get("owner"),
        "reviewer": change.get("reviewer"),
        "destination": change.get("destination"),
        "provenance": _packet_provenance(packet, packet_json, signal_id=signal_id, source_name=source_name),
    }


def _with_update_log(item: dict[str, Any], entry: dict[str, Any], *, limit: int = 5) -> dict[str, Any]:
    existing = [log for log in item.get("update_log", []) if isinstance(log, dict) and log.get("id") != entry.get("id")]
    item["update_log"] = [entry, *existing][:limit]
    item["last_provenance"] = entry["provenance"]
    return item


def _find_change(changes: list[dict[str, str]], area: str, object_id: str) -> dict[str, str]:
    return next((change for change in changes if change.get("area") == area and change.get("object_id") == object_id), {"area": area, "object_id": object_id, "label": area, "detail": ""})


def _demo_company_changes(packet: dict[str, Any], packet_json: Path) -> list[dict[str, str]]:
    return _company_changes(packet, packet_json, source_name="Demo/OpenClaw")


def apply_company_brain_update(state: dict[str, Any], packet: dict[str, Any], packet_json: Path, *, signal_id: str = DEMO_SIGNAL_ID, source_name: str = "Demo/OpenClaw", review_note: str = "") -> list[dict[str, str]]:
    """Apply a processed signal to local org/company brain state and return a human-readable diff."""
    now = _now()
    run_id = str(packet.get("run_id") or DEMO_SIGNAL_ID)
    changes = _company_changes(packet, packet_json, source_name=source_name, review_note=review_note)

    organization = state.setdefault("organization", {})
    organization.update(
        {
            "status": "signal processed",
            "setup_stage": "Company brain proof active",
            "updated_at": now,
            "summary": f"Local org is wired to show {source_name} signal → lens → router → company-brain state changes.",
        }
    )

    brain = state.setdefault("company_brain", {})
    def log_for(area: str, object_id: str) -> dict[str, Any]:
        change = _find_change(changes, area, object_id)
        return _update_log_entry(
            packet=packet,
            packet_json=packet_json,
            signal_id=signal_id,
            source_name=source_name,
            object_area=area,
            object_id=object_id,
            change=change,
            now=now,
        )

    profile_change = _find_change(changes, "company_profile", "company_profile")
    profile = brain.setdefault("company_profile", {})
    profile.update(
        {
            "summary": profile_change.get("detail") or "Lettuce turns company signal into durable, inspectable company context for agents and operators.",
            "positioning": "A markdown+git context-control protocol that routes signal-specific updates into the durable brain agents actually use.",
            "current_stage": "YC sprint first-user app",
            "updated_at": now,
        }
    )
    _with_update_log(profile, log_for("company_profile", "company_profile"))

    existing_people = {item.get("id"): item for item in brain.get("people_accounts", []) if isinstance(item, dict)}
    people_entry = {
        **existing_people.get("ai-first-teams", {}),
        "id": "ai-first-teams",
        "name": "AI-first technical teams",
        "type": "target account segment",
        "status": "validated pain signal",
        "notes": _find_change(changes, "people_accounts", "ai-first-teams").get("detail") or _find_change(changes, "people_accounts", "validated-market-pain").get("detail"),
        "updated_at": now,
    }
    brain["people_accounts"] = _upsert_by_id(
        list(brain.get("people_accounts", [])),
        _with_update_log(people_entry, log_for("people_accounts", "ai-first-teams")),
    )

    existing_projects = {item.get("id"): item for item in brain.get("projects_products", []) if isinstance(item, dict)}
    project_entry = {
        **existing_projects.get("lettuce-runtime", {}),
        "id": "lettuce-runtime",
        "name": "Standalone Lettuce runtime",
        "status": "company-brain dogfood active" if source_name == "Manual Paste" else "company-brain integration active",
        "notes": _find_change(changes, "projects_products", "lettuce-runtime").get("detail") or f"Run {source_name} signal to generate packet artifacts and update org/company brain state in local JSON.",
        "updated_at": now,
    }
    brain["projects_products"] = _upsert_by_id(
        list(brain.get("projects_products", [])),
        _with_update_log(project_entry, log_for("projects_products", "lettuce-runtime")),
    )

    existing_decisions = {item.get("id"): item for item in brain.get("decisions_defaults", []) if isinstance(item, dict)}
    decision_entry = {
        **existing_decisions.get("direct-brain-update-default", {}),
        "id": "direct-brain-update-default",
        "decision": _find_change(changes, "decisions_defaults", "direct-brain-update-default").get("detail") or "Default product posture should apply scoped local company-brain updates before any external write automation.",
        "source": run_id,
        "updated_at": now,
    }
    brain["decisions_defaults"] = _upsert_by_id(
        list(brain.get("decisions_defaults", [])),
        _with_update_log(decision_entry, log_for("decisions_defaults", "direct-brain-update-default")),
    )

    existing_risks = {item.get("id"): item for item in brain.get("open_loops_risks", []) if isinstance(item, dict)}
    risk_entry = {
        **existing_risks.get("prove-real-state-change", {}),
        "id": "prove-real-state-change",
        "risk": _find_change(changes, "open_loops_risks", "prove-real-state-change").get("detail") or "Keep proving that signals update durable company context, not only packet artifacts.",
        "owner": _find_change(changes, "open_loops_risks", "prove-real-state-change").get("owner") or "operator",
        "status": "mitigated in app runtime",
        "updated_at": now,
    }
    brain["open_loops_risks"] = _upsert_by_id(
        list(brain.get("open_loops_risks", [])),
        _with_update_log(risk_entry, log_for("open_loops_risks", "prove-real-state-change")),
    )

    changelog_id = f"signal-{run_id}"
    existing_changelog = {item.get("id"): item for item in brain.get("agent_context_changelog", []) if isinstance(item, dict)}
    changelog_entry = {
        **existing_changelog.get(changelog_id, {}),
        "id": changelog_id,
        "time": now,
        "title": f"{source_name} signal updated company brain",
        "body": (_find_change(changes, "agent_context_changelog", changelog_id).get("detail") or "Company profile, target segment, runtime project, default, and risk posture were refreshed from the signal processing run.") + (f" Reviewer edit: {review_note}" if review_note else ""),
        "packet_path": str(packet_json),
    }
    brain["agent_context_changelog"] = _upsert_by_id(
        list(brain.get("agent_context_changelog", [])),
        _with_update_log(changelog_entry, log_for("agent_context_changelog", changelog_id)),
    )
    return changes


def apply_demo_company_brain_update(state: dict[str, Any], packet: dict[str, Any], packet_json: Path) -> list[dict[str, str]]:
    return apply_company_brain_update(state, packet, packet_json, signal_id=DEMO_SIGNAL_ID, source_name="Demo/OpenClaw")


@contextmanager
def _runtime_preview_home() -> Any:
    original_home = preview_runner.LETTUCE_HOME
    preview_runner.LETTUCE_HOME = STATE_DIR
    try:
        yield
    finally:
        preview_runner.LETTUCE_HOME = original_home


def _write_demo_signal_input() -> Path:
    RUNTIME_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_path = RUNTIME_INPUT_DIR / f"{DEMO_SIGNAL_ID}.md"
    input_path.write_text(DEMO_SIGNAL_MARKDOWN, encoding="utf-8")
    return input_path


def _runtime_lens_runner(requested: str | None = None) -> str:
    value = (requested or os.environ.get(RUNTIME_LENS_RUNNER_ENV) or "").strip().lower()
    if value:
        if value not in {"deterministic", "ai", "agent", "test"}:
            raise ValueError(f"Unsupported runtime lens runner: {value}")
        return value
    if os.environ.get(AI_LENS_COMMAND_ENV, "").strip():
        return "ai"
    return "deterministic"


def _packet_signal_summary(packet: dict[str, Any], packet_json: Path, *, signal_id: str = DEMO_SIGNAL_ID, source_name: str = "Demo/OpenClaw") -> dict[str, Any]:
    fired = [lens.get("lens", "") for lens in packet.get("lenses", []) if lens.get("fired") and not lens.get("skipped")]
    routes = [route.get("path", "") for route in packet.get("routes", [])]
    lens_runner_sources = sorted({str(lens.get("runner") or "deterministic") for lens in packet.get("lenses", [])})
    signal = packet.get("signal") or {}
    run_dir = packet_json.parent
    input_path = Path(str(signal.get("input_path") or "")) if signal.get("input_path") else None
    input_body = input_path.read_text(encoding="utf-8") if input_path and input_path.exists() else ""
    quote = next((line.strip().lstrip("# ").strip() for line in input_body.splitlines() if line.strip()), "Better organized Notion is not enough if agents are not forced/reminded/equipped to use the context.")
    return {
        "id": signal_id,
        "source_name": source_name,
        "title": signal.get("title", "Baschez: company brain control problem"),
        "quote": quote[:220],
        "lenses": fired,
        "routes": routes,
        "lens_runner_sources": lens_runner_sources,
        "feedback": "Company brain updated directly" if not packet.get("feedback") else "Feedback captured",
        "run_id": packet.get("run_id"),
        "packet_path": str(packet_json),
        "packet_markdown_path": str(run_dir / "packet.md"),
        "brief_html_path": str(run_dir / "brief.html"),
        "detail_endpoint": f"/api/signals/{signal_id}",
        "company_changes": _company_changes(packet, packet_json, source_name=source_name),
        "reviewable_route_proposals": [_company_brain_route_proposal(packet, packet_json, signal_id=signal_id, source_name=source_name)],
    }


def record_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action") or "").strip()
    if action not in {"approve", "edit", "decline"}:
        raise ValueError("feedback action must be approve, edit, or decline")
    entry = {
        "id": f"fb-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "action": action,
        "signal_id": str(payload.get("signal_id") or DEMO_SIGNAL_ID),
        "route_id": str(payload.get("route_id") or "company_brain:reviewed-context-update"),
        "note": str(payload.get("note") or "").strip(),
        "edited_update": str(payload.get("edited_update") or payload.get("edited_proposal") or "").strip(),
        "created_at": _now(),
    }
    state = load_state()
    state.setdefault("feedback", []).insert(0, entry)
    applied = apply_signal_review_decision(state, entry)
    audit_body = entry["note"] or "Operator feedback was saved to local runtime JSON."
    if applied:
        audit_body = f"{audit_body} Company Brain update was applied locally."
    state.setdefault("audit", []).insert(
        0,
        {
            "time": "just now",
            "title": f"Feedback captured: {action}",
            "body": audit_body,
        },
    )
    save_state(state)
    return entry


def _brain_review_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    brain = state.get("company_brain", {})
    profile = brain.get("company_profile", {}) if isinstance(brain.get("company_profile"), dict) else {}

    def find_item(section: str, item_id: str) -> dict[str, Any]:
        return next((item for item in brain.get(section, []) if isinstance(item, dict) and item.get("id") == item_id), {})

    return {
        "company_profile": {
            "summary": profile.get("summary"),
            "positioning": profile.get("positioning"),
            "current_stage": profile.get("current_stage"),
        },
        "people_accounts:ai-first-teams": {
            "status": find_item("people_accounts", "ai-first-teams").get("status"),
            "notes": find_item("people_accounts", "ai-first-teams").get("notes"),
        },
        "projects_products:lettuce-runtime": {
            "status": find_item("projects_products", "lettuce-runtime").get("status"),
            "notes": find_item("projects_products", "lettuce-runtime").get("notes"),
        },
        "decisions_defaults:direct-brain-update-default": {
            "decision": find_item("decisions_defaults", "direct-brain-update-default").get("decision"),
            "source": find_item("decisions_defaults", "direct-brain-update-default").get("source"),
        },
        "open_loops_risks:prove-real-state-change": {
            "risk": find_item("open_loops_risks", "prove-real-state-change").get("risk"),
            "status": find_item("open_loops_risks", "prove-real-state-change").get("status"),
        },
    }


def _snapshot_diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for object_key in sorted(set(before) | set(after)):
        before_values = before.get(object_key, {}) if isinstance(before.get(object_key), dict) else {}
        after_values = after.get(object_key, {}) if isinstance(after.get(object_key), dict) else {}
        fields = []
        for field in sorted(set(before_values) | set(after_values)):
            if before_values.get(field) != after_values.get(field):
                fields.append({"field": field, "before": before_values.get(field), "after": after_values.get(field)})
        if fields:
            diffs.append({"object": object_key, "fields": fields})
    return diffs


def apply_signal_review_decision(state: dict[str, Any], feedback_entry: dict[str, Any]) -> bool:
    """Apply optional feedback for an already processed signal into local Company Brain state."""
    signal_id = str(feedback_entry.get("signal_id") or "").strip()
    action = str(feedback_entry.get("action") or "").strip()
    signal = next((item for item in state.get("signals", []) if item.get("id") == signal_id), None)
    if signal is None:
        return False

    decision = {
        "action": action,
        "note": feedback_entry.get("note", ""),
        "route_id": feedback_entry.get("route_id") or "company_brain:reviewed-context-update",
        "edited_update": feedback_entry.get("edited_update", ""),
        "created_at": feedback_entry.get("created_at"),
        "feedback_id": feedback_entry.get("id"),
    }
    signal["review_decision"] = decision

    if action == "decline":
        signal["feedback"] = "Declined; company brain unchanged"
        signal["company_changes"] = []
        signal["review_diff"] = {"before": _brain_review_snapshot(state), "after": _brain_review_snapshot(state), "diff": []}
        return False

    packet_path = Path(str(signal.get("packet_path") or "")) if signal.get("packet_path") else None
    if not packet_path or not packet_path.exists():
        signal["feedback"] = "Feedback captured; packet artifact missing, no apply performed"
        return False

    if not str(decision.get("route_id") or "").startswith("company_brain:"):
        signal["feedback"] = "Feedback captured for preview-only route; company brain unchanged"
        signal["company_changes"] = []
        signal["review_diff"] = {"before": _brain_review_snapshot(state), "after": _brain_review_snapshot(state), "diff": []}
        return False

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    before = _brain_review_snapshot(state)
    review_note = str(decision.get("edited_update") or decision.get("note") or "") if action == "edit" else ""
    company_changes = apply_company_brain_update(
        state,
        packet,
        packet_path,
        signal_id=signal_id,
        source_name=str(signal.get("source_name") or "Manual Paste"),
        review_note=review_note,
    )
    after = _brain_review_snapshot(state)
    signal["company_changes"] = company_changes
    signal["feedback"] = f"Company brain updated via optional {action} feedback"
    signal["review_diff"] = {"before": before, "after": after, "diff": _snapshot_diff(before, after)}
    return True


def _process_runtime_signal(
    *,
    input_path: Path,
    signal_id: str,
    title: str | None,
    source: str,
    source_name: str,
    audit_title: str,
    lens_runner: str | None = None,
) -> dict[str, Any]:
    resolved_lens_runner = _runtime_lens_runner(lens_runner)
    with _runtime_preview_home():
        packet, paths = preview_runner.run_preview(
            input_path=str(input_path),
            title=title,
            source=source,
            mode="preview",
            lens_runner=resolved_lens_runner,
            include_weak_lenses=True,
        )
    packet_json = paths[1]
    packet_data = json.loads(packet_json.read_text(encoding="utf-8"))
    fired = [result.lens for result in packet.lens_results if result.fired and not result.skipped]
    route_paths = [route.path for route in packet.routes]
    lens_runner_sources = sorted({result.runner for result in packet.lens_results})
    entry = {
        "time": "just now",
        "title": audit_title,
        "body": f"Created runtime packet {packet.run_id}; lenses: {', '.join(fired) or 'none'}; routes: {', '.join(route_paths) or 'none'}; runners: {', '.join(lens_runner_sources) or resolved_lens_runner}.",
        "run_id": packet.run_id,
        "packet_path": str(packet_json),
        "lens_runner_requested": resolved_lens_runner,
        "lens_runner_sources": lens_runner_sources,
    }
    state = load_state()
    state.setdefault("audit", []).insert(0, entry)
    signals = [signal for signal in state.get("signals", []) if signal.get("id") != signal_id]
    signal_summary = _packet_signal_summary(packet_data, packet_json, signal_id=signal_id, source_name=source_name)
    before = _brain_review_snapshot(state)
    company_changes = apply_company_brain_update(
        state,
        packet_data,
        packet_json,
        signal_id=signal_id,
        source_name=source_name,
    )
    after = _brain_review_snapshot(state)
    signal_summary["company_changes"] = company_changes
    signal_summary["feedback"] = "Company brain updated directly"
    signal_summary["review_decision"] = None
    signal_summary["review_diff"] = {"before": before, "after": after, "diff": _snapshot_diff(before, after)}
    signals.insert(0, signal_summary)
    state["signals"] = signals
    onboarding = state.setdefault("onboarding", {})
    onboarding["sources_ready"] = True
    onboarding["destinations_ready"] = True
    if source_name == "Manual Paste":
        onboarding["first_signal_ready"] = True
    _refresh_onboarding(state)
    metrics = state.setdefault("metrics", [])
    if metrics:
        current = str(metrics[0].get("value", "0"))
        try:
            metrics[0]["value"] = str(int(current.replace(",", "")) + 1)
        except ValueError:
            metrics[0]["detail"] = f"{source_name} signal processed"
    save_state(state)
    return entry


def add_demo_signal() -> dict[str, Any]:
    return _process_runtime_signal(
        input_path=_write_demo_signal_input(),
        signal_id=DEMO_SIGNAL_ID,
        title=None,
        source="runtime-demo-signal",
        source_name="Demo/OpenClaw",
        audit_title="Demo signal processed into packet",
    )


def add_manual_signal(payload: dict[str, Any]) -> dict[str, Any]:
    body = str(payload.get("body") or payload.get("content") or "").strip()
    if not body:
        raise ValueError("manual signal body is required")
    title = _manual_signal_title(body, str(payload.get("title") or ""))
    now_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    signal_id = f"manual-{now_slug}-{_slugify(title)[:32]}"
    RUNTIME_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_path = RUNTIME_INPUT_DIR / f"{signal_id}.md"
    input_path.write_text(body + "\n", encoding="utf-8")
    entry = _process_runtime_signal(
        input_path=input_path,
        signal_id=signal_id,
        title=title,
        source="manual-paste",
        source_name="Manual Paste",
        audit_title="Manual pasted signal processed into packet",
        lens_runner=str(payload.get("lens_runner") or payload.get("runner") or "") or None,
    )
    entry["signal_id"] = signal_id
    return entry


def request_connector(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or payload.get("connector") or "").strip()
    if not name:
        raise ValueError("connector name is required")
    entry = {"name": name, "requested_at": _now()}
    state = load_state()
    requested = [item for item in state.get("requested_connectors", []) if item.get("name") != name]
    requested.insert(0, entry)
    state["requested_connectors"] = requested
    state.setdefault("audit", []).insert(0, {"time": "just now", "title": f"Connector requested: {name}", "body": "Stored locally for connector prioritization. No external integration was configured."})
    save_state(state)
    return entry


def _brain_update_logs_for_signal(brain: dict[str, Any], signal_id: str, run_id: str | None = None) -> list[dict[str, Any]]:
    ids = {value for value in {signal_id, run_id} if value}
    logs: list[dict[str, Any]] = []
    sections: list[tuple[str, Any]] = [("company_profile", brain.get("company_profile", {}))]
    sections.extend((key, item) for key in ["people_accounts", "projects_products", "decisions_defaults", "open_loops_risks", "agent_context_changelog"] for item in brain.get(key, []) if isinstance(item, dict))
    for section, item in sections:
        if not isinstance(item, dict):
            continue
        for log in item.get("update_log", []):
            provenance = log.get("provenance", {}) if isinstance(log, dict) else {}
            if provenance.get("signal_id") in ids or provenance.get("run_id") in ids:
                enriched = {**log, "brain_section": section}
                logs.append(enriched)
    return logs


def signal_detail(signal_id: str) -> dict[str, Any]:
    state = load_state()
    signal = next((item for item in state.get("signals", []) if item.get("id") == signal_id), None)
    if signal is None:
        raise KeyError(signal_id)

    packet_path = Path(str(signal.get("packet_path") or "")) if signal.get("packet_path") else None
    packet: dict[str, Any] = {}
    if packet_path and packet_path.exists():
        packet = json.loads(packet_path.read_text(encoding="utf-8"))

    packet_signal = packet.get("signal") or {}
    input_path = Path(str(packet_signal.get("input_path") or "")) if packet_signal.get("input_path") else None
    input_body = input_path.read_text(encoding="utf-8") if input_path and input_path.exists() else signal.get("quote", "")
    feedback = [item for item in state.get("feedback", []) if item.get("signal_id") in {signal_id, packet.get("run_id")}]
    proposed_changes = [
        {
            "path": route.get("path"),
            "action": route.get("action"),
            "requires_approval": route.get("requires_approval"),
            "preview": route.get("preview"),
        }
        for route in packet.get("routes", [])
    ]
    route_proposals = list(signal.get("reviewable_route_proposals") or []) + proposed_changes
    update_logs = _brain_update_logs_for_signal(state.get("company_brain", {}), signal_id, packet.get("run_id", signal.get("run_id")))
    lens_runner_sources = sorted({str(lens.get("runner") or "deterministic") for lens in packet.get("lenses", [])})
    review_decision = signal.get("review_decision")
    company_changes = signal.get("company_changes", [])
    status = "company_brain_updated" if company_changes else "review_pending"
    if isinstance(review_decision, dict) and review_decision.get("action") == "decline":
        status = "declined"
    result = "Stored a packet artifact, proposed routes, applied the local Company Brain update, and appended provenance-backed update_log entries. Optional review remains available for correction or decline."
    if status == "company_brain_updated":
        result = "Stored a packet artifact, proposed routes, applied the local Company Brain update, and appended provenance-backed update_log entries. No external workspace files were changed."
    elif status == "declined":
        result = "Stored a packet artifact and recorded the decline decision. Existing Company Brain state was not further changed."
    return {
        "id": signal_id,
        "summary": signal,
        "lens_runner_sources": lens_runner_sources,
        "input": {
            "source": packet_signal.get("source", "seed"),
            "path": packet_signal.get("input_path"),
            "body": input_body,
        },
        "lens_findings": packet.get("lenses", []),
        "route_proposals": route_proposals,
        "feedback_history": feedback,
        "review_decision": review_decision,
        "context_update": {
            "status": status,
            "run_id": packet.get("run_id", signal.get("run_id")),
            "artifact_dir": str(packet_path.parent) if packet_path else None,
            "packet_path": str(packet_path) if packet_path else None,
            "brief_html_path": signal.get("brief_html_path"),
            "proposed_changes": route_proposals,
            "company_changes": company_changes,
            "update_logs": update_logs,
            "review_diff": signal.get("review_diff"),
            "lens_runner_sources": lens_runner_sources,
            "provenance_chain": {
                "raw_signal_path": packet_signal.get("input_path"),
                "packet_path": str(packet_path) if packet_path else None,
                "route_paths": [route.get("path") for route in packet.get("routes", []) if route.get("path")],
                "updated_objects": [f"{log.get('object_area')}:{log.get('object_id')}" for log in update_logs],
            },
            "result": result,
        },
    }


class LettuceRuntimeHandler(SimpleHTTPRequestHandler):
    server_version = "LettuceRuntime/0.1"

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, body: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict[str, Any]:
        cached = getattr(self, "_cached_json_body", None)
        if cached is not None:
            return cached
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            self._cached_json_body = {}
            return {}
        raw = self.rfile.read(length)
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("request body must be a JSON object")
        self._cached_json_body = parsed
        return parsed

    def _write_authorized(self, payload: dict[str, Any]) -> bool:
        expected = getattr(self.server, "preview_token", "")
        auth_header = self.headers.get("Authorization", "")
        bearer = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
        query_values = parse_qs(urlparse(self.path).query).get("preview_token", [])
        presented = (
            self.headers.get(PREVIEW_TOKEN_HEADER)
            or bearer
            or str(payload.get("preview_token") or payload.get("token") or "")
            or (query_values[0] if query_values else "")
        ).strip()
        if expected and hmac.compare_digest(presented, expected):
            return True
        self._send_json(
            {
                "error": "preview token required for write endpoints",
                "hint": f"Enter the token printed by the runtime server, send {PREVIEW_TOKEN_HEADER}, or set {PREVIEW_TOKEN_ENV}.",
            },
            HTTPStatus.UNAUTHORIZED,
        )
        return False

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True, "state_path": str(STATE_PATH), "ui_dir": str(UI_DIR)})
            return
        if path == "/api/state":
            self._send_json(load_state())
            return
        if path == "/api/brain":
            state = load_state()
            self._send_json({"organization": state.get("organization", {}), "company_brain": state.get("company_brain", {})})
            return
        if path == "/api/brain-files":
            self._send_json({"files": brain_markdown_files()})
            return
        if path.startswith("/api/signals/"):
            signal_id = path.removeprefix("/api/signals/").strip("/")
            try:
                self._send_json(signal_detail(signal_id))
            except KeyError:
                self._send_json({"error": f"unknown signal: {signal_id}"}, HTTPStatus.NOT_FOUND)
            return
        if path.startswith("/api/"):
            key = path.removeprefix("/api/").strip("/")
            state = load_state()
            if key in state:
                self._send_json(state[key])
            else:
                self._send_json({"error": f"unknown endpoint: {path}"}, HTTPStatus.NOT_FOUND)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if not self._write_authorized(payload):
                return
            if path == "/api/feedback":
                self._send_json(record_feedback(payload), HTTPStatus.CREATED)
                return
            if path == "/api/manual-signal":
                self._send_json(add_manual_signal(payload), HTTPStatus.CREATED)
                return
            if path == "/api/request-connector":
                self._send_json(request_connector(payload), HTTPStatus.CREATED)
                return
            if path == "/api/sources":
                self._send_json(save_source(payload), HTTPStatus.CREATED)
                return
            if path == "/api/org":
                self._send_json(upsert_org(payload), HTTPStatus.CREATED)
                return
            if path == "/api/user":
                self._send_json(update_user_profile(payload), HTTPStatus.CREATED)
                return
            if path == "/api/brain-setup":
                self._send_json(update_brain_setup(payload), HTTPStatus.CREATED)
                return
            if path == "/api/lenses/custom":
                self._send_json(save_custom_lens(payload), HTTPStatus.CREATED)
                return
            if path == "/api/request-destination":
                self._send_json(request_destination(payload), HTTPStatus.CREATED)
                return
            if path == "/api/destinations":
                self._send_json(save_destination(payload), HTTPStatus.CREATED)
                return
            self._send_json({"error": f"unknown endpoint: {path}"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "request body must be valid JSON"}, HTTPStatus.BAD_REQUEST)


def make_server(host: str, port: int, *, quiet: bool = False) -> ThreadingHTTPServer:
    ensure_state()
    server = ThreadingHTTPServer((host, port), LettuceRuntimeHandler)
    token, token_source = _make_preview_token()
    server.preview_token = token  # type: ignore[attr-defined]
    server.preview_token_source = token_source  # type: ignore[attr-defined]
    server.quiet = quiet  # type: ignore[attr-defined]
    return server


def smoke() -> dict[str, Any]:
    state = load_state()
    required = ["sources", "lenses", "destinations", "routers", "signals", "audit", "feedback_actions", "user_profile", "organization", "organizations", "company_brain"]
    missing = [key for key in required if not state.get(key)]
    return {
        "ok": not missing and UI_DIR.joinpath("index.html").exists(),
        "missing": missing,
        "state_path": str(STATE_PATH),
        "ui_index": str(UI_DIR / "index.html"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the legacy Lettuce preview UI and local JSON API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--smoke", action="store_true", help="Validate local runtime data and exit.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.smoke:
        result = smoke()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    server = make_server(args.host, args.port, quiet=args.quiet)
    url = f"http://{args.host}:{args.port}/"
    print(f"Lettuce legacy preview runtime serving {url}")
    print(f"Local JSON state: {STATE_PATH}")
    if not args.quiet:
        print(f"Preview write token: {server.preview_token}")  # type: ignore[attr-defined]
        print(f"Token source: {_preview_token_hint(server.preview_token_source)}")  # type: ignore[attr-defined]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Lettuce runtime.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
