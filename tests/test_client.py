from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

import lettuce.client as client


class _FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._raw = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


class _FakeStdin(io.StringIO):
    def isatty(self) -> bool:
        return False


class LettuceClientTests(unittest.TestCase):
    def test_submit_signal_posts_manual_signal_payload(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: float) -> _FakeResponse:
            captured["url"] = request.full_url  # type: ignore[attr-defined]
            captured["method"] = request.get_method()  # type: ignore[attr-defined]
            captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
            captured["timeout"] = timeout
            captured["token"] = request.headers.get("X-lettuce-preview-token")  # type: ignore[attr-defined]
            return _FakeResponse({"signal_id": "manual-1", "title": "Manual pasted signal processed into packet"})

        with patch.object(client, "urlopen", fake_urlopen):
            result = client.submit_signal("http://runtime.local/", title="Customer pain", body="Agents miss pricing context", timeout=2, token="write-token")

        self.assertEqual(result["signal_id"], "manual-1")
        self.assertEqual(captured["url"], "http://runtime.local/api/manual-signal")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["payload"], {"title": "Customer pain", "body": "Agents miss pricing context"})
        self.assertEqual(captured["timeout"], 2)
        self.assertEqual(captured["token"], "write-token")

    def test_get_brain_calls_brain_endpoint(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: float) -> _FakeResponse:
            captured["url"] = request.full_url  # type: ignore[attr-defined]
            captured["method"] = request.get_method()  # type: ignore[attr-defined]
            return _FakeResponse({"organization": {"status": "ok"}, "company_brain": {"company_profile": {}}})

        with patch.object(client, "urlopen", fake_urlopen):
            result = client.get_brain("http://runtime.local")

        self.assertEqual(captured["url"], "http://runtime.local/api/brain")
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(result["organization"]["status"], "ok")

    def test_review_signal_posts_feedback_for_company_brain_route(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: float) -> _FakeResponse:
            captured["url"] = request.full_url  # type: ignore[attr-defined]
            captured["method"] = request.get_method()  # type: ignore[attr-defined]
            captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
            captured["token"] = request.headers.get("X-lettuce-preview-token")  # type: ignore[attr-defined]
            return _FakeResponse({"id": "fb-1", "action": "edit"})

        with patch.object(client, "urlopen", fake_urlopen):
            result = client.review_signal(
                "http://runtime.local",
                signal_id="manual-1",
                action="edit",
                note="tighten wording",
                edited_update="Use current pricing context.",
                token="write-token",
            )

        self.assertEqual(result["id"], "fb-1")
        self.assertEqual(captured["url"], "http://runtime.local/api/feedback")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["payload"]["route_id"], "company_brain:reviewed-context-update")
        self.assertEqual(captured["payload"]["edited_update"], "Use current pricing context.")
        self.assertEqual(captured["token"], "write-token")

    def test_cli_submit_reads_stdin_when_body_omitted(self) -> None:
        with (
            patch.object(client.sys, "stdin", _FakeStdin("Signal from stdin")),
            patch.object(client, "submit_signal", return_value={"signal_id": "manual-stdin"}) as submit,
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            status = client.main(["--runtime-url", "http://runtime.local", "submit", "--title", "stdin signal"])

        self.assertEqual(status, 0)
        submit.assert_called_once_with("http://runtime.local", title="stdin signal", body="Signal from stdin", timeout=10.0, token=None)
        self.assertIn("manual-stdin", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
