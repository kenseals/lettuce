from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lettuce.ai_lens_runner import parse_ai_lens_results
from lettuce.lenses import load_lens_definitions, select_lenses, run_lenses
import lettuce.run_signal as runner
from lettuce.signal import LettuceSignal


class AILensRunnerTests(unittest.TestCase):
    def _signal(self) -> LettuceSignal:
        return LettuceSignal(
            title="Revenue wedge decision",
            source="test",
            body="The operator decided we should validate a painful buyer workflow before building more infrastructure.",
            input_path=None,
        )

    def test_ai_output_parses_to_structured_lens_result(self) -> None:
        signal = self._signal()
        definitions = load_lens_definitions()
        selected, _ = select_lenses(signal, definitions, max_lenses=1)
        definition = selected[0][0]
        raw = json.dumps(
            {
                "lenses": [
                    {
                        "lens_id": definition.id,
                        "fired": True,
                        "confidence": "high",
                        "finding": "The signal changes product validation focus.",
                        "evidence": ["validate a painful buyer workflow"],
                        "operator_implication": "Preview a project-context update, but do not apply it yet.",
                        "route_hints": ["idea_or_opportunity"],
                        "proposed_updates": [
                            {"surface": "ideas", "action": "append", "reason": "candidate revenue wedge"}
                        ],
                        "anti_actions": ["Do not create a queue commitment yet."],
                        "open_questions": ["Which buyer segment is reachable first?"],
                    }
                ]
            }
        )

        results = parse_ai_lens_results(raw, selected=selected)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].runner, "ai")
        self.assertTrue(results[0].fired)
        self.assertEqual(results[0].proposed_updates[0]["surface"], "ideas")
        self.assertIn("Do not create", results[0].anti_actions[0])

    def test_ai_runner_falls_back_without_command(self) -> None:
        with patch.dict("os.environ", {"LETTUCE_AI_LENS_COMMAND": ""}, clear=False):
            results = run_lenses(self._signal(), runner="ai", max_lenses=1)

        self.assertTrue(results)
        self.assertTrue(any(result.runner == "deterministic-fallback" for result in results))
        self.assertIn("AI runner failed", results[0].implication)

    def test_cli_ai_mode_stays_preview_only_on_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            install_dir = tmp_path / ".lettuce"
            signal_path = tmp_path / "signal.md"
            signal_path.write_text("# Signal\n\nWe should validate customer pain before shipping.", encoding="utf-8")

            with patch.object(runner, "LETTUCE_HOME", install_dir), patch.dict("os.environ", {"LETTUCE_AI_LENS_COMMAND": ""}, clear=False):
                packet, paths = runner.run_preview(
                    input_path=str(signal_path),
                    title=None,
                    source="test",
                    mode="preview",
                    lens_runner="ai",
                )

            self.assertEqual(packet.mode, "preview")
            self.assertTrue(paths[0].exists())
            data = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertTrue(any(lens["runner"] == "deterministic-fallback" for lens in data["lenses"]))
            self.assertIn("Preview mode only", paths[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
