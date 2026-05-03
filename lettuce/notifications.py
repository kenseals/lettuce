from __future__ import annotations

from .lenses import LensResult
from .packet import RouteProposal
from .signal import LettuceSignal


def build_notification(signal: LettuceSignal, lens_results: list[LensResult], routes: list[RouteProposal]) -> str:
    fired = [result.lens for result in lens_results if result.fired]
    route_paths = [route.path for route in routes]
    approval_routes = [route.path for route in routes if route.requires_approval]
    next_action = "Inspect packet.md and approve or discard proposed durable routes." if approval_routes else "No operator action needed."
    return "\n".join(
        [
            f"Lettuce processed: {signal.title}",
            f"- Source: {signal.source}",
            f"- Lenses fired: {', '.join(fired) if fired else 'none'}",
            f"- Proposed/applied: {', '.join(route_paths) if route_paths else 'none'}",
            f"- Needs approval: {'yes, ' + ', '.join(approval_routes) if approval_routes else 'no'}",
            f"- Next: {next_action}",
        ]
    )
