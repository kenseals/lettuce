from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Protocol

from .lenses import LensDefinition, LensResult
from .signal import LettuceSignal

VALID_CONFIDENCE = {"low", "medium", "high"}
AI_LENS_COMMAND_ENV = "LETTUCE_AI_LENS_COMMAND"
AI_LENS_MODEL_ENV = "LETTUCE_AI_LENS_MODEL"
AI_LENS_REASONING_ENV = "LETTUCE_AI_LENS_REASONING"


@dataclass(frozen=True)
class AILensRun:
    results: list[LensResult]
    provider: str
    fallback_reason: str = ""


class AILensProvider(Protocol):
    name: str

    def evaluate(
        self,
        *,
        signal: LettuceSignal,
        selected: list[tuple[LensDefinition, int, list[str]]],
        insights: list[object] | None = None,
    ) -> list[LensResult]:
        """Return structured lens results for selected lenses."""


class CommandAILensProvider:
    """AI lens provider boundary backed by a local command.

    Lettuce intentionally does not couple the package to an OpenClaw runtime API or
    paid model SDK. In `--lens-runner ai` mode, operators can set
    `LETTUCE_AI_LENS_COMMAND` to a command that reads the JSON payload from stdin
    and writes either `{\"lenses\": [...]}` or `[...]` to stdout. The command can be
    an OpenClaw-native agent adapter later; this class only owns the safe schema
    boundary and validation.
    """

    name = "command-ai"

    def __init__(self, command: str | None = None, *, timeout_seconds: int = 120) -> None:
        self.command = command or os.environ.get(AI_LENS_COMMAND_ENV, "")
        self.timeout_seconds = timeout_seconds

    def evaluate(
        self,
        *,
        signal: LettuceSignal,
        selected: list[tuple[LensDefinition, int, list[str]]],
        insights: list[object] | None = None,
    ) -> list[LensResult]:
        if not self.command.strip():
            raise RuntimeError(f"{AI_LENS_COMMAND_ENV} is not set")
        payload = build_ai_payload(signal=signal, selected=selected, insights=insights)
        completed = subprocess.run(
            self.command,
            input=json.dumps(payload, indent=2),
            text=True,
            capture_output=True,
            shell=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()[:500]
            raise RuntimeError(f"AI lens command exited {completed.returncode}: {stderr}")
        return parse_ai_lens_results(completed.stdout, selected=selected)


def _load_text(relative_path: str) -> str:
    return (Path(__file__).resolve().parent / relative_path).read_text(encoding="utf-8")


def _reasoning_level(lens_id: str) -> str:
    override = os.environ.get(AI_LENS_REASONING_ENV, "").strip()
    if override:
        return override
    if lens_id in {"product_discovery", "risk_open_loop"}:
        return "high"
    if lens_id == "project_focus_shift":
        return "medium-high"
    return "medium"


def build_ai_payload(
    *,
    signal: LettuceSignal,
    selected: list[tuple[LensDefinition, int, list[str]]],
    insights: list[object] | None = None,
) -> dict[str, Any]:
    return {
        "task": "Run Lettuce lenses as evidence-backed judgment passes.",
        "prompt": _load_text("prompts/ai-lens-runner.md"),
        "schema": json.loads(_load_text("schemas/lens-result.schema.json")),
        "model": os.environ.get(AI_LENS_MODEL_ENV, ""),
        "signal": {
            "title": signal.title,
            "source": signal.source,
            "input_path": signal.input_path,
            "body": signal.body,
        },
        "deterministic_insights": [insight.to_dict() if hasattr(insight, "to_dict") else insight for insight in (insights or [])],
        "lenses": [
            {
                "id": definition.id,
                "name": definition.name,
                "body": definition.body,
                "route_hints": list(definition.route_hints),
                "fit_score": score,
                "fit_reasons": reasons,
                "reasoning": _reasoning_level(definition.id),
            }
            for definition, score, reasons in selected
        ],
    }


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def parse_ai_lens_results(raw_json: str, *, selected: list[tuple[LensDefinition, int, list[str]]]) -> list[LensResult]:
    try:
        decoded = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI lens output was not valid JSON: {exc}") from exc
    rows = decoded.get("lenses", decoded) if isinstance(decoded, dict) else decoded
    if not isinstance(rows, list):
        raise ValueError("AI lens output must be a list or an object with a 'lenses' list")

    selected_by_id = {definition.id: (definition, score) for definition, score, _ in selected}
    results: list[LensResult] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each AI lens output must be an object")
        lens_id = str(row.get("lens_id") or row.get("lens") or "").strip()
        if lens_id not in selected_by_id:
            raise ValueError(f"AI lens output referenced unknown or unselected lens: {lens_id!r}")
        definition, fit_score = selected_by_id[lens_id]
        confidence = str(row.get("confidence", "low")).lower()
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"Invalid confidence for {lens_id}: {confidence!r}")
        fired = bool(row.get("fired", False))
        finding = str(row.get("finding") or "No strong signal found.").strip()
        implication = str(row.get("operator_implication") or row.get("implication") or "No route should be created from this lens alone.").strip()
        evidence = _coerce_list(row.get("evidence"))
        if fired and not evidence:
            raise ValueError(f"Fired AI lens {lens_id} must include quoted evidence")
        route_hints = _coerce_list(row.get("route_hints")) if fired else []
        # Keep hints bounded to the lens definition unless the model explicitly says none.
        if fired and not route_hints:
            route_hints = list(definition.route_hints)
        results.append(
            LensResult(
                lens=lens_id,
                fired=fired,
                finding=finding,
                confidence=confidence,
                evidence=evidence,
                implication=implication,
                route_hints=route_hints,
                fit_score=fit_score,
                runner="ai",
                proposed_updates=[item for item in row.get("proposed_updates", []) if isinstance(item, dict)],
                anti_actions=_coerce_list(row.get("anti_actions")),
                open_questions=_coerce_list(row.get("open_questions")),
            )
        )
        seen.add(lens_id)

    missing = [lens_id for lens_id in selected_by_id if lens_id not in seen]
    if missing:
        raise ValueError(f"AI lens output omitted selected lenses: {', '.join(missing)}")
    return results


def run_ai_lenses(
    *,
    signal: LettuceSignal,
    selected: list[tuple[LensDefinition, int, list[str]]],
    insights: list[object] | None = None,
    provider: AILensProvider | None = None,
) -> AILensRun:
    provider = provider or CommandAILensProvider()
    return AILensRun(results=provider.evaluate(signal=signal, selected=selected, insights=insights), provider=provider.name)
