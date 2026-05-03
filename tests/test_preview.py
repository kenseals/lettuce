from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lettuce.run_signal as runner


class LettucePreviewTests(unittest.TestCase):
    def test_preview_writes_packet_notification_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_dir = tmp_path / ".orbital"
            signal_path = tmp_path / "signal.md"
            signal_path.write_text(
                "# Operator reopened Lettuce\n\n"
                "The operator made a durable decision: Lettuce dogfood starts today. Build the v0.1 preview CLI and avoid generic memory. "
                "The product opportunity is routing task action context while keeping public proof inspectable.\n",
                encoding="utf-8",
            )

            with patch.object(runner, "LETTUCE_HOME", install_dir):
                packet, paths = runner.run_preview(
                    input_path=str(signal_path),
                    title=None,
                    source="test",
                    mode="preview",
                    include_weak_lenses=True,
                )

            packet_md, packet_json, feedback_json, brief_html, notification, index = paths
            self.assertTrue(packet_md.exists())
            self.assertTrue(packet_json.exists())
            self.assertTrue(feedback_json.exists())
            self.assertTrue(brief_html.exists())
            self.assertTrue(notification.exists())
            self.assertTrue(index.exists())
            self.assertEqual(packet.mode, "preview")
            self.assertIn("Lettuce processed: Operator reopened Lettuce", notification.read_text(encoding="utf-8"))
            data = json.loads(packet_json.read_text(encoding="utf-8"))
            feedback = json.loads(feedback_json.read_text(encoding="utf-8"))
            all_lenses = {lens["lens"] for lens in data["lenses"]}
            fired = {lens["lens"] for lens in data["lenses"] if lens["fired"] and not lens.get("skipped")}
            self.assertEqual(
                all_lenses,
                {"next_action", "operator_memory", "product_discovery", "project_focus_shift", "relationship_account", "risk_open_loop"},
            )
            self.assertIn("product_discovery", fired)
            self.assertIn("operator_memory", fired)
            self.assertNotIn("public_proof", fired)
            self.assertIn("operator_brief", data)
            self.assertIn("feedback_options", data)
            self.assertIn("insights", data)
            insight_kinds = {insight["kind"] for insight in data["insights"]}
            self.assertIn("decision", insight_kinds)
            self.assertIn("opportunity", insight_kinds)
            self.assertEqual(feedback["run_id"], packet.run_id)
            self.assertIn("One review moment", packet_md.read_text(encoding="utf-8"))
            self.assertIn("Decision or direction", packet_md.read_text(encoding="utf-8"))
            self.assertIn("Lettuce operator brief", brief_html.read_text(encoding="utf-8"))
            self.assertIn("Extracted signal", brief_html.read_text(encoding="utf-8"))
            self.assertIn("Lettuce feed", index.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
