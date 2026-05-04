from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import lettuce.runtime as runtime


class LettuceRuntimeTests(unittest.TestCase):
    def test_smoke_uses_seeded_local_json_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                result = runtime.smoke()
                self.assertTrue(result["ok"])
                self.assertEqual(result["missing"], [])
                self.assertTrue((state_dir / "state.json").exists())
                state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
                self.assertIn("sources", state)
                self.assertIn("feedback_actions", state)
                self.assertIn("organization", state)
                self.assertIn("company_brain", state)
                self.assertIn("destinations", state)
                self.assertIn("organizations", state)
                self.assertEqual(state["sources"][0]["id"], "api-client")
                self.assertEqual(state["sources"][0]["name"], "Local API client")
                self.assertEqual(state["sources"][1]["id"], "manual-paste")
                self.assertEqual(state["destinations"][0]["name"], "Company Brain")

    def test_feedback_action_persists_to_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                entry = runtime.record_feedback({"action": "edit", "signal_id": "demo", "note": "tighten route"})
                state = runtime.load_state()
                self.assertEqual(entry["action"], "edit")
                self.assertEqual(state["feedback"][0]["note"], "tighten route")
                self.assertIn("Feedback captured", state["audit"][0]["title"])

    def test_feedback_rejects_unknown_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                with self.assertRaises(ValueError):
                    runtime.record_feedback({"action": "ship-it"})

    def test_demo_signal_writes_runtime_packet_and_updates_company_brain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
            ):
                entry = runtime.add_demo_signal()
                detail = runtime.signal_detail("company-brain-control-problem")
                state = runtime.load_state()

            self.assertIn("packet", entry["title"])
            packet_path = Path(detail["context_update"]["packet_path"])
            self.assertTrue(packet_path.exists())
            self.assertIn("runtime/runs", packet_path.as_posix())
            self.assertIn("Better organized Notion", detail["input"]["body"])
            self.assertTrue(detail["lens_findings"])
            self.assertTrue(detail["route_proposals"])
            self.assertEqual(detail["route_proposals"][0]["id"], "company_brain:reviewed-context-update")
            self.assertEqual(detail["route_proposals"][0]["destination"], "company_brain")
            self.assertEqual(detail["route_proposals"][0]["apply_scope"], "local_only")
            self.assertEqual(detail["context_update"]["status"], "company_brain_updated")
            self.assertIn("applied the local Company Brain update", detail["context_update"]["result"])
            self.assertTrue(detail["context_update"]["company_changes"])
            self.assertTrue(detail["context_update"]["update_logs"])
            self.assertIn("raw_signal_path", detail["context_update"]["provenance_chain"])
            self.assertIn("company_profile:company_profile", detail["context_update"]["provenance_chain"]["updated_objects"])
            self.assertEqual(state["organization"]["status"], "signal processed")
            self.assertEqual(state["signals"][0]["feedback"], "Company brain updated directly")

    def test_approve_feedback_applies_company_brain_update_with_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
            ):
                runtime.add_demo_signal()
                entry = runtime.record_feedback({"action": "approve", "signal_id": "company-brain-control-problem", "note": "looks right", "route_id": "company_brain:reviewed-context-update"})
                detail = runtime.signal_detail("company-brain-control-problem")
                state = runtime.load_state()

            self.assertEqual(entry["action"], "approve")
            self.assertEqual(detail["context_update"]["status"], "company_brain_updated")
            self.assertTrue(detail["context_update"]["company_changes"])
            self.assertTrue(detail["context_update"]["update_logs"])
            self.assertIn("diff", detail["context_update"]["review_diff"])
            self.assertEqual(detail["review_decision"]["action"], "approve")
            self.assertEqual(detail["review_decision"]["route_id"], "company_brain:reviewed-context-update")
            self.assertIn("company_profile:company_profile", detail["context_update"]["provenance_chain"]["updated_objects"])
            self.assertEqual(state["organization"]["status"], "signal processed")
            self.assertEqual(state["company_brain"]["open_loops_risks"][0]["status"], "mitigated in app runtime")
            self.assertIn("company-brain integration", state["company_brain"]["projects_products"][0]["status"])
            self.assertEqual(state["company_brain"]["company_profile"]["update_log"][0]["provenance"]["signal_id"], "company-brain-control-problem")

    def test_manual_signal_processes_into_packet_detail_and_allows_optional_edit_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
            ):
                entry = runtime.add_manual_signal(
                    {
                        "title": "Manual customer pain",
                        "body": "# Manual customer pain\n\nA customer says their agents keep missing updated pricing context. Next action: route this into the company brain.",
                    }
                )
                pending_state = runtime.load_state()
                pending_detail = runtime.signal_detail(entry["signal_id"])
                runtime.record_feedback({"action": "edit", "signal_id": entry["signal_id"], "note": "apply this with tighter wording", "edited_update": "Use current pricing context in agent onboarding."})
                state = runtime.load_state()
                detail = runtime.signal_detail(entry["signal_id"])

            self.assertIn("Manual pasted", entry["title"])
            self.assertTrue(entry["signal_id"].startswith("manual-"))
            self.assertEqual(pending_state["signals"][0]["source_name"], "Manual Paste")
            self.assertIn("Manual customer pain", pending_detail["input"]["body"])
            self.assertEqual(pending_detail["context_update"]["status"], "company_brain_updated")
            self.assertEqual(detail["context_update"]["status"], "company_brain_updated")
            self.assertEqual(detail["review_decision"]["action"], "edit")
            self.assertIn("current pricing context", detail["review_decision"]["edited_update"])
            self.assertTrue(detail["context_update"]["company_changes"])
            self.assertTrue(detail["context_update"]["update_logs"])
            self.assertIn("diff", detail["context_update"]["review_diff"])
            self.assertEqual(state["company_brain"]["projects_products"][0]["update_log"][0]["provenance"]["source_name"], "Manual Paste")
            self.assertIn("Manual customer pain", state["company_brain"]["projects_products"][0]["update_log"][0]["provenance"]["signal_title"])
            self.assertIn("dogfood", state["company_brain"]["projects_products"][0]["status"])
            self.assertIn("current pricing context", state["company_brain"]["agent_context_changelog"][0]["body"])
            self.assertTrue(state["onboarding"]["first_signal_ready"])

    def test_preview_only_route_feedback_does_not_apply_company_brain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
            ):
                entry = runtime.add_manual_signal(
                    {
                        "title": "Preview only route",
                        "body": "Decision: keep external routes preview-only until local review works.",
                    }
                )
                runtime.record_feedback({"action": "approve", "signal_id": entry["signal_id"], "route_id": "company-brain/followups.md", "note": "do not apply brain"})
                detail = runtime.signal_detail(entry["signal_id"])

            self.assertEqual(detail["context_update"]["status"], "review_pending")
            self.assertEqual(detail["context_update"]["company_changes"], [])
            self.assertTrue(detail["context_update"]["update_logs"])
            self.assertEqual(detail["review_decision"]["route_id"], "company-brain/followups.md")
            self.assertEqual(detail["context_update"]["review_diff"]["diff"], [])

    def test_runtime_uses_ai_lens_runner_command_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_dir = tmp_path / "runtime"
            ai_script = tmp_path / "ai_lenses.py"
            ai_script.write_text(
                """
import json
import sys

payload = json.load(sys.stdin)
print(json.dumps({
    "lenses": [
        {
            "lens_id": lens["id"],
            "fired": True,
            "confidence": "medium",
            "finding": f"AI runner reviewed {lens['name']}.",
            "evidence": [payload["signal"]["body"].splitlines()[0]],
            "operator_implication": "Keep this as a provenance-backed update before any external write.",
            "route_hints": lens.get("route_hints", []),
            "proposed_updates": [{"surface": "none", "action": "none", "reason": "preview only"}],
            "anti_actions": ["Do not write externally."],
            "open_questions": [],
        }
        for lens in payload["lenses"]
    ]
}))
""".strip(),
                encoding="utf-8",
            )
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
                patch.dict("os.environ", {runtime.AI_LENS_COMMAND_ENV: f"{sys.executable} {ai_script}"}, clear=False),
            ):
                entry = runtime.add_manual_signal(
                    {
                        "title": "AI runtime signal",
                        "body": "AI runtime signal\n\nA customer says agents miss pricing context and wants a safer review gate.",
                    }
                )
                detail = runtime.signal_detail(entry["signal_id"])

            self.assertEqual(detail["lens_runner_sources"], ["ai"])
            self.assertTrue(detail["lens_findings"])
            self.assertTrue(all(lens["runner"] == "ai" for lens in detail["lens_findings"]))
            self.assertEqual(detail["context_update"]["lens_runner_sources"], ["ai"])
            self.assertIn("applied the local Company Brain update", detail["context_update"]["result"])
            packet_markdown = Path(detail["summary"]["packet_markdown_path"]).read_text(encoding="utf-8")
            self.assertIn("Preview mode only", packet_markdown)

    def test_runtime_ai_runner_records_deterministic_fallback_without_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
                patch.dict("os.environ", {runtime.AI_LENS_COMMAND_ENV: "", runtime.RUNTIME_LENS_RUNNER_ENV: "ai"}, clear=False),
            ):
                entry = runtime.add_manual_signal(
                    {
                        "title": "Fallback runtime signal",
                        "body": "Fallback runtime signal\n\nDecision: validate customer pain before building more routing machinery.",
                    }
                )
                detail = runtime.signal_detail(entry["signal_id"])

            self.assertIn("deterministic-fallback", detail["lens_runner_sources"])
            self.assertTrue(any(lens["runner"] == "deterministic-fallback" for lens in detail["lens_findings"]))
            self.assertEqual(detail["summary"]["lens_runner_sources"], detail["lens_runner_sources"])
            self.assertIn("applied the local Company Brain update", detail["context_update"]["result"])

    def test_first_user_org_brain_lens_and_destination_state_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                user = runtime.update_user_profile({"name": "Taylor Quinn", "email": "taylor@example.com", "role": "Founder"})
                org = runtime.upsert_org({"name": "DemoCo Labs"})
                profile = runtime.update_brain_setup(
                    {
                        "summary": "DemoCo is dogfooding Lettuce for agent context control.",
                        "positioning": "Durable company context for agent-first operators.",
                        "stage": "first-user dogfood",
                    }
                )
                lens = runtime.save_custom_lens(
                    {
                        "name": "Founder revenue signal",
                        "body": "Find budget, urgency, painful workarounds, and buyer language.",
                        "tags": "revenue, founder",
                    }
                )
                source = runtime.save_source({"name": "Founder inbox", "kind": "email", "detail": "Customer and founder signal."})
                destination = runtime.request_destination({"id": "linear", "name": "Linear"})
                active_destination = runtime.save_destination({"name": "Founder brief", "kind": "email", "detail": "Send company-context weekly brief."})
                state = runtime.load_state()

            self.assertEqual(user["role"], "Founder")
            self.assertEqual(state["user_profile"]["name"], "Taylor Quinn")
            self.assertEqual(org["name"], "DemoCo Labs")
            self.assertEqual(state["current_org_id"], org["id"])
            self.assertEqual(profile["current_stage"], "first-user dogfood")
            self.assertTrue(lens["custom"])
            self.assertEqual(source["name"], "Founder inbox")
            self.assertTrue(source["active"])
            self.assertEqual(state["lenses"][0]["name"], "Founder revenue signal")
            self.assertEqual(destination["name"], "Linear")
            self.assertEqual(active_destination["name"], "Founder brief")
            self.assertTrue(state["destinations"][0]["active"])
            self.assertEqual(state["sources"][0]["kind"], "email")
            self.assertEqual(state["requested_destinations"][0]["id"], "linear")
            self.assertTrue(state["onboarding"]["user_ready"])
            self.assertTrue(state["onboarding"]["org_ready"])
            self.assertTrue(state["onboarding"]["brain_ready"])
            self.assertTrue(state["onboarding"]["lenses_ready"])

    def test_request_connector_persists_to_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                entry = runtime.request_connector({"name": "Linear"})
                state = runtime.load_state()

            self.assertEqual(entry["name"], "Linear")
            self.assertEqual(state["requested_connectors"][0]["name"], "Linear")
            self.assertIn("Connector requested", state["audit"][0]["title"])


    def test_write_api_requires_preview_token_but_get_remains_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                server = runtime.make_server("127.0.0.1", 0, quiet=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    host, port = server.server_address
                    with urlopen(f"http://{host}:{port}/api/state", timeout=5) as response:  # noqa: S310 - local test server
                        self.assertEqual(response.status, 200)

                    request = Request(
                        f"http://{host}:{port}/api/feedback",
                        data=json.dumps({"action": "approve"}).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with self.assertRaises(HTTPError) as raised:
                        urlopen(request, timeout=5)  # noqa: S310 - local test server
                    self.assertEqual(raised.exception.code, 401)

                    authorized = Request(
                        f"http://{host}:{port}/api/feedback",
                        data=json.dumps({"action": "approve", "signal_id": "demo"}).encode("utf-8"),
                        headers={"Content-Type": "application/json", runtime.PREVIEW_TOKEN_HEADER: server.preview_token},
                        method="POST",
                    )
                    with urlopen(authorized, timeout=5) as response:  # noqa: S310 - local test server
                        body = json.loads(response.read().decode("utf-8"))
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

        self.assertEqual(body["action"], "approve")

    def test_preview_token_can_come_from_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.dict("os.environ", {runtime.PREVIEW_TOKEN_ENV: "demo-secret"}),
            ):
                server = runtime.make_server("127.0.0.1", 0, quiet=True)
                try:
                    self.assertEqual(server.preview_token, "demo-secret")
                    self.assertEqual(server.preview_token_source, "env")
                finally:
                    server.server_close()

    def test_brain_api_returns_company_brain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with patch.object(runtime, "STATE_DIR", state_dir), patch.object(runtime, "STATE_PATH", state_dir / "state.json"):
                server = runtime.make_server("127.0.0.1", 0, quiet=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    host, port = server.server_address
                    with urlopen(f"http://{host}:{port}/api/brain", timeout=5) as response:  # noqa: S310 - local test server
                        body = json.loads(response.read().decode("utf-8"))
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

        self.assertIn("organization", body)
        self.assertIn("company_brain", body)
        self.assertIn("company_profile", body["company_brain"])

    def test_company_brain_writes_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "BRAIN_MARKDOWN_DIR", state_dir / "brain"),
            ):
                runtime.update_brain_setup({"summary": "Markdown backed brain", "positioning": "File-first context", "stage": "dogfood"})
                files = runtime.brain_markdown_files()

            names = {item["name"] for item in files}
            self.assertIn("company-profile.md", names)
            profile = next(item for item in files if item["name"] == "company-profile.md")
            self.assertIn("Markdown backed brain", profile["content"])
            self.assertTrue((state_dir / "brain" / "company-profile.md").exists())

    def test_company_brain_proposed_changes_are_signal_specific_with_owner_and_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "runtime"
            with (
                patch.object(runtime, "STATE_DIR", state_dir),
                patch.object(runtime, "STATE_PATH", state_dir / "state.json"),
                patch.object(runtime, "RUNTIME_INPUT_DIR", state_dir / "inputs"),
            ):
                external = runtime.add_manual_signal(
                    {
                        "title": "Saved external YC RFS company brain signal",
                        "body": "Saved external x-post: YC RFS and Baschez category evidence says company brain is crowded. Risk: do not build generic knowledge storage.",
                    }
                )
                market = runtime.add_manual_signal(
                    {
                        "title": "Customer market pain note",
                        "body": "Customer pain: founders say agents miss updated pricing context. Next action: validate willingness to pay before building more UI.",
                    }
                )
                external_detail = runtime.signal_detail(external["signal_id"])
                market_detail = runtime.signal_detail(market["signal_id"])

            external_changes = external_detail["route_proposals"][0]["proposed_changes"]
            market_changes = market_detail["route_proposals"][0]["proposed_changes"]
            self.assertNotEqual(external_changes[0]["detail"], market_changes[0]["detail"])
            self.assertIn("durable company context", external_changes[0]["detail"])
            self.assertIn("customer pain", market_changes[0]["detail"].lower())
            self.assertEqual(external_changes[0]["owner"], "Product/positioning owner")
            self.assertEqual(market_changes[0]["owner"], "Discovery/revenue owner")
            self.assertEqual(market_changes[0]["reviewer"], "Founder/operator")


if __name__ == "__main__":
    unittest.main()
