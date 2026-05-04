from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from lettuce.openclaw_provider import build_prompt, extract_json_object, run_openclaw
from lettuce.protocol_runtime import add_handler, add_stream_event, approve_review, configure_source, configure_subscription, decline_review, import_source_event, ingest_email_signal, init_repo, list_reviews, read_logs, read_stream_events, run_once, status


class ProtocolRuntimeTests(unittest.TestCase):
    def test_init_scaffolds_personal_lettuce_repo_and_discovers_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            self.assertTrue((repo / "lettuce.yml").exists())
            self.assertTrue((repo / "handlers/lenses/default-lens.md").exists())
            self.assertTrue((repo / "handlers/routers/brain-router.md").exists())
            self.assertTrue((repo / "streams/inbox/direct/.gitkeep").exists())
            self.assertTrue((repo / "brain/general/.gitkeep").exists())
            self.assertIn("operator: ken", (repo / "lettuce.yml").read_text(encoding="utf-8"))
            self.assertIn(".lettuce/", (repo / ".gitignore").read_text(encoding="utf-8"))

    def test_default_lens_prompts_include_skip_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            discovery = (repo / "handlers/lenses/discovery-lens.md").read_text(encoding="utf-8")
            accounts = (repo / "handlers/lenses/accounts-lens.md").read_text(encoding="utf-8")

            self.assertIn("beyond one account's immediate next step", discovery)
            self.assertIn("Skip pure sales follow-up", discovery)
            self.assertIn("named customer, prospect, account", accounts)
            self.assertIn("Skip general product feedback", accounts)

    def test_ingest_direct_cli_writes_agent_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "ingest-direct",
                    str(repo),
                    "--title",
                    "Operator direction",
                    "--body",
                    "Focus Lettuce on agent-operated onboarding.",
                    "--source",
                    "openclaw.telegram",
                    "--surface",
                    "telegram",
                    "--message-id",
                    "10462",
                    "--chat-id",
                    "openclaw-topic-1",
                    "--sender",
                    "ken",
                    "--consent",
                    "operator-direct-request",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            text = Path(output["event_path"]).read_text(encoding="utf-8")

            self.assertEqual(output["source"], "openclaw.telegram")
            self.assertEqual(output["consent_basis"], "operator-direct-request")
            self.assertIn("source_type: direct", text)
            self.assertIn("surface: telegram", text)
            self.assertIn("message_id: 10462", text)
            self.assertIn("chat_id: openclaw-topic-1", text)
            self.assertIn("sender: ken", text)
            self.assertIn("consent_basis: operator-direct-request", text)
            self.assertIn("provenance: agent-observed", text)
            self.assertIn("ingestion_boundary: operator-provided", text)
            self.assertIn("external_action: false", text)
            self.assertIn("Focus Lettuce", text)

    def test_ingest_email_cli_writes_email_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            body_file = Path(tmp) / "email.md"
            body_file.write_text("OpenAI says Codex can run persistent automations.", encoding="utf-8")
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "ingest-email",
                    str(repo),
                    "--subject",
                    "Codex Product Update",
                    "--body-file",
                    str(body_file),
                    "--message-id",
                    "msg-123",
                    "--thread-id",
                    "thread-456",
                    "--from",
                    "OpenAI <noreply@email.openai.com>",
                    "--to",
                    "ken@example.com",
                    "--email-timestamp",
                    "2026-05-01T17:58:03Z",
                    "--source-url",
                    "https://mail.google.com/mail/#all/msg-123",
                    "--forwarded-by",
                    "ken",
                    "--consent",
                    "operator-forwarded-email",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            text = Path(output["event_path"]).read_text(encoding="utf-8")

            self.assertEqual(output["source"], "openclaw.email.forwarded")
            self.assertEqual(output["consent_basis"], "operator-forwarded-email")
            self.assertIn("source_type: email", text)
            self.assertIn("provenance: operator-forwarded", text)
            self.assertIn("ingestion_boundary: operator-selected-email", text)
            self.assertIn("message_id: msg-123", text)
            self.assertIn("thread_id: thread-456", text)
            self.assertIn("email_from: OpenAI <noreply@email.openai.com>", text)
            self.assertIn("email_to: ken@example.com", text)
            self.assertIn("email_timestamp: 2026-05-01T17:58:03Z", text)
            self.assertIn("source_url: https://mail.google.com/mail/#all/msg-123", text)
            self.assertIn("forwarded_by: ken", text)
            self.assertIn("OpenAI says Codex", text)

    def test_ingest_email_rejects_blank_subject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            with self.assertRaises(ValueError):
                ingest_email_signal(repo, subject=" ", body="body", consent_basis="operator-forwarded-email")

    def test_onboard_cli_initializes_ingests_and_runs_first_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "onboard",
                    str(repo),
                    "--org",
                    "acme",
                    "--operator",
                    "ken",
                    "--title",
                    "First signal",
                    "--body",
                    "Customer wants agent-operated setup.",
                    "--source",
                    "openclaw.telegram",
                    "--surface",
                    "telegram",
                    "--message-id",
                    "10465",
                    "--sender",
                    "ken",
                    "--consent",
                    "operator-direct-request",
                    "--commit",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            event_text = Path(output["event_path"]).read_text(encoding="utf-8")
            git_status = subprocess.run(["git", "status", "--short"], cwd=repo, check=True, capture_output=True, text=True).stdout

            self.assertTrue(output["initialized"])
            self.assertTrue((repo / "lettuce.yml").exists())
            self.assertIn("source: openclaw.telegram", event_text)
            self.assertIn("consent_basis: operator-direct-request", event_text)
            self.assertEqual(output["run"]["handlers"], 3)
            self.assertEqual(len(output["run"]["runs"]), 3)
            self.assertGreaterEqual(output["status"]["log_entries"], 3)
            self.assertEqual(git_status.strip(), "")
            self.assertIn("lettuce: running", completed.stderr)

    def test_onboard_cli_accepts_handler_command_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            script = Path(tmp) / "selective_handler.py"
            script.write_text(
                """
import json
import sys
payload = json.loads(sys.stdin.read())
context = payload["payload"]["context"]
event = payload["payload"]["events"][0]
if context["handler_id"] == "accounts-lens":
    print(json.dumps({"skip": True, "notes": ["not account context"]}))
else:
    stream = payload["payload"]["publishes"][0]["stream"]
    print(json.dumps({
        "skip": False,
        "publishes": [{
            "stream": stream,
            "frontmatter": {"title": f"Handled {context['handler_id']}"},
            "body": f"Handled {event['id']} with {context['handler_id']}"
        }],
        "notes": ["custom command"]
    }))
""".strip(),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "onboard",
                    str(repo),
                    "--org",
                    "acme",
                    "--operator",
                    "ken",
                    "--title",
                    "Provider command signal",
                    "--body",
                    "This should use the explicit provider command.",
                    "--source",
                    "openclaw.telegram",
                    "--surface",
                    "telegram",
                    "--sender",
                    "ken",
                    "--consent",
                    "operator-direct-request",
                    "--handler-command",
                    f"python3 {script}",
                    "--commit",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            runs = {run["handler_id"]: run for run in output["run"]["runs"]}

            self.assertTrue(runs["accounts-lens"]["skipped"])
            self.assertFalse(runs["default-lens"]["skipped"])
            self.assertFalse(runs["discovery-lens"]["skipped"])
            self.assertEqual(runs["accounts-lens"]["publishes"], [])
            self.assertIn("custom command", runs["default-lens"]["notes"])

    def test_cli_rejects_openclaw_provider_and_handler_command_together(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Conflict", body="Conflict")

            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "run",
                    str(repo),
                    "--openclaw-provider",
                    "--handler-command",
                    "python3 fake.py",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("use either --openclaw-provider or --handler-command", completed.stderr)

    def test_onboard_cli_reads_first_signal_from_body_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            body_file = Path(tmp) / "first-signal.md"
            body_file.write_text("Customer pasted a longer signal about stale agent context.\n\nIt spans lines.", encoding="utf-8")

            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "onboard",
                    str(repo),
                    "--org",
                    "acme",
                    "--operator",
                    "ken",
                    "--title",
                    "First file-backed signal",
                    "--body-file",
                    str(body_file),
                    "--source",
                    "openclaw.telegram",
                    "--surface",
                    "telegram",
                    "--sender",
                    "ken",
                    "--consent",
                    "operator-direct-request",
                    "--no-run",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            event_text = Path(output["event_path"]).read_text(encoding="utf-8")

            self.assertIn("First file-backed signal", event_text)
            self.assertIn("It spans lines.", event_text)
            self.assertIsNone(output["run"])

    def test_setup_cli_runs_interactive_happy_path_with_manual_and_email_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-walm-e-ken"
            setup_input = "\n".join(
                [
                    "y",
                    "WALM-E",
                    "ken",
                    str(repo),
                    "operator-direct-request",
                    "y",
                    "walm-e-email",
                    "walm-e@example.com",
                    "first-5-operator-approved",
                    "skip personal mail",
                    "n",
                    "Setup signal",
                    "WALM-E needs Lettuce onboarding to configure manual ingestion and email source intent.",
                    ".",
                    "",
                ]
            )

            completed = subprocess.run(
                ["python3", "-m", "lettuce.cli", "setup", "--commit"],
                input=setup_input,
                check=True,
                capture_output=True,
                text=True,
            )

            git_status = subprocess.run(["git", "status", "--short"], cwd=repo, check=True, capture_output=True, text=True).stdout

            self.assertIn("Lettuce is a work-context layer", completed.stdout)
            self.assertIn("Manual/direct ingestion is ready", completed.stdout)
            self.assertIn("pending reviews", completed.stdout)
            self.assertTrue((repo / "lettuce.yml").exists())
            self.assertTrue((repo / "sources" / "direct-manual-direct.md").exists())
            self.assertTrue((repo / "sources" / "email-walm-e-email.md").exists())
            self.assertTrue(any((repo / "reviews" / "pending").glob("*.md")))
            self.assertEqual(git_status.strip(), "")

    def test_cli_rejects_body_and_body_file_together(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            body_file = Path(tmp) / "signal.md"
            body_file.write_text("file body", encoding="utf-8")

            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "ingest-direct",
                    str(repo),
                    "--title",
                    "Conflicting body args",
                    "--body",
                    "inline body",
                    "--body-file",
                    str(body_file),
                    "--source",
                    "openclaw.telegram",
                    "--surface",
                    "telegram",
                    "--consent",
                    "operator-direct-request",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("use either --body or --body-file", completed.stderr)

    def test_file_source_rejects_body_file_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            source_file = Path(tmp) / "source.md"
            source_file.write_text("source body", encoding="utf-8")
            body_file = Path(tmp) / "body.md"
            body_file.write_text("wrong body", encoding="utf-8")

            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "add-source",
                    "file",
                    str(repo),
                    "--input",
                    str(source_file),
                    "--body-file",
                    str(body_file),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("only valid for stdin sources", completed.stderr)

    def test_add_handler_scaffolds_discoverable_markdown_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            handler_path = add_handler(
                repo,
                "lens",
                handler_id="pricing-lens",
                name="Pricing Lens",
                publishes="brain/pricing",
                model="claude-haiku-4-5",
            )
            result = subprocess.run(
                ["python3", "-m", "lettuce.cli", "discover", str(repo)],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(handler_path.exists())
            text = handler_path.read_text(encoding="utf-8")
            self.assertIn("id: pricing-lens", text)
            self.assertIn("type: lens", text)
            self.assertIn("stream: brain/pricing", text)
            self.assertIn("model: claude-haiku-4-5", text)
            self.assertIn('"id": "pricing-lens"', result.stdout)

    def test_add_stream_event_and_run_once_writes_brain_markdown_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            event_path = add_stream_event(
                repo,
                title="Pricing question from BigCorp",
                body="Anna asked whether enterprise pricing can be clearer for agents.",
                source="manual",
            )

            events = read_stream_events(repo, "streams/inbox/direct")
            result = run_once(repo, stream="streams/inbox/direct", commit=False)
            second = run_once(repo, stream="streams/inbox/direct", commit=False)

            self.assertTrue(event_path.exists())
            self.assertEqual(len(events), 1)
            self.assertEqual(result.handlers, 3)
            self.assertEqual(result.events, 1)
            self.assertEqual(len(result.runs), 3)
            self.assertFalse(any(run.errors for run in result.runs))
            self.assertEqual(second.runs, [])
            published = [publish for run in result.runs for publish in run.publishes]
            self.assertTrue(published)
            for publish in published:
                path = Path(publish.path)
                self.assertTrue(path.exists())
                text = path.read_text(encoding="utf-8")
                self.assertIn("handler_version: 0.1.0", text)
                self.assertIn("source_event:", text)
                self.assertIn("provider: default-adapter", text)
            checkpoints = json.loads((repo / ".lettuce/checkpoints.json").read_text(encoding="utf-8"))
            self.assertIn("default-lens:streams/inbox/direct", checkpoints)
            self.assertTrue((repo / ".lettuce/runtime.log").read_text(encoding="utf-8").strip())

    def test_run_once_review_mode_writes_pending_reviews_not_brain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(
                repo,
                title="Review gate signal",
                body="Customer asks for review before any durable context update.",
                source="manual",
            )

            result = run_once(repo, stream="streams/inbox/direct", review=True, commit=False)
            reviews = list_reviews(repo)

            self.assertFalse(any(run.errors for run in result.runs))
            self.assertTrue(reviews)
            self.assertTrue(all(review.status == "pending" for review in reviews))
            self.assertTrue(all(review.target_stream.startswith("brain/") for review in reviews))
            self.assertTrue(all("reviews/pending" in publish.path for run in result.runs for publish in run.publishes))
            self.assertFalse(list((repo / "brain/general").glob("*.md")))

    def test_review_approve_publishes_target_and_moves_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Approval signal", body="Customer wants audited review gates.", source="manual")
            run_once(repo, stream="streams/inbox/direct", review=True, commit=False)
            review = list_reviews(repo)[0]

            result = approve_review(repo, review.id, operator="ken", commit=False)
            approved = list_reviews(repo, status="approved")

            self.assertTrue(Path(result.path).exists())
            self.assertEqual(result.stream, review.target_stream)
            self.assertEqual(result.review_id, review.id)
            self.assertFalse(Path(review.path).exists())
            self.assertTrue(approved)
            self.assertIn("review_id: " + review.id, Path(result.path).read_text(encoding="utf-8"))

    def test_review_protocol_fields_cannot_be_overwritten_by_handler_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "lettuce-acme-ken"
            script = tmp_path / "reserved_frontmatter_handler.py"
            script.write_text(
                """
import json
print(json.dumps({
    "skip": False,
    "publishes": [{
        "stream": "brain/general",
        "frontmatter": {
            "id": "handler-id-should-not-win",
            "source_event": "handler-source-should-not-win",
            "review_id": "handler-review-should-not-win",
            "title": "Reserved field signal"
        },
        "body": "Handler tried to override protocol fields."
    }]
}))
""".strip(),
                encoding="utf-8",
            )
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Reserved field signal", body="Preserve protocol-owned frontmatter.", source="manual")

            with patch.dict("os.environ", {"LETTUCE_HANDLER_COMMAND": f"python3 {script}"}, clear=False):
                run_once(repo, stream="streams/inbox/direct", review=True, commit=False)
            review = list_reviews(repo)[0]
            result = approve_review(repo, review.id, operator="ken", commit=False)
            published_text = Path(result.path).read_text(encoding="utf-8")

            self.assertEqual(review.id, result.review_id)
            self.assertNotEqual(review.id, "handler-id-should-not-win")
            self.assertIn(f"review_id: {review.id}", published_text)
            self.assertIn("source_event: 202", published_text)
            self.assertNotIn("handler-source-should-not-win", published_text)
            self.assertNotIn("handler-review-should-not-win", published_text)

    def test_review_decline_moves_review_without_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Decline signal", body="No durable update should be applied.", source="manual")
            run_once(repo, stream="streams/inbox/direct", review=True, commit=False)
            review = list_reviews(repo)[0]

            result = decline_review(repo, review.id, reason="too noisy", operator="ken", commit=False)

            self.assertEqual(result.status, "declined")
            self.assertFalse(Path(review.path).exists())
            self.assertTrue(Path(result.path).exists())
            self.assertIn("decline_reason: too noisy", Path(result.path).read_text(encoding="utf-8"))
            self.assertFalse(list((repo / review.target_stream).glob("*.md")))

    def test_review_cli_lists_and_approves_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="CLI review signal", body="Operator needs approve and decline commands.", source="manual")
            run_completed = subprocess.run(
                ["python3", "-m", "lettuce.cli", "run", str(repo), "--review"],
                check=True,
                capture_output=True,
                text=True,
            )
            run_output = json.loads(run_completed.stdout)
            review_id = next(review_id for run in run_output["runs"] for review_id in run.get("review_ids", []))

            list_completed = subprocess.run(
                ["python3", "-m", "lettuce.cli", "reviews", str(repo)],
                check=True,
                capture_output=True,
                text=True,
            )
            approve_completed = subprocess.run(
                ["python3", "-m", "lettuce.cli", "review-approve", str(repo), review_id, "--operator", "ken"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(json.loads(list_completed.stdout)["reviews"][0]["id"], review_id)
            self.assertEqual(json.loads(approve_completed.stdout)["review_id"], review_id)

    def test_import_source_file_writes_event_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "lettuce-acme-ken"
            source_file = tmp_path / "call-note.md"
            source_file.write_text("# Customer call\n\nAnna asked whether agent context can stay fresh.", encoding="utf-8")
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            result = import_source_event(repo, "file", input_path=source_file)
            events = read_stream_events(repo, "streams/inbox/direct")

            self.assertEqual(result.source_type, "file")
            self.assertEqual(result.title, "Customer call")
            self.assertEqual(result.source, "file:call-note.md")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].frontmatter["source_type"], "file")
            self.assertEqual(events[0].frontmatter["source_path"], str(source_file.resolve()))
            self.assertIn("Anna asked", events[0].body)

    def test_configure_source_writes_markdown_source_record_and_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            result = configure_source(repo, "email", name="support-forward", metadata={"address": "lettuce-support@example.com"})
            config_path = Path(result.config_path)
            text = config_path.read_text(encoding="utf-8")

            self.assertEqual(result.source_type, "email")
            self.assertEqual(result.stream, "streams/inbox/email")
            self.assertTrue(config_path.exists())
            self.assertTrue((repo / "streams/inbox/email/.gitkeep").exists())
            self.assertIn("type: email", text)
            self.assertIn("address: lettuce-support@example.com", text)
            self.assertIn("stream: streams/inbox/email", text)
            self.assertIn("access_status: unknown", text)
            self.assertIn("access_owner: operator-agent", text)

    def test_add_source_cli_configures_transcript_source_with_setup_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "add-source",
                    "granola",
                    str(repo),
                    "--name",
                    "sales-calls",
                    "--workspace",
                    "ken-granola",
                    "--access-status",
                    "needs_setup",
                    "--sample-policy",
                    "first-3-operator-approved",
                    "--privacy-notes",
                    "skip recruiting and legal calls",
                    "--setup-next-action",
                    "connect existing Granola export or MCP before polling",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            text = Path(output["config_path"]).read_text(encoding="utf-8")

            self.assertEqual(output["source_type"], "granola")
            self.assertEqual(output["stream"], "streams/inbox/transcripts")
            self.assertEqual(output["access_status"], "needs_setup")
            self.assertIn("workspace: ken-granola", text)
            self.assertIn("sample_policy: first-3-operator-approved", text)
            self.assertIn("privacy_notes: skip recruiting and legal calls", text)
            self.assertIn("setup_next_action: connect existing Granola export or MCP before polling", text)

    def test_add_source_cli_configures_telegram_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "add-source",
                    "telegram",
                    str(repo),
                    "--name",
                    "ken-bot",
                    "--bot",
                    "@lettuce_ken_bot",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            text = Path(output["config_path"]).read_text(encoding="utf-8")

            self.assertEqual(output["source_type"], "telegram")
            self.assertEqual(output["stream"], "streams/inbox/direct")
            self.assertEqual(output["status"], "configured")
            self.assertIn("bot: @lettuce_ken_bot", text)

    def test_configure_subscription_requires_initialized_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"

            with self.assertRaises(FileNotFoundError):
                configure_subscription(repo, "github.com/acme/lettuce-acme", stream="brain/decisions")

    def test_configure_subscription_writes_markdown_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)

            result = configure_subscription(repo, "github.com/acme/lettuce-acme", stream="brain/decisions", name="acme-decisions", policy="read-only")
            text = Path(result.subscription_path).read_text(encoding="utf-8")

            self.assertEqual(result.remote, "github.com/acme/lettuce-acme")
            self.assertEqual(result.stream, "brain/decisions")
            self.assertEqual(result.status, "configured")
            self.assertIn("remote: github.com/acme/lettuce-acme", text)
            self.assertIn("stream: brain/decisions", text)
            self.assertIn("policy: read-only", text)

    def test_subscribe_cli_reports_clean_error_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "subscribe",
                    str(repo),
                    "--remote",
                    "github.com/acme/lettuce-acme",
                    "--stream",
                    "brain/customers",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("error: not a Lettuce repo", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_subscribe_cli_configures_remote_stream_subscription(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "subscribe",
                    str(repo),
                    "--remote",
                    "github.com/acme/lettuce-acme",
                    "--stream",
                    "brain/customers",
                    "--local-stream",
                    "streams/shared/customers",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            text = Path(output["subscription_path"]).read_text(encoding="utf-8")

            self.assertEqual(output["remote"], "github.com/acme/lettuce-acme")
            self.assertEqual(output["stream"], "brain/customers")
            self.assertEqual(output["status"], "configured")
            self.assertIn("local_stream: streams/shared/customers", text)

    def test_add_source_cli_imports_stdin_and_can_run_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "lettuce.cli",
                    "add-source",
                    "stdin",
                    str(repo),
                    "--title",
                    "Stdin customer signal",
                    "--body",
                    "Customer wants source connectors before more UI polish.",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = json.loads(completed.stdout)
            result = run_once(repo, stream="streams/inbox/direct", commit=False)

            self.assertEqual(output["source_type"], "stdin")
            self.assertEqual(output["source"], "stdin")
            self.assertTrue(Path(output["event_path"]).exists())
            self.assertFalse(any(run.errors for run in result.runs))
            self.assertTrue(any(run.publishes for run in result.runs))

    def test_run_once_can_commit_events_and_publishes_to_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=True)
            add_stream_event(repo, title="Support escalation", body="Customer needs follow-up on stale support docs.", commit=True)

            result = run_once(repo, stream="streams/inbox/direct", commit=True)
            log = subprocess.run(["git", "log", "--oneline"], cwd=repo, check=True, capture_output=True, text=True).stdout
            status = subprocess.run(["git", "status", "--short"], cwd=repo, check=True, capture_output=True, text=True).stdout

            self.assertTrue(any(run.committed for run in result.runs))
            self.assertIn("lettuce init scaffold", log)
            self.assertIn("event:", log)
            self.assertIn("default-lens:", log)
            self.assertEqual(status.strip(), "")

    def test_run_once_reuses_existing_publish_when_checkpoint_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "lettuce-acme-ken"
            script = tmp_path / "stable_handler.py"
            script.write_text(
                """
import json
import sys
payload = json.loads(sys.stdin.read())
context = payload["payload"]["context"]
event = payload["payload"]["events"][0]
stream = payload["payload"]["publishes"][0]["stream"]
print(json.dumps({
    "skip": False,
    "publishes": [{
        "stream": stream,
        "frontmatter": {"title": f"Stable {context['handler_id']}"},
        "body": f"Stable publish for {event['id']}"
    }],
    "notes": ["stable publish"]
}))
""".strip(),
                encoding="utf-8",
            )
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Interrupted signal", body="Resume should not duplicate publishes.")

            with patch.dict("os.environ", {"LETTUCE_HANDLER_COMMAND": f"python3 {script}"}, clear=False):
                first = run_once(repo, stream="streams/inbox/direct", commit=False)
            first_paths = sorted(publish.path for run in first.runs for publish in run.publishes)
            (repo / ".lettuce/checkpoints.json").write_text("{}\n", encoding="utf-8")
            with patch.dict("os.environ", {"LETTUCE_HANDLER_COMMAND": f"python3 {script}"}, clear=False):
                second = run_once(repo, stream="streams/inbox/direct", commit=False)
            second_paths = sorted(publish.path for run in second.runs for publish in run.publishes)

            self.assertEqual(len(first_paths), 3)
            self.assertEqual(second_paths, first_paths)
            for stream in ["brain/customers", "brain/discovery", "brain/general"]:
                self.assertEqual(len(list((repo / stream).glob("*.md"))), 1)

    def test_run_once_uses_handler_command_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "lettuce-acme-ken"
            script = tmp_path / "handler.py"
            script.write_text(
                """
import json
import sys
payload = json.loads(sys.stdin.read())
event = payload["payload"]["events"][0]
print(json.dumps({
    "skip": False,
    "publishes": [{
        "stream": "brain/general",
        "frontmatter": {"title": "Command handled", "source_event": event["id"]},
        "body": "Handled by command"
    }],
    "notes": ["command runner"]
}))
""".strip(),
                encoding="utf-8",
            )
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Command signal", body="Run with command.")

            progress: list[dict[str, object]] = []
            with patch.dict("os.environ", {"LETTUCE_HANDLER_COMMAND": f"python3 {script}"}, clear=False):
                result = run_once(repo, stream="streams/inbox/direct", commit=False, progress=progress.append)

            published_text = "\n".join(Path(publish.path).read_text(encoding="utf-8") for run in result.runs for publish in run.publishes)
            logs = read_logs(repo, limit=1)
            self.assertIn("Handled by command", published_text)
            self.assertTrue(any("command runner" in run.notes for run in result.runs))
            self.assertTrue(all(run.duration_ms >= 0 for run in result.runs))
            self.assertIn("duration_ms", logs[-1])
            self.assertEqual(progress[0]["phase"], "start")
            self.assertEqual(progress[1]["phase"], "finish")

    def test_handler_command_timeout_records_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "lettuce-acme-ken"
            script = tmp_path / "slow_handler.py"
            script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Slow signal", body="This handler should time out.")

            with patch.dict("os.environ", {"LETTUCE_HANDLER_COMMAND": f"python3 {script}", "LETTUCE_HANDLER_TIMEOUT_SECONDS": "1"}, clear=False):
                result = run_once(repo, stream="streams/inbox/direct", commit=False)

            self.assertTrue(result.runs)
            self.assertTrue(all(run.errors for run in result.runs))
            self.assertTrue(all("timed out after 1s" in run.errors[0] for run in result.runs))
            self.assertFalse(any("Traceback" in run.errors[0] for run in result.runs))

    def test_status_and_logs_report_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "lettuce-acme-ken"
            init_repo(repo, org="acme", operator="ken", initialize_git=False)
            add_stream_event(repo, title="Status signal", body="Check status and logs.")
            run_once(repo, stream="streams/inbox/direct", commit=False)

            current = status(repo)
            logs = read_logs(repo, limit=2)

            self.assertEqual(current.handlers, 6)
            self.assertEqual(current.streams["streams/inbox/direct"], 1)
            self.assertGreaterEqual(current.log_entries, 1)
            self.assertTrue(current.last_log)
            self.assertEqual(len(logs), 2)

    def test_openclaw_provider_builds_prompt_and_extracts_fenced_json(self) -> None:
        invocation = {
            "system": "Only publish clear account signal.",
            "payload": {
                "events": [{"id": "evt-1", "body": "Anna asked for clearer pricing."}],
                "publishes": [{"stream": "brain/accounts", "mode": "append", "key": ""}],
                "context": {"handler_id": "accounts-lens", "model": "claude-haiku-4-5"},
            },
        }

        prompt = build_prompt(invocation)
        parsed = extract_json_object('```json\n{"skip": true, "notes": ["nothing"]}\n```')

        self.assertIn("HANDLER PROMPT", prompt)
        self.assertIn("Only publish clear account signal.", prompt)
        self.assertIn("INVOCATION PAYLOAD JSON", prompt)
        self.assertEqual(parsed["skip"], True)
        self.assertEqual(parsed["notes"], ["nothing"])

    def test_openclaw_provider_invokes_model_cli_and_returns_handler_json(self) -> None:
        invocation = {
            "system": "Publish one useful note.",
            "payload": {
                "events": [{"id": "evt-2", "body": "Customer wants a repair sprint."}],
                "publishes": [{"stream": "brain/discovery", "mode": "append", "key": ""}],
                "context": {"handler_id": "discovery-lens", "model": "anthropic/claude-haiku-4-5"},
            },
        }

        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                "Config warnings:\n"
                + json.dumps(
                    {
                        "outputs": [
                            {
                                "text": json.dumps(
                                    {
                                        "skip": False,
                                        "publishes": [
                                            {
                                                "stream": "brain/discovery",
                                                "frontmatter": {"title": "Repair sprint signal"},
                                                "body": "Customer wants a repair sprint.",
                                            }
                                        ],
                                    }
                                )
                            }
                        ]
                    }
                )
            ),
            stderr="",
        )

        with patch("lettuce.openclaw_provider.subprocess.run", return_value=completed) as run:
            output = run_openclaw(invocation)

        self.assertFalse(output["skip"])
        self.assertEqual(output["publishes"][0]["stream"], "brain/discovery")
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["openclaw", "capability", "model", "run"])
        self.assertIn("--gateway", command)
        self.assertIn("--json", command)


if __name__ == "__main__":
    unittest.main()
