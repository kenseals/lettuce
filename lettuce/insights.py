from __future__ import annotations

from dataclasses import dataclass
import re

from .signal import LettuceSignal


@dataclass(frozen=True)
class SignalInsight:
    kind: str
    text: str
    evidence: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "evidence": self.evidence}


_KIND_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("decision", ("decision", "decided", "we should", "let's", "need to", "going to", "start", "stop", "ship")),
    ("open_loop", ("need to", "next", "todo", "follow up", "question", "blocked", "unclear", "not sure", "validate")),
    ("risk", ("risk", "concern", "worry", "avoid", "don't", "do not", "approval", "privacy", "destructive")),
    ("opportunity", ("opportunity", "pain", "buyer", "market", "customer", "revenue", "pay", "sponsor", "product", "wedge")),
)


def _clean_line(line: str) -> str:
    cleaned = line.strip().strip("-*").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _sentences(signal: LettuceSignal) -> list[str]:
    lines: list[str] = []
    for raw in signal.body.splitlines():
        cleaned = _clean_line(raw)
        if not cleaned or cleaned.startswith("#"):
            continue
        if cleaned.lower().startswith("source:"):
            continue
        # Preserve bullet/list items as their own evidence. Split long prose lightly.
        chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned)
        lines.extend(chunk.strip() for chunk in chunks if chunk.strip())
    return lines


def _summarize(kind: str, sentence: str) -> str:
    text = sentence.rstrip(".")
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    prefixes = {
        "decision": "Decision or direction",
        "open_loop": "Open loop",
        "risk": "Risk or boundary",
        "opportunity": "Opportunity signal",
    }
    return f"{prefixes.get(kind, 'Signal')}: {text}"


def extract_insights(signal: LettuceSignal, *, max_per_kind: int = 3, max_total: int = 8) -> list[SignalInsight]:
    sentences = _sentences(signal)
    insights: list[SignalInsight] = []
    counts: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for sentence in sentences:
        lowered = sentence.lower()
        for kind, cues in _KIND_PATTERNS:
            if counts.get(kind, 0) >= max_per_kind:
                continue
            if not any(cue in lowered for cue in cues):
                continue
            key = (kind, sentence.lower())
            if key in seen:
                continue
            seen.add(key)
            counts[kind] = counts.get(kind, 0) + 1
            insights.append(SignalInsight(kind=kind, text=_summarize(kind, sentence), evidence=sentence))
            break
        if len(insights) >= max_total:
            break
    return insights
