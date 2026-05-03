from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any


OPENCLAW_MODEL_ENV = "LETTUCE_OPENCLAW_MODEL"
OPENCLAW_COMMAND_ENV = "LETTUCE_OPENCLAW_COMMAND"
OPENCLAW_TIMEOUT_ENV = "LETTUCE_OPENCLAW_TIMEOUT_SECONDS"
DEFAULT_MODEL = "anthropic/claude-haiku-4-5"
DEFAULT_OPENCLAW_COMMAND = "openclaw"


def _model_from_payload(payload: dict[str, Any]) -> str:
    override = os.environ.get(OPENCLAW_MODEL_ENV, "").strip()
    if override:
        return override
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    model = str(context.get("model") or "").strip()
    if "/" in model:
        return model
    if model in {"claude-sonnet-4", "claude-sonnet-4-6"}:
        return "anthropic/claude-sonnet-4-6"
    if model in {"claude-haiku-4-5", "haiku"}:
        return "anthropic/claude-haiku-4-5"
    return DEFAULT_MODEL


def _timeout_seconds() -> int:
    raw = os.environ.get(OPENCLAW_TIMEOUT_ENV, "").strip()
    if not raw:
        return 180
    try:
        return max(1, int(raw))
    except ValueError:
        return 180


def build_prompt(invocation: dict[str, Any]) -> str:
    system = str(invocation.get("system") or "").strip()
    payload = invocation.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    return "\n".join(
        [
            "You are running one Lettuce markdown handler.",
            "Use the handler prompt and invocation payload to decide whether to publish.",
            "Return only one JSON object with this shape:",
            '{"skip": true, "notes": ["..."]}',
            "or",
            '{"skip": false, "publishes": [{"stream": "brain/example", "frontmatter": {"title": "..."}, "body": "..."}], "notes": ["..."]}',
            "Every publish must include a non-empty stream and body. Do not include markdown fences.",
            "",
            "HANDLER PROMPT:",
            system,
            "",
            "INVOCATION PAYLOAD JSON:",
            json.dumps(payload, indent=2, sort_keys=True),
        ]
    )


def _extract_text(raw: str) -> str:
    decoded = _decode_first_json_object(raw)
    if isinstance(decoded, dict) and isinstance(decoded.get("outputs"), list) and decoded["outputs"]:
        first = decoded["outputs"][0]
        if isinstance(first, dict):
            return str(first.get("text") or "")
    if isinstance(decoded, dict) and "text" in decoded:
        return str(decoded.get("text") or "")
    if isinstance(decoded, str):
        return decoded
    return json.dumps(decoded)


def _decode_first_json_object(raw: str) -> Any:
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            decoded, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        return decoded
    return json.loads(raw)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidate = fence_match.group(1).strip() if fence_match else stripped
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    decoded = json.loads(candidate)
    if not isinstance(decoded, dict):
        raise ValueError("OpenClaw provider output must decode to a JSON object")
    return decoded


def run_openclaw(invocation: dict[str, Any]) -> dict[str, Any]:
    payload = invocation.get("payload") if isinstance(invocation.get("payload"), dict) else {}
    model = _model_from_payload(payload)
    command = os.environ.get(OPENCLAW_COMMAND_ENV, DEFAULT_OPENCLAW_COMMAND).strip() or DEFAULT_OPENCLAW_COMMAND
    completed = subprocess.run(
        [
            command,
            "capability",
            "model",
            "run",
            "--gateway",
            "--model",
            model,
            "--prompt",
            build_prompt(invocation),
            "--json",
        ],
        text=True,
        capture_output=True,
        timeout=_timeout_seconds(),
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()[:1000]
        raise RuntimeError(f"OpenClaw model command exited {completed.returncode}: {stderr}")
    return extract_json_object(_extract_text(completed.stdout))


def main() -> int:
    try:
        invocation = json.loads(sys.stdin.read())
        output = run_openclaw(invocation if isinstance(invocation, dict) else {})
    except Exception as exc:  # noqa: BLE001 - provider command returns structured handler failure.
        output = {"skip": True, "notes": [f"OpenClaw provider error: {exc}"]}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
