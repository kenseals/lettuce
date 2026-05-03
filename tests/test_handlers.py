from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lettuce.handlers import discover_handlers, handlers_for_stream, parse_handler_file


class HandlerSpecTests(unittest.TestCase):
    def test_parse_v0_handler_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "discovery-lens.md"
            path.write_text(
                """---
id: discovery-lens
name: Discovery Lens
type: lens
version: 0.1.0
subscribes:
 - stream: inbox/email
   filter: "from:customer.com"
publishes:
 - stream: brain/discovery
   mode: upsert
   key: "{title}"
triggers:
 - on: new-event
 - on: schedule
   cron: "0 */6 * * *"
batch: true
batch_size: 5
timeout: 45s
model: claude-sonnet-4
description: Finds discovery signal.
tags: [product, discovery]
depends_on: [inbox-normalizer]
---

# Discovery Lens

Return JSON publish actions.
""",
                encoding="utf-8",
            )

            handler = parse_handler_file(path)

        self.assertEqual(handler.id, "discovery-lens")
        self.assertEqual(handler.type, "lens")
        self.assertEqual(handler.subscribes[0].stream, "inbox/email")
        self.assertEqual(handler.subscribes[0].filter, "from:customer.com")
        self.assertEqual(handler.publishes[0].stream, "brain/discovery")
        self.assertEqual(handler.publishes[0].mode, "upsert")
        self.assertEqual(handler.publishes[0].key, "{title}")
        self.assertEqual([trigger.on for trigger in handler.triggers], ["new-event", "schedule"])
        self.assertEqual(handler.triggers[1].cron, "0 */6 * * *")
        self.assertTrue(handler.batch)
        self.assertEqual(handler.batch_size, 5)
        self.assertEqual(handler.timeout, "45s")
        self.assertEqual(handler.tags, ["product", "discovery"])
        self.assertEqual(handler.depends_on, ["inbox-normalizer"])
        self.assertIn("Return JSON", handler.body)

    def test_discover_handlers_scans_handlers_directory_and_matches_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handler_dir = root / "handlers" / "lenses"
            handler_dir.mkdir(parents=True)
            (handler_dir / "default-lens.md").write_text(
                """---
id: default-lens
name: Default Lens
type: lens
version: 0.1.0
subscribes:
 - stream: streams/inbox/direct
publishes:
 - stream: brain/general
---

Notice useful signal.
""",
                encoding="utf-8",
            )
            (handler_dir / "notes.md").write_text("# Not a handler\n", encoding="utf-8")

            handlers = discover_handlers(root)
            matches = handlers_for_stream(handlers, "streams/inbox/direct")

        self.assertEqual([handler.id for handler in handlers], ["default-lens"])
        self.assertEqual([handler.id for handler in matches], ["default-lens"])


if __name__ == "__main__":
    unittest.main()
