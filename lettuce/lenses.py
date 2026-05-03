from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from .signal import LettuceSignal


@dataclass(frozen=True)
class LensDefinition:
    id: str
    name: str
    path: str
    body: str
    applies_to: list[str] = field(default_factory=list)
    fit_boosts: list[str] = field(default_factory=list)
    fit_penalties: list[str] = field(default_factory=list)
    route_hints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LensResult:
    lens: str
    fired: bool
    finding: str
    confidence: str
    evidence: list[str] = field(default_factory=list)
    implication: str = ""
    route_hints: list[str] = field(default_factory=list)
    fit_score: int = 0
    skipped: bool = False
    skip_reason: str = ""
    runner: str = "deterministic"
    proposed_updates: list[dict] = field(default_factory=list)
    anti_actions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lens": self.lens,
            "fired": self.fired,
            "finding": self.finding,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "implication": self.implication,
            "route_hints": list(self.route_hints),
            "fit_score": self.fit_score,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "runner": self.runner,
            "proposed_updates": list(self.proposed_updates),
            "anti_actions": list(self.anti_actions),
            "open_questions": list(self.open_questions),
        }


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_list(frontmatter: str, key: str) -> list[str]:
    lines = frontmatter.splitlines()
    values: list[str] = []
    in_key = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            in_key = True
            inline = stripped[len(key) + 1 :].strip()
            if inline and not inline.startswith("["):
                values.append(inline.strip('"\''))
            continue
        if in_key:
            if stripped.startswith("- "):
                values.append(stripped[2:].strip())
                continue
            if stripped and not line.startswith((" ", "\t")):
                break
    return values


def _parse_scalar(frontmatter: str, key: str, fallback: str = "") -> str:
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            return stripped[len(key) + 1 :].strip().strip('"\'') or fallback
    return fallback


def load_lens_definitions(lens_dir: str | Path | None = None) -> list[LensDefinition]:
    root = Path(lens_dir) if lens_dir else Path.cwd() / "lenses"
    definitions: list[LensDefinition] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if match:
            frontmatter, body = match.group(1), match.group(2)
        else:
            frontmatter, body = "", text
        lens_id = _parse_scalar(frontmatter, "id", path.stem.replace("-", "_"))
        name = _parse_scalar(frontmatter, "name", path.stem.replace("-", " ").title())
        definitions.append(
            LensDefinition(
                id=lens_id,
                name=name,
                path=str(path),
                body=body.strip(),
                applies_to=_parse_list(frontmatter, "applies_to"),
                fit_boosts=_parse_list(frontmatter, "fit_boosts"),
                fit_penalties=_parse_list(frontmatter, "fit_penalties"),
                route_hints=_parse_list(frontmatter, "route_hints"),
            )
        )
    return definitions


def _infer_source_type(signal: LettuceSignal) -> str:
    source = signal.source.lower()
    if any(token in source for token in ("transcript", "call", "fathom", "zoom")):
        return "transcript"
    if "email" in source:
        return "email"
    if "link" in source or "url" in source:
        return "link"
    if "session" in source:
        return "session_summary"
    if "message" in source or "telegram" in source or "chat" in source:
        return "message"
    return "note" if signal.input_path else "message"


def _matching_evidence(text: str, original_lines: list[str], cues: list[str]) -> list[str]:
    evidence: list[str] = []
    for cue in cues:
        cue_text = cue.lower()
        cue_tokens = [token for token in re.findall(r"[a-z0-9]+", cue_text) if len(token) >= 4]
        if not cue_tokens:
            continue
        if not (all(token in text for token in cue_tokens) if len(cue_tokens) > 1 else any(token in text for token in cue_tokens)):
            continue
        for line in original_lines:
            lowered = line.lower()
            if (all(token in lowered for token in cue_tokens) if len(cue_tokens) > 1 else any(token in lowered for token in cue_tokens)):
                cleaned = line.strip(" -\t")
                snippet = cleaned[:240]
                if len(cleaned) > 240:
                    snippet += "..."
                if snippet and snippet not in evidence:
                    evidence.append(snippet)
                break
        if len(evidence) >= 3:
            break
    return evidence


def _fit_score(definition: LensDefinition, source_type: str, text: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if not definition.applies_to or source_type in definition.applies_to:
        score += 2
        reasons.append(f"applies_to:{source_type}")
    else:
        score -= 2
    for cue in definition.fit_boosts:
        tokens = [token for token in re.findall(r"[a-z0-9]+", cue.lower()) if len(token) >= 4]
        if tokens and (all(token in text for token in tokens) if len(tokens) > 1 else any(token in text for token in tokens)):
            score += 2
            reasons.append(cue)
    for cue in definition.fit_penalties:
        tokens = [token for token in re.findall(r"[a-z0-9]+", cue.lower()) if len(token) >= 4]
        if tokens and (all(token in text for token in tokens) if len(tokens) > 1 else any(token in text for token in tokens)):
            score -= 1
    return score, reasons


def select_lenses(
    signal: LettuceSignal,
    definitions: list[LensDefinition],
    *,
    max_lenses: int | None = None,
    include_weak_lenses: bool = False,
) -> tuple[list[tuple[LensDefinition, int, list[str]]], list[LensResult]]:
    source_type = _infer_source_type(signal)
    text = f"{signal.title}\n{signal.body}".lower()
    scored: list[tuple[LensDefinition, int, list[str]]] = []
    skipped: list[LensResult] = []
    for definition in definitions:
        score, reasons = _fit_score(definition, source_type, text)
        if score <= 2 and not include_weak_lenses:
            skipped.append(
                LensResult(
                    lens=definition.id,
                    fired=False,
                    finding="Lens skipped because fit was too weak.",
                    confidence="low",
                    fit_score=score,
                    skipped=True,
                    skip_reason=f"source_type={source_type}; no meaningful fit boost",
                )
            )
        else:
            scored.append((definition, score, reasons))
    scored.sort(key=lambda item: item[1], reverse=True)
    selected = scored if max_lenses is None else scored[:max_lenses]
    overflow = [] if max_lenses is None else scored[max_lenses:]
    for definition, score, _ in overflow:
        skipped.append(
            LensResult(
                lens=definition.id,
                fired=False,
                finding="Lens skipped because more relevant lenses were selected.",
                confidence="low",
                fit_score=score,
                skipped=True,
                skip_reason=f"max_lenses={max_lenses}",
            )
        )
    return selected, skipped


def _run_deterministic_selected(
    signal: LettuceSignal,
    selected: list[tuple[LensDefinition, int, list[str]]],
    *,
    insights: list[object] | None = None,
    runner: str = "deterministic",
) -> list[LensResult]:
    text = f"{signal.title}\n{signal.body}".lower()
    lines = [line for line in signal.body.splitlines() if line.strip()]
    results: list[LensResult] = []
    for definition, score, reasons in selected:
        evidence = _matching_evidence(text, lines, definition.fit_boosts + reasons)
        fired = bool(evidence) or score >= 4
        if definition.id == "relationship_account":
            relationship_tokens = ("named person", "prospect", "account", "follow-up", "follow up", "objection", "trust signal", "relationship change")
            if not any(token in text for token in relationship_tokens):
                fired = False
        confidence = "high" if len(evidence) >= 2 or score >= 6 else "medium" if fired else "low"
        if fired and insights is not None:
            from .lens_findings import operator_finding

            finding, implication = operator_finding(definition, insights)  # type: ignore[arg-type]
            no_signal_prefixes = (
                "No clear",
                "No concrete",
                "Relationship/account signal is possible",
                "Project/focus shift is possible",
            )
            if finding.startswith(no_signal_prefixes):
                fired = False
                confidence = "low"
        else:
            finding = (
                f"{definition.name} found relevant signal."
                if fired
                else f"{definition.name} was selected but did not find strong signal."
            )
            implication = (
                "Send this finding to the central router for route synthesis."
                if fired
                else "No route should be created from this lens alone."
            )
        results.append(
            LensResult(
                lens=definition.id,
                fired=fired,
                finding=finding,
                confidence=confidence,
                evidence=evidence or reasons[:3],
                implication=implication,
                route_hints=definition.route_hints if fired else [],
                fit_score=score,
                runner=runner,
            )
        )
    return results


def run_lenses(
    signal: LettuceSignal,
    lens_dir: str | Path | None = None,
    *,
    max_lenses: int | None = None,
    include_weak_lenses: bool = False,
    insights: list[object] | None = None,
    runner: str = "deterministic",
    ai_provider: object | None = None,
    fallback_to_deterministic: bool = True,
) -> list[LensResult]:
    definitions = load_lens_definitions(lens_dir)
    if not definitions:
        raise FileNotFoundError("No Lettuce lens markdown files found. Expected lenses/*.md")
    selected, skipped = select_lenses(signal, definitions, max_lenses=max_lenses, include_weak_lenses=include_weak_lenses)
    normalized_runner = runner.lower().strip()
    if normalized_runner in {"deterministic", "test"}:
        return _run_deterministic_selected(signal, selected, insights=insights) + skipped
    if normalized_runner in {"ai", "agent"}:
        try:
            from .ai_lens_runner import run_ai_lenses

            ai_run = run_ai_lenses(signal=signal, selected=selected, insights=insights, provider=ai_provider)  # type: ignore[arg-type]
            return ai_run.results + [LensResult(**{**item.to_dict(), "runner": "ai-prefilter"}) for item in skipped]
        except Exception as exc:
            if not fallback_to_deterministic:
                raise
            fallback_results = _run_deterministic_selected(signal, selected, insights=insights, runner="deterministic-fallback")
            if fallback_results:
                first = fallback_results[0]
                fallback_results[0] = LensResult(
                    lens=first.lens,
                    fired=first.fired,
                    finding=first.finding,
                    confidence=first.confidence,
                    evidence=first.evidence,
                    implication=f"{first.implication} AI runner failed, so deterministic fallback was used: {exc}",
                    route_hints=first.route_hints,
                    fit_score=first.fit_score,
                    runner="deterministic-fallback",
                    proposed_updates=first.proposed_updates,
                    anti_actions=first.anti_actions,
                    open_questions=first.open_questions,
                )
            return fallback_results + [LensResult(**{**item.to_dict(), "runner": "deterministic-fallback"}) for item in skipped]
    raise ValueError(f"Unknown lens runner: {runner}")
