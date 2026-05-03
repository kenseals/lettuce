from __future__ import annotations

import unittest

from lettuce.lenses import LensResult
from lettuce.routers import propose_routes
from lettuce.signal import LettuceSignal


def _result(lens: str, hints: list[str]) -> LensResult:
    return LensResult(lens=lens, fired=True, finding="finding", confidence="high", route_hints=hints)


class RouteSpecificityTests(unittest.TestCase):
    def test_saved_external_lettuce_category_routes_to_project_artifact_not_idea_inbox(self) -> None:
        signal = LettuceSignal(
            title="Saved external YC RFS company brain signal",
            source="saved external x-post",
            body="YC RFS and Baschez category evidence sharpen Lettuce company brain context-control positioning.",
        )

        routes = propose_routes(signal, [_result("product_discovery", ["idea_or_opportunity", "product_artifact"])])
        paths = [route.path for route in routes]

        self.assertIn("company-brain/product-context.md", paths)
        self.assertNotIn("company-brain/opportunity-inbox.md", paths)
        project_route = next(route for route in routes if route.path == "company-brain/product-context.md")
        self.assertEqual(project_route.owner, "Product context owner")
        self.assertIn("saved external/category evidence", project_route.reason)

    def test_new_raw_opportunity_can_still_route_to_idea_inbox(self) -> None:
        signal = LettuceSignal(
            title="Unrelated product wedge",
            source="manual note",
            body="Opportunity: a new startup idea for plumbers who need quote automation.",
        )

        routes = propose_routes(signal, [_result("product_discovery", ["idea_or_opportunity"])])
        paths = [route.path for route in routes]

        self.assertIn("company-brain/opportunity-inbox.md", paths)


if __name__ == "__main__":
    unittest.main()
