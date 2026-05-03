from __future__ import annotations

import json
import sys
from typing import Any


def _first_event(payload: dict[str, Any]) -> dict[str, Any]:
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        return {}
    event = events[0]
    return event if isinstance(event, dict) else {}


def _slug_tags(handler_type: str) -> list[str]:
    tags = [handler_type.strip()] if handler_type.strip() else []
    tags.append("default-adapter")
    return tags


def handle(invocation: dict[str, Any]) -> dict[str, Any]:
    """Default local handler provider for the v0 protocol loop."""
    payload = invocation.get("payload")
    if not isinstance(payload, dict):
        return {"skip": True, "notes": ["Default adapter received no payload."]}
    event = _first_event(payload)
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    publishes = payload.get("publishes")
    if not isinstance(publishes, list) or not publishes:
        return {"skip": True, "notes": ["No publishes declared for this handler."]}

    title = str((event.get("frontmatter") or {}).get("title") or event.get("id") or "Untitled signal")
    body = str(event.get("body") or "").strip()
    if not body:
        return {"skip": True, "notes": ["Source event body was empty."]}

    publish = publishes[0] if isinstance(publishes[0], dict) else {}
    stream = str(publish.get("stream") or "").strip()
    if not stream:
        return {"skip": True, "notes": ["First publish declaration has no stream."]}

    handler_id = str(context.get("handler_id") or "handler")
    handler_name = str(context.get("handler_name") or handler_id)
    handler_type = str(context.get("handler_type") or "")
    excerpt = body.replace("\n", " ")[:500]
    return {
        "skip": False,
        "publishes": [
            {
                "stream": stream,
                "frontmatter": {
                    "title": f"{handler_name}: {title}",
                    "source_event": str(event.get("id") or ""),
                    "tags": _slug_tags(handler_type),
                    "provider": "default-adapter",
                },
                "body": f"Default adapter publish for `{handler_id}`.\n\nSource signal excerpt: {excerpt}",
            }
        ],
        "notes": ["Used default local provider adapter. Set LETTUCE_HANDLER_COMMAND to use a model-backed provider."],
    }


def main() -> int:
    raw = sys.stdin.read()
    try:
        invocation = json.loads(raw)
        output = handle(invocation)
    except Exception as exc:  # noqa: BLE001 - provider boundary returns structured failure.
        output = {"skip": True, "notes": [f"Default adapter error: {exc}"]}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
