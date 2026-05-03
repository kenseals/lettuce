from __future__ import annotations

from collections import OrderedDict

from .lenses import LensResult
from .packet import RouteProposal
from .signal import LettuceSignal


_ROUTE_HINTS = {
    "daily_memory": ("company-brain/daily-signal-log.md", "daily signal log can capture low-risk run context"),
    "durable_memory": ("company-brain/durable-context.md", "durable context only if the decision remains durable after review"),
    "user_preference": ("company-brain/operator-profile.md", "stable operator preferences require review before updating"),
    "project_artifact": ("company-brain/product-context.md", "project-specific learning should stay close to the product context artifact"),
    "idea_or_opportunity": ("company-brain/opportunity-inbox.md", "raw product/opportunity signal can land in the reviewed opportunity inbox"),
    "product_artifact": ("company-brain/product-context.md", "product-learning updates belong in reviewed product context"),
    "relationship_memory": ("company-brain/relationship-log.md", "relationship/account signal should be captured before promotion"),
    "account_artifact": ("company-brain/account-context.md", "relationship/account context needs a reviewable company surface"),
    "followup_candidate": ("company-brain/followups.md", "follow-ups should be previewed before becoming active commitments"),
}


def _signal_text(signal: LettuceSignal) -> str:
    return f"{signal.title}\n{signal.source}\n{signal.body}".lower()


def _is_saved_external_category(signal: LettuceSignal) -> bool:
    text = _signal_text(signal)
    return any(token in text for token in ("saved", "external", "x-post", "tweet", "yc", "rfs", "baschez", "category", "article", "resource"))


def _is_existing_lettuce_context(signal: LettuceSignal) -> bool:
    text = _signal_text(signal)
    return any(token in text for token in ("lettuce", "company brain", "context-control", "context control", "agent context"))


def _is_customer_market_pain(signal: LettuceSignal) -> bool:
    text = _signal_text(signal)
    return any(token in text for token in ("customer", "buyer", "prospect", "pain", "pay", "revenue", "lead", "market"))


def _owner_for_path(path: str, signal: LettuceSignal) -> tuple[str, str]:
    if path == "company-brain/opportunity-inbox.md":
        return "Opportunity triage owner", "Founder/operator"
    if path == "company-brain/product-context.md":
        return "Product context owner", "Founder/operator"
    if path == "company-brain/followups.md":
        return "Company-building operator", "Founder/operator"
    if path == "company-brain/operator-profile.md":
        return "Operator context steward", "Founder/operator"
    if path == "company-brain/durable-context.md":
        return "Durable context steward", "Founder/operator"
    if path == "company-brain/daily-signal-log.md":
        return "Daily context steward", "Founder/operator"
    return "Context steward", "Founder/operator"


def _map_hint(hint: str, signal: LettuceSignal) -> tuple[str, str] | None:
    mapped = _ROUTE_HINTS.get(hint)
    if not mapped:
        return None
    path, reason = mapped
    if hint == "idea_or_opportunity":
        if _is_saved_external_category(signal) and _is_existing_lettuce_context(signal):
            return ("company-brain/product-context.md", "saved external/category evidence for the active product belongs in reviewed product context, not the raw opportunity inbox")
        if _is_existing_lettuce_context(signal):
            return ("company-brain/product-context.md", "active product learning belongs in reviewed product context, not the raw opportunity inbox")
        if _is_customer_market_pain(signal):
            return ("company-brain/product-context.md", "customer/market pain for the active sprint belongs in reviewed product evidence before becoming a generic opportunity")
    if hint == "project_artifact" and _is_existing_lettuce_context(signal):
        return ("company-brain/product-context.md", "product-specific learning should update reviewed product context")
    return path, reason

_ALWAYS_RECORD_PACKET = RouteProposal(
    path=".lettuce/runs/<run>/packet.md",
    action="record_in_packet",
    reason="every run should preserve the packet, lens selection, evidence, and router decision",
    preview="- Preserve this run as an inspectable Lettuce packet.",
    requires_approval=False,
)


def _preview_for(path: str, signal: LettuceSignal, lenses: list[str]) -> str:
    lens_text = ", ".join(lenses)
    if path == "company-brain/daily-signal-log.md":
        return f"- Lettuce processed `{signal.title}` from {signal.source}; relevant lenses: {lens_text}."
    if path == "company-brain/durable-context.md":
        return f"- Consider preserving durable context from `{signal.title}` after operator review."
    if path == "company-brain/operator-profile.md":
        return f"- Consider whether `{signal.title}` reveals a stable operator preference or constraint before updating operator profile."
    if path == "company-brain/followups.md":
        return f"- [preview] Review whether `{signal.title}` creates or changes an active commitment."
    if path.startswith(".lettuce/"):
        return f"- Keep `{signal.title}` context inside the generated Lettuce packet."
    return f"- Append Lettuce signal note for `{signal.title}`. Relevant lenses: {lens_text}."


def _requires_approval(path: str) -> bool:
    if path.startswith(".lettuce/"):
        return False
    return True


def propose_routes(signal: LettuceSignal, lens_results: list[LensResult]) -> list[RouteProposal]:
    """Central router: synthesize all lens outputs into route proposals.

    Lenses emit route_hints only. This router owns exact surfaces, approval policy,
    and merge behavior.
    """
    by_path: OrderedDict[str, list[str]] = OrderedDict()
    route_reasons: dict[str, list[str]] = {}

    for result in lens_results:
        if not result.fired or result.skipped:
            continue
        for hint in result.route_hints:
            mapped = _map_hint(hint, signal)
            if not mapped:
                continue
            path, reason = mapped
            by_path.setdefault(path, []).append(result.lens)
            route_reasons.setdefault(path, []).append(reason)

    proposals: list[RouteProposal] = [_ALWAYS_RECORD_PACKET]
    for path, lenses in by_path.items():
        reasons = list(dict.fromkeys(route_reasons[path]))
        requires_approval = _requires_approval(path)
        owner, reviewer = _owner_for_path(path, signal)
        proposals.append(
            RouteProposal(
                path=path,
                action="preview_append" if requires_approval else "record_in_packet",
                reason="; ".join(reasons),
                preview=_preview_for(path, signal, lenses),
                requires_approval=requires_approval,
                owner=owner,
                reviewer=reviewer,
            )
        )
    return proposals
