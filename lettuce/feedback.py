from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class FeedbackOption:
    id: str
    label: str
    description: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
        }


DEFAULT_FEEDBACK_OPTIONS: tuple[FeedbackOption, ...] = (
    FeedbackOption(
        id="approve_all",
        label="Approve all recommendations",
        description="The brief and route recommendations are useful as-is.",
    ),
    FeedbackOption(
        id="approve_some",
        label="Approve with edits",
        description="Some recommendations are right, but routes, wording, or lens judgments need edits.",
    ),
    FeedbackOption(
        id="decline",
        label="Decline recommendations",
        description="Do not apply the recommended updates from this signal.",
    ),
    FeedbackOption(
        id="lens_feedback",
        label="Improve a lens",
        description="A lens overfired, missed something, or should be tuned for future signals.",
    ),
    FeedbackOption(
        id="auto_approve_candidate",
        label="Make this auto-approvable later",
        description="This route type looks safe enough to consider for future auto-approval rules.",
    ),
)


def feedback_template(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "decision": None,
        "approved_routes": [],
        "declined_routes": [],
        "route_edits": [],
        "lens_feedback": [],
        "auto_approve_candidates": [],
        "notes": "",
    }


def write_feedback_template(run_id: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(feedback_template(run_id), indent=2, sort_keys=True) + "\n", encoding="utf-8")
