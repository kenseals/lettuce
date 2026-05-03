from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "synthetic-corpus"


class SyntheticCorpusTests(unittest.TestCase):
    def test_manifest_covers_expected_signal_mix(self) -> None:
        manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
        signals = manifest["signals"]
        source_types = {signal["source_type"] for signal in signals}

        self.assertEqual(len(signals), 10)
        self.assertIn("email", source_types)
        self.assertIn("direct", source_types)
        self.assertIn("transcript", source_types)
        self.assertIn("work-system", source_types)
        self.assertTrue(any(not signal["expected_handlers"] for signal in signals))

    def test_runner_defaults_to_review_mode(self) -> None:
        text = (CORPUS / "run.sh").read_text(encoding="utf-8")

        self.assertIn("review=${LETTUCE_SYNTHETIC_REVIEW:-true}", text)
        self.assertIn("run_args+=(--review)", text)
        self.assertIn("reviews \"$repo\"", text)

    def test_manifest_files_exist_and_are_public_safe(self) -> None:
        manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
        forbidden_terms = [
            "Real Customer Inc",
            "@gmail.com",
            "personal-owner-handle",
            "agentmail.to",
        ]

        for signal in manifest["signals"]:
            path = CORPUS / signal["file"]
            self.assertTrue(path.exists(), signal["file"])
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# "), signal["file"])
            self.assertGreater(len(text.strip()), 200, signal["file"])
            for forbidden in forbidden_terms:
                self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
