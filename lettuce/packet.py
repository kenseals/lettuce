from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from .feedback import DEFAULT_FEEDBACK_OPTIONS, FeedbackOption
from .insights import SignalInsight, extract_insights
from .lenses import LensResult
from .signal import LettuceSignal


@dataclass(frozen=True)
class RouteProposal:
    path: str
    action: str
    reason: str
    preview: str
    requires_approval: bool = True
    owner: str = "Context steward"
    reviewer: str = "Founder/operator"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "action": self.action,
            "reason": self.reason,
            "preview": self.preview,
            "requires_approval": self.requires_approval,
            "owner": self.owner,
            "reviewer": self.reviewer,
        }


@dataclass(frozen=True)
class LettucePacket:
    run_id: str
    created_at: str
    mode: str
    signal: LettuceSignal
    judgment: str
    what_matters: list[str]
    lens_results: list[LensResult]
    routes: list[RouteProposal]
    notification: str
    approval_gates: list[str]
    learning: str
    operator_brief: str
    insights: list[SignalInsight]
    feedback_options: tuple[FeedbackOption, ...] = DEFAULT_FEEDBACK_OPTIONS

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "signal": {
                "title": self.signal.title,
                "source": self.signal.source,
                "input_path": self.signal.input_path,
            },
            "judgment": self.judgment,
            "what_matters": list(self.what_matters),
            "lenses": [result.to_dict() for result in self.lens_results],
            "routes": [route.to_dict() for route in self.routes],
            "notification": self.notification,
            "approval_gates": list(self.approval_gates),
            "learning": self.learning,
            "operator_brief": self.operator_brief,
            "insights": [insight.to_dict() for insight in self.insights],
            "feedback_options": [option.to_dict() for option in self.feedback_options],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def to_markdown(self) -> str:
        fired = [result for result in self.lens_results if result.fired and not result.skipped]
        skipped = [result for result in self.lens_results if result.skipped]
        lines: list[str] = [
            f"# Lettuce operator brief: {self.signal.title}",
            "",
            "## Operator brief",
            self.operator_brief,
            "",
            "## One review moment",
            "Approve, edit, or decline the recommendations below. Your feedback tunes both routing and lens behavior over time.",
            "",
            "### Feedback options",
        ]
        for option in self.feedback_options:
            lines.append(f"- `{option.id}` — **{option.label}**: {option.description}")
        lines.extend(["", "## Extracted signal"])
        if self.insights:
            for insight in self.insights:
                lines.extend([
                    f"### {insight.kind.replace('_', ' ').title()}",
                    f"- {insight.text}",
                    f"- Evidence: {insight.evidence}",
                ])
        else:
            lines.append("- No concrete decisions, open loops, risks, or opportunities extracted yet.")
        lines.extend([
            "",
            "## Routing packet",
            "",
            "## Source metadata",
            f"- Run: `{self.run_id}`",
            f"- Created: {self.created_at}",
            f"- Mode: {self.mode}",
            f"- Source: {self.signal.source}",
        ])
        if self.signal.input_path:
            lines.append(f"- Input: `{self.signal.input_path}`")
        lines.extend([
            "",
            "## One-sentence judgment",
            self.judgment,
            "",
            "## What matters",
        ])
        lines.extend([f"- {item}" for item in self.what_matters] or ["- No high-signal matters detected."])
        lines.extend(["", "## Lenses fired"])
        if fired:
            for result in fired:
                lines.extend([
                    f"### {result.lens}",
                    f"- Confidence: {result.confidence}",
                    f"- Runner: {result.runner}",
                    f"- Finding: {result.finding}",
                    f"- Implication: {result.implication}",
                    "- Evidence:",
                ])
                lines.extend([f"  - {item}" for item in result.evidence] or ["  - n/a"])
                lines.append(f"- Route hints: {', '.join(result.route_hints) or 'none'}")
                lines.append(f"- Fit score: {result.fit_score}")
                if result.proposed_updates:
                    lines.append("- AI proposed updates:")
                    for update in result.proposed_updates:
                        surface = update.get("surface", "unknown")
                        action = update.get("action", "preview")
                        reason = update.get("reason", "")
                        lines.append(f"  - {surface}/{action}: {reason}")
                if result.anti_actions:
                    lines.append("- Anti-actions:")
                    lines.extend([f"  - {item}" for item in result.anti_actions])
                if result.open_questions:
                    lines.append("- Open questions:")
                    lines.extend([f"  - {item}" for item in result.open_questions])
        else:
            lines.append("- None")
        if skipped:
            lines.extend(["", "## Lenses skipped"])
            for result in skipped:
                lines.append(f"- {result.lens}: {result.skip_reason} (fit {result.fit_score})")
        lines.extend(["", "## Proposed routes"])
        for route in self.routes:
            approval = "yes" if route.requires_approval else "no"
            lines.extend([
                f"### `{route.path}`",
                f"- Action: {route.action}",
                f"- Reason: {route.reason}",
                f"- Requires approval: {approval}",
                f"- Owner: {route.owner}",
                f"- Reviewer: {route.reviewer}",
                "- Preview:",
                "```md",
                route.preview.rstrip(),
                "```",
            ])
        if not self.routes:
            lines.append("- None")
        lines.extend([
            "",
            "## Proposed file changes / diffs",
            "Preview mode only. No workspace files were changed outside `.lettuce`.",
            "",
            "## Feedback capture",
            "A feedback template was written beside this packet as `feedback.json`. Edit that file or send the same feedback through your Claw review flow.",
            "",
            "## Notification summary",
            "```text",
            self.notification.rstrip(),
            "```",
            "",
            "## Approval gates",
        ])
        lines.extend([f"- {gate}" for gate in self.approval_gates] or ["- None"])
        lines.extend(["", "## Continue/kill learning", self.learning, ""])
        return "\n".join(lines)


def _build_operator_brief(*, signal: LettuceSignal, fired: list[LensResult], routes: list[RouteProposal], insights: list[SignalInsight]) -> str:
    route_count = len([route for route in routes if route.requires_approval])
    lens_names = ", ".join(result.lens for result in fired) or "no strong lenses"
    top_findings = [insight.text for insight in insights[:4]] or [result.finding for result in fired[:3]]
    if not top_findings:
        top_findings = ["No durable update is recommended yet."]
    route_lines = [f"- {route.path}: {route.preview}" for route in routes if route.requires_approval][:4]
    route_phrase = f"{route_count} recommended update{'s' if route_count != 1 else ''} need review" if route_count else "no durable updates need review"
    return "\n".join(
        [
            f"Lettuce read `{signal.title}` through {lens_names} and found {route_phrase}.",
            "",
            "What matters:",
            *[f"- {finding}" for finding in top_findings],
            "",
            "Recommended updates:",
            *(route_lines or ["- No durable routes recommended yet."]),
            "",
            "Next: approve, edit, or decline the recommendations in one pass. No external systems are changed by v0.1.",
        ]
    )


def build_packet(
    *,
    run_id: str,
    created_at: datetime,
    mode: str,
    signal: LettuceSignal,
    lens_results: list[LensResult],
    routes: list[RouteProposal],
    notification: str,
) -> LettucePacket:
    fired = [result for result in lens_results if result.fired and not result.skipped]
    fired_names = [result.lens for result in fired]
    judgment = (
        f"This signal should be routed through {', '.join(fired_names[:4])}{' and more' if len(fired_names) > 4 else ''}."
        if fired
        else "This signal does not yet justify durable routing."
    )
    insights = extract_insights(signal)
    what_matters = [insight.text for insight in insights[:5]] or [result.finding for result in fired[:5]]
    approval_gates = [
        "Preview only: inspect packet before applying any durable file changes.",
        "Do not route to external systems in v0.1.",
    ]
    if any(route.path.startswith("company-brain/") for route in routes):
        approval_gates.append("Durable context, operator-profile, and follow-up changes require operator review.")
    learning = "Continue if the proposed routes feel like useful agent context; kill or narrow any route that feels like generic memory theater."
    operator_brief = _build_operator_brief(signal=signal, fired=fired, routes=routes, insights=insights)
    return LettucePacket(
        run_id=run_id,
        created_at=created_at.isoformat(timespec="seconds"),
        mode=mode,
        signal=signal,
        judgment=judgment,
        what_matters=what_matters,
        lens_results=lens_results,
        routes=routes,
        notification=notification,
        approval_gates=approval_gates,
        learning=learning,
        operator_brief=operator_brief,
        insights=insights,
    )
