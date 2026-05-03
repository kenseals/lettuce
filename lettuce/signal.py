from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LettuceSignal:
    """A source-agnostic solo-operator signal for the Lettuce preview loop."""

    title: str
    source: str
    body: str
    input_path: str | None = None


def _title_from_markdown(text: str, fallback: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def load_signal(path: str | Path, *, title: str | None = None, source: str = "markdown") -> LettuceSignal:
    input_path = Path(path).expanduser().resolve()
    body = input_path.read_text(encoding="utf-8")
    fallback_title = input_path.stem.replace("-", " ").strip().title() or "Untitled signal"
    signal_title = title.strip() if title and title.strip() else _title_from_markdown(body, fallback_title)
    return LettuceSignal(
        title=signal_title,
        source=source.strip() or "markdown",
        body=body,
        input_path=str(input_path),
    )
