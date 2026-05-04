from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

DEFAULT_RUNTIME_URL = "http://127.0.0.1:8787"


class LettuceClientError(RuntimeError):
    """Raised when the Lettuce runtime API cannot satisfy a client request."""


def _runtime_url(value: str) -> str:
    return value.rstrip("/") + "/"


def _request_json(runtime_url: str, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 10.0, token: str | None = None) -> dict[str, Any]:
    url = urljoin(_runtime_url(runtime_url), path.lstrip("/"))
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["X-Lettuce-Preview-Token"] = token
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided local/runtime URL is expected CLI input
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LettuceClientError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise LettuceClientError(f"Could not reach Lettuce runtime at {url}: {exc.reason}") from exc
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise LettuceClientError(f"Runtime returned non-JSON response from {url}") from exc
    if not isinstance(body, dict):
        raise LettuceClientError(f"Runtime returned unexpected JSON from {url}: {type(body).__name__}")
    if "error" in body:
        raise LettuceClientError(str(body["error"]))
    return body


def submit_signal(runtime_url: str, *, title: str | None, body: str, timeout: float = 10.0, token: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"body": body}
    if title:
        payload["title"] = title
    return _request_json(runtime_url, "/api/manual-signal", method="POST", payload=payload, timeout=timeout, token=token or os.environ.get("LETTUCE_PREVIEW_TOKEN"))


def get_brain(runtime_url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    return _request_json(runtime_url, "/api/brain", timeout=timeout)


def review_signal(runtime_url: str, *, signal_id: str, action: str, note: str = "", route_id: str = "company_brain:reviewed-context-update", edited_update: str = "", timeout: float = 10.0, token: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"signal_id": signal_id, "action": action, "route_id": route_id, "note": note}
    if edited_update:
        payload["edited_update"] = edited_update
    return _request_json(runtime_url, "/api/feedback", method="POST", payload=payload, timeout=timeout, token=token or os.environ.get("LETTUCE_PREVIEW_TOKEN"))


def _read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as handle:
            return handle.read()
    if args.body is not None:
        return args.body
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise LettuceClientError("submit requires --body, --body-file, or stdin")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal CLI client for the standalone Lettuce runtime API.")
    parser.add_argument("--runtime-url", default=DEFAULT_RUNTIME_URL, help=f"Lettuce runtime URL (default: {DEFAULT_RUNTIME_URL})")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    parser.add_argument("--token", default=os.environ.get("LETTUCE_PREVIEW_TOKEN", ""), help="Write token for POST requests. Defaults to LETTUCE_PREVIEW_TOKEN.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit = subparsers.add_parser("submit", help="Submit a signal to Lettuce for packet/context processing")
    submit.add_argument("--title", help="Optional signal title")
    submit.add_argument("--body", help="Signal body text. If omitted, stdin is used when piped.")
    submit.add_argument("--body-file", help="Read signal body from a UTF-8 text/markdown file")

    subparsers.add_parser("brain", help="Fetch the current company brain from the Lettuce runtime")

    review = subparsers.add_parser("review", help="Optionally approve, edit, or decline one route proposal for a signal")
    review.add_argument("--signal-id", required=True, help="Signal id from submit output or /api/signals")
    review.add_argument("--action", choices=["approve", "edit", "decline"], required=True, help="Optional feedback decision")
    review.add_argument("--route-id", default="company_brain:reviewed-context-update", help="Route proposal to target. Only company_brain routes apply local state.")
    review.add_argument("--note", default="", help="Feedback note")
    review.add_argument("--edited-update", default="", help="Optional edited wording for an edit decision")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "submit":
            result = submit_signal(args.runtime_url, title=args.title, body=_read_body(args), timeout=args.timeout, token=args.token or None)
        elif args.command == "brain":
            result = get_brain(args.runtime_url, timeout=args.timeout)
        elif args.command == "review":
            result = review_signal(args.runtime_url, signal_id=args.signal_id, action=args.action, route_id=args.route_id, note=args.note, edited_update=args.edited_update, timeout=args.timeout, token=args.token or None)
        else:  # pragma: no cover - argparse prevents this
            parser.error(f"unknown command: {args.command}")
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except LettuceClientError as exc:
        print(f"lettuce.client: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
