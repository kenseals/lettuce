from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_VALID_HANDLER_TYPES = {"lens", "router", "handler"}


@dataclass(frozen=True)
class StreamRef:
    stream: str
    filter: str = ""
    since: str = ""
    mode: str = "append"
    key: str = ""

    @classmethod
    def from_mapping(cls, value: dict[str, Any], *, publish: bool = False) -> "StreamRef":
        stream = str(value.get("stream") or "").strip()
        if not stream:
            raise ValueError("stream entries require a non-empty stream")
        return cls(
            stream=stream,
            filter=str(value.get("filter") or "").strip(),
            since=str(value.get("since") or "").strip(),
            mode=str(value.get("mode") or ("append" if publish else "")).strip(),
            key=str(value.get("key") or "").strip(),
        )


@dataclass(frozen=True)
class Trigger:
    on: str
    cron: str = ""

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "Trigger":
        event = str(value.get("on") or "").strip()
        if not event:
            raise ValueError("trigger entries require a non-empty on field")
        return cls(on=event, cron=str(value.get("cron") or "").strip())


@dataclass(frozen=True)
class HandlerDefinition:
    id: str
    name: str
    type: str
    version: str
    subscribes: list[StreamRef]
    publishes: list[StreamRef]
    body: str
    path: str
    triggers: list[Trigger] = field(default_factory=lambda: [Trigger(on="new-event")])
    batch: bool = False
    batch_size: int = 10
    timeout: str = "60s"
    model: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    def subscribes_to(self, stream: str) -> bool:
        return any(ref.stream == stream for ref in self.subscribes)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",")]
    if value.isdigit():
        return int(value)
    return value.strip("\"'")


def _parse_key_value(line: str) -> tuple[str, Any] | None:
    if ":" not in line:
        return None
    key, raw_value = line.split(":", 1)
    key = key.strip()
    if not key:
        return None
    return key, _parse_scalar(raw_value)


def _parse_list_block(lines: list[str]) -> list[Any]:
    items: list[Any] = []
    current: dict[str, Any] | None = None
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current is not None:
                items.append(current)
                current = None
            item_text = stripped[2:].strip()
            parsed = _parse_key_value(item_text)
            if parsed:
                key, value = parsed
                current = {key: value}
            else:
                items.append(_parse_scalar(item_text))
            continue
        parsed = _parse_key_value(stripped)
        if parsed and current is not None:
            key, value = parsed
            current[key] = value
    if current is not None:
        items.append(current)
    return items


def _parse_frontmatter(frontmatter: str) -> dict[str, Any]:
    lines = frontmatter.splitlines()
    data: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "\t")) or ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        index += 1
        if raw_value:
            data[key] = _parse_scalar(raw_value)
            continue
        block: list[str] = []
        while index < len(lines):
            next_line = lines[index]
            if next_line.strip() and not next_line.startswith((" ", "\t", "-")) and ":" in next_line:
                break
            block.append(next_line)
            index += 1
        data[key] = _parse_list_block(block)
    return data


def _as_mapping_list(value: Any, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    mappings: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} entries must be objects")
        mappings.append(item)
    return mappings


def _as_string_list(value: Any, field_name: str) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [str(item).strip() for item in value if str(item).strip()]


def parse_handler_file(path: str | Path) -> HandlerDefinition:
    handler_path = Path(path)
    text = handler_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{handler_path} is missing YAML frontmatter")
    frontmatter, body = match.group(1), match.group(2).strip()
    data = _parse_frontmatter(frontmatter)

    missing = [key for key in ("id", "name", "type", "version", "subscribes", "publishes") if key not in data]
    if missing:
        raise ValueError(f"{handler_path} missing required handler fields: {', '.join(missing)}")

    handler_type = str(data["type"]).strip()
    if handler_type not in _VALID_HANDLER_TYPES:
        raise ValueError(f"{handler_path} has unsupported handler type: {handler_type}")

    subscribes = [StreamRef.from_mapping(item) for item in _as_mapping_list(data.get("subscribes"), "subscribes")]
    if not subscribes:
        raise ValueError(f"{handler_path} must subscribe to at least one stream")
    publishes = [StreamRef.from_mapping(item, publish=True) for item in _as_mapping_list(data.get("publishes"), "publishes")]
    triggers = [Trigger.from_mapping(item) for item in _as_mapping_list(data.get("triggers"), "triggers")]

    return HandlerDefinition(
        id=str(data["id"]).strip(),
        name=str(data["name"]).strip(),
        type=handler_type,
        version=str(data["version"]).strip(),
        subscribes=subscribes,
        publishes=publishes,
        body=body,
        path=str(handler_path),
        triggers=triggers or [Trigger(on="new-event")],
        batch=bool(data.get("batch", False)),
        batch_size=int(data.get("batch_size", 10)),
        timeout=str(data.get("timeout") or "60s").strip(),
        model=str(data.get("model") or "").strip(),
        description=str(data.get("description") or "").strip(),
        tags=_as_string_list(data.get("tags"), "tags"),
        depends_on=_as_string_list(data.get("depends_on"), "depends_on"),
    )


def discover_handlers(root: str | Path) -> list[HandlerDefinition]:
    """Scan a repo or handlers directory for v0 markdown handlers."""
    base = Path(root)
    search_root = base / "handlers" if (base / "handlers").is_dir() else base
    handlers: list[HandlerDefinition] = []
    for path in sorted(search_root.rglob("*.md")):
        try:
            handlers.append(parse_handler_file(path))
        except ValueError:
            continue
    return handlers


def handlers_for_stream(handlers: list[HandlerDefinition], stream: str) -> list[HandlerDefinition]:
    return [handler for handler in handlers if handler.subscribes_to(stream)]
