from __future__ import annotations

from .insights import SignalInsight
from .lenses import LensDefinition


def _first(kind: str, insights: list[SignalInsight]) -> SignalInsight | None:
    return next((insight for insight in insights if insight.kind == kind), None)


def operator_finding(definition: LensDefinition, insights: list[SignalInsight]) -> tuple[str, str]:
    """Return a plain-language finding + implication for an individual operator.

    The current v0.1 lenses are deterministic. This layer makes the output feel
    less like a classifier fired and more like an operator-facing judgment.
    """
    decision = _first("decision", insights)
    open_loop = _first("open_loop", insights)
    risk = _first("risk", insights)
    opportunity = _first("opportunity", insights)

    if definition.id == "product_discovery":
        if opportunity:
            return (
                f"This may be an operator-relevant opportunity: {opportunity.evidence}",
                "Pressure-test the evidence before changing focus; route to ideas/project context as a candidate, not a commitment.",
            )
        if open_loop:
            return (
                f"This raises a product/discovery question: {open_loop.evidence}",
                "Capture the learning question and decide whether it is worth a validation step.",
            )
        return (
            "This has some product-discovery shape, but the opportunity is not yet precise.",
            "Keep as a weak signal unless more buyer pain, behavior, or timing evidence appears.",
        )

    if definition.id == "operator_memory":
        if decision:
            return (
                f"This changes operator context: {decision.evidence}",
                "Preserve the decision or preference so the operator does not have to re-explain it later.",
            )
        if risk:
            return (
                f"This contains an operating boundary or risk: {risk.evidence}",
                "Route as a reviewed preference/boundary before future agents act on similar signals.",
            )
        return (
            "This may affect operator memory, but the durable takeaway is weak.",
            "Avoid saving generic summary; ask what future work would need to know.",
        )

    if definition.id == "relationship_account":
        if open_loop:
            return (
                f"This may affect a relationship or follow-up: {open_loop.evidence}",
                "Capture the person/account and next touch only if the signal names a real external actor or commitment.",
            )
        return (
            "Relationship/account signal is possible but not yet concrete.",
            "Do not create relationship memory unless a named person/org, commitment, objection, or trust change is present.",
        )

    if definition.id == "project_focus_shift":
        if decision:
            return (
                f"This may change project focus: {decision.evidence}",
                "Preview a project/queue update only if this supersedes current focus, scope, or success criteria.",
            )
        if risk:
            return (
                f"This warns against stale focus: {risk.evidence}",
                "Use it as a guardrail before advancing active work; do not silently rewrite priorities.",
            )
        return (
            "Project/focus shift is possible, but the signal is not strong enough to redirect work.",
            "Keep the packet for review without changing the active queue.",
        )

    if definition.id == "risk_open_loop":
        if risk:
            return (
                f"This contains a risk or boundary: {risk.evidence}",
                "Make the risk visible in the operator brief before any agent updates external or durable surfaces.",
            )
        if open_loop:
            return (
                f"This leaves an open loop: {open_loop.evidence}",
                "Route as a reviewable follow-up candidate only if it needs a real owner or decision.",
            )
        return (
            "No concrete risk or open loop stood out.",
            "Do not invent a blocker just to make the packet feel useful.",
        )

    if definition.id == "next_action":
        if open_loop:
            return (
                f"Likely next action candidate: {open_loop.evidence}",
                "Convert to a queue/task preview only if it is the smallest useful action after review.",
            )
        if decision:
            return (
                f"Decision may imply follow-through: {decision.evidence}",
                "Ask what state change should happen next rather than only saving the note.",
            )
        return (
            "No clear next action emerges from this signal.",
            "Packet-only is better than adding fake work.",
        )

    return (
        f"{definition.name} found relevant operator signal.",
        "Use this lens result as one input to the route recommendation.",
    )
