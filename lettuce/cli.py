from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .handlers import discover_handlers
from .protocol_runtime import add_handler, add_stream_event, approve_review, configure_source, configure_subscription, decline_review, ensure_source_config, import_source_event, ingest_direct_signal, ingest_email_signal, init_repo, list_reviews, read_logs, read_source_record, record_onboarding_handoff, run_once, status


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _print_progress(event: dict[str, Any]) -> None:
    if event.get("phase") == "start":
        print(f"lettuce: running {event['handler_id']} on {event['event_id']}", file=sys.stderr, flush=True)
        return
    status = "ok" if event.get("success") else "error"
    skipped = " skipped" if event.get("skipped") else ""
    duration_ms = int(event.get("duration_ms") or 0)
    print(
        f"lettuce: {event['handler_id']} {status}{skipped} in {duration_ms / 1000:.1f}s",
        file=sys.stderr,
        flush=True,
    )


def _resolve_handler_command(args: argparse.Namespace) -> str | None:
    if getattr(args, "openclaw_provider", False) and getattr(args, "handler_command", None):
        raise ValueError("use either --openclaw-provider or --handler-command, not both")
    if getattr(args, "openclaw_provider", False):
        return "python3 -m lettuce.openclaw_provider"
    return getattr(args, "handler_command", None)


def _read_body(body: str | None, body_file: str | None) -> str:
    if body is not None and body_file:
        raise ValueError("use either --body or --body-file, not both")
    if body_file:
        return Path(body_file).expanduser().read_text(encoding="utf-8")
    if body is not None:
        return body
    return sys.stdin.read()


def _ask(prompt: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def _ask_yes_no(prompt: str, *, default: bool = False) -> bool:
    default_label = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_label}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")


def _ask_multiline(prompt: str, *, default: str) -> str:
    print(prompt)
    print("End with a single '.' on its own line. Leave blank, then '.', to use the default setup signal.")
    lines: list[str] = []
    while True:
        line = input()
        if line == ".":
            break
        lines.append(line)
    body = "\n".join(lines).strip()
    return body or default


def _default_repo_path(
    path: str | None,
    org: str,
    operator: str,
    *,
    repo_type: str = "personal",
    owner_kind: str = "human_operator",
    role_agent_id: str | None = None,
) -> str:
    if path:
        return path
    def slug(value: str) -> str:
        return "-".join(part for part in value.lower().replace("_", "-").split() if part) or "demo"
    if repo_type == "company_hub":
        return f"./lettuce-{slug(org)}-hub"
    owner_slug = slug(role_agent_id or operator) if owner_kind == "role_agent" else slug(operator)
    return f"./lettuce-{slug(org)}-{owner_slug}"


def _source_summary(source_type: str, result: object) -> str:
    return f"{source_type} -> {getattr(result, 'config_path')} ({getattr(result, 'access_status')})"


def _normalize_onboarding_path(value: str | None) -> str:
    onboarding_path = str(value or "solo_founder").strip().lower()
    if onboarding_path not in {"solo_founder", "multi_operator"}:
        raise ValueError("onboarding path must be solo_founder or multi_operator")
    return onboarding_path


def _default_multi_operator_plan(org: str, operator: str) -> dict[str, Any]:
    def slug(value: str) -> str:
        return "-".join(part for part in value.lower().replace("_", "-").split() if part) or "demo"

    org_slug = slug(org)
    operator_slug = slug(operator)
    return {
        "github_org_scan": {
            "status": "runtime_owned_discovery_not_run",
            "notes": "Record candidate repos and next steps here; actual GitHub org scanning is runtime/operator work.",
        },
        "candidate_repos": [
            {"kind": "personal", "repo": f"lettuce-{org_slug}-{operator_slug}", "status": "current_repo"},
            {"kind": "role_agent", "repo": f"lettuce-{org_slug}-<role-agent-id>", "status": "discover_or_create_if_needed"},
            {"kind": "hub", "repo": f"lettuce-{org_slug}-hub", "status": "offer_if_missing"},
        ],
        "hub_repo": {
            "status": "intent_only",
            "suggested_name": f"lettuce-{org_slug}-hub",
        },
        "shared_streams": {
            "subscription_scope": "subscribe only to explicit exported streams",
            "mirror_path": "streams/shared/*",
            "mirror_status": "planned_runtime_followup",
            "promotion_rule": "run local handlers on shared signal before any local brain promotion",
        },
    }


def _parse_source_plan(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"source plan must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("source plan must decode to a JSON object")
    return payload


def _parse_export(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"export must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("export must decode to a JSON object")
    return payload


def _source_plan_record(repo_path: str, payload: dict[str, Any], *, commit: bool) -> dict[str, Any]:
    source_type = str(payload.get("source_type") or payload.get("type") or "").strip()
    if not source_type:
        raise ValueError("source plan requires source_type")
    metadata = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "source_type",
            "type",
            "name",
            "stream",
            "access_status",
            "access_owner",
            "sample_policy",
            "privacy_notes",
            "setup_next_action",
        }
    }
    result = ensure_source_config(
        repo_path,
        source_type,
        name=str(payload.get("name") or "").strip() or None,
        stream=str(payload.get("stream") or "").strip() or None,
        metadata=metadata,
        access_status=str(payload.get("access_status") or "unknown"),
        access_owner=str(payload.get("access_owner") or "operator-agent"),
        sample_policy=str(payload.get("sample_policy") or "").strip() or None,
        privacy_notes=str(payload.get("privacy_notes") or "").strip() or None,
        setup_next_action=str(payload.get("setup_next_action") or "").strip() or None,
        commit=commit,
    )
    return read_source_record(repo_path, Path(result.config_path).name)


def _first_sample_outcome(run_result: Any, *, no_run: bool, review: bool) -> str:
    if no_run or run_result is None:
        return "ingested_only"
    if any(run.errors for run in run_result.runs):
        return "handler_errors"
    if review and any(publish.status == "pending_review" for run in run_result.runs for publish in run.publishes):
        return "review_pending"
    if any(run.publishes for run in run_result.runs):
        return "processed"
    if any(run.skipped for run in run_result.runs):
        return "no_publish"
    return "processed"


def _resolve_review_id(path: str, review_id: str | None, *, first: bool) -> str:
    if review_id and first:
        raise ValueError("use either a review id or --first, not both")
    if review_id:
        return review_id
    if not first:
        raise ValueError("provide a review id or use --first")
    reviews = list_reviews(path, status="pending")
    if not reviews:
        raise ValueError("no pending reviews found")
    return reviews[0].id



def _run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lettuce", description="Lettuce v0 protocol CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Bootstrap a Lettuce repo")
    init_parser.add_argument("path", nargs="?", default=".", help="Repo path to scaffold")
    init_parser.add_argument("--org", required=True, help="Organization slug/name for this Lettuce")
    init_parser.add_argument("--operator", required=True, help="Operator handle/name")
    init_parser.add_argument("--default-model", default="claude-sonnet-4", help="Default handler model")
    init_parser.add_argument("--repo-type", choices=["personal", "company_hub"], default="personal", help="Repo identity type")
    init_parser.add_argument("--owner-kind", choices=["human_operator", "role_agent"], default="human_operator", help="Identity owner kind")
    init_parser.add_argument("--role-agent-id", help="Required when --owner-kind=role_agent")
    init_parser.add_argument("--permission-basis", choices=["github-user", "github-app", "machine-user"], default="github-user", help="Bounded GitHub identity behind this repo")
    init_parser.add_argument("--visibility", default="private", help="Repo visibility label written to lettuce.yml")
    init_parser.add_argument("--export", action="append", default=[], help="Exported shared stream JSON object")
    init_parser.add_argument("--no-git", action="store_true", help="Do not initialize git or commit scaffold")

    discover_parser = subparsers.add_parser("discover", help="Discover markdown handlers")
    discover_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo or handlers directory")

    add_event_parser = subparsers.add_parser("add-event", help="Add a markdown event to a local stream")
    add_event_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    add_event_parser.add_argument("--stream", default="streams/inbox/direct", help="Destination stream")
    add_event_parser.add_argument("--title", required=True, help="Event title")
    add_event_parser.add_argument("--body", help="Event body text. If omitted, stdin is used")
    add_event_parser.add_argument("--body-file", help="Read event body text from a UTF-8 file")
    add_event_parser.add_argument("--source", default="direct", help="Source label")
    add_event_parser.add_argument("--commit", action="store_true", help="Commit the stream event to git")

    ingest_direct_parser = subparsers.add_parser("ingest-direct", help="Ingest direct operator input already received by the agent")
    ingest_direct_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    ingest_direct_parser.add_argument("--title", required=True, help="Event title")
    ingest_direct_parser.add_argument("--body", help="Event body text. If omitted, stdin is used")
    ingest_direct_parser.add_argument("--body-file", help="Read event body text from a UTF-8 file")
    ingest_direct_parser.add_argument("--source", default="agent.direct", help="Source label, e.g. openclaw.telegram or cli")
    ingest_direct_parser.add_argument("--surface", required=True, help="Agent communication surface, e.g. telegram, imessage, discord, cli")
    ingest_direct_parser.add_argument("--message-id", help="Source message id when available")
    ingest_direct_parser.add_argument("--chat-id", help="Source chat/channel id when available")
    ingest_direct_parser.add_argument("--thread-id", help="Source thread id when available")
    ingest_direct_parser.add_argument("--topic", help="Source topic/forum label when available")
    ingest_direct_parser.add_argument("--observed-at", help="Original observation timestamp when available")
    ingest_direct_parser.add_argument("--sender", help="Source sender/operator label when available")
    ingest_direct_parser.add_argument("--consent", required=True, help="Consent or standing-rule basis for ingesting this signal")
    ingest_direct_parser.add_argument("--commit", action="store_true", help="Commit the stream event to git")

    ingest_email_parser = subparsers.add_parser("ingest-email", help="Ingest an operator-selected or forwarded email signal")
    ingest_email_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    ingest_email_parser.add_argument("--subject", required=True, help="Original email subject")
    ingest_email_parser.add_argument("--title", help="Event title. Defaults to subject")
    ingest_email_parser.add_argument("--body", help="Email body or concise agent summary. If omitted, stdin is used")
    ingest_email_parser.add_argument("--body-file", help="Read email body or summary from a UTF-8 file")
    ingest_email_parser.add_argument("--source", default="openclaw.email.forwarded", help="Source label")
    ingest_email_parser.add_argument("--stream", default="streams/inbox/direct", help="Destination stream. Defaults to direct so standard lenses run")
    ingest_email_parser.add_argument("--message-id", help="Email message id when available")
    ingest_email_parser.add_argument("--thread-id", help="Email thread id when available")
    ingest_email_parser.add_argument("--from", dest="email_from", help="Original email sender")
    ingest_email_parser.add_argument("--to", dest="email_to", help="Original email recipients")
    ingest_email_parser.add_argument("--cc", dest="email_cc", help="Original email cc recipients")
    ingest_email_parser.add_argument("--email-timestamp", help="Original email timestamp")
    ingest_email_parser.add_argument("--source-url", help="Email source URL when available")
    ingest_email_parser.add_argument("--forwarded-by", help="Operator or agent who selected/forwarded the email")
    ingest_email_parser.add_argument("--consent", required=True, help="Consent or standing-rule basis for ingesting this email")
    ingest_email_parser.add_argument("--commit", action="store_true", help="Commit the stream event to git")

    onboard_parser = subparsers.add_parser("onboard", help="Run the first agent-operated onboarding pass with a direct sample")
    onboard_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    onboard_parser.add_argument("--org", required=True, help="Organization slug/name for this Lettuce")
    onboard_parser.add_argument("--operator", required=True, help="Operator handle/name")
    onboard_parser.add_argument("--default-model", default="claude-sonnet-4", help="Default handler model for new repos")
    onboard_parser.add_argument("--repo-type", choices=["personal", "company_hub"], default="personal", help="Repo identity type for newly initialized repos")
    onboard_parser.add_argument("--owner-kind", choices=["human_operator", "role_agent"], default="human_operator", help="Identity owner kind for newly initialized repos")
    onboard_parser.add_argument("--role-agent-id", help="Required when --owner-kind=role_agent")
    onboard_parser.add_argument("--permission-basis", choices=["github-user", "github-app", "machine-user"], default="github-user", help="Bounded GitHub identity behind this repo")
    onboard_parser.add_argument("--visibility", default="private", help="Repo visibility label written to lettuce.yml")
    onboard_parser.add_argument("--export", action="append", default=[], help="Exported shared stream JSON object for newly initialized repos")
    onboard_parser.add_argument("--title", required=True, help="First direct signal title")
    onboard_parser.add_argument("--body", help="First direct signal body. If omitted, stdin is used")
    onboard_parser.add_argument("--body-file", help="Read first direct signal body from a UTF-8 file")
    onboard_parser.add_argument("--source", default="agent.direct", help="Source label, e.g. openclaw.telegram or cli")
    onboard_parser.add_argument("--surface", required=True, help="Agent communication surface, e.g. telegram, imessage, discord, cli")
    onboard_parser.add_argument("--message-id", help="Source message id when available")
    onboard_parser.add_argument("--chat-id", help="Source chat/channel id when available")
    onboard_parser.add_argument("--thread-id", help="Source thread id when available")
    onboard_parser.add_argument("--topic", help="Source topic/forum label when available")
    onboard_parser.add_argument("--observed-at", help="Original observation timestamp when available")
    onboard_parser.add_argument("--sender", help="Source sender/operator label when available")
    onboard_parser.add_argument("--consent", required=True, help="Consent or standing-rule basis for ingesting this signal")
    onboard_parser.add_argument("--commit", action="store_true", help="Commit scaffold, event, and review proposals/publishes to git")
    onboard_parser.add_argument("--review", action="store_true", help="Write first-pass handler outputs to reviews/pending instead of publishing directly")
    onboard_parser.add_argument("--no-run", action="store_true", help="Only initialize and ingest the first direct event")
    onboard_parser.add_argument("--source-plan", action="append", default=[], help="JSON source-plan object to create/reuse and include in onboarding handoff")
    onboard_parser.add_argument("--source-record", action="append", default=[], help="Existing source record id/path to include in onboarding handoff")
    onboard_parser.add_argument("--cadence-hint", help="Cadence hint for post-onboarding source refresh, e.g. manual-for-now or daily")
    onboard_parser.add_argument("--cadence-trigger", help="Trigger hint for post-onboarding refresh, e.g. when-asked or after-meetings")
    onboard_parser.add_argument("--handoff-summary", help="Concise onboarding handoff summary to record")
    onboard_parser.add_argument("--onboarding-path", choices=["solo_founder", "multi_operator"], default="solo_founder", help="Onboarding branch to record in the setup handoff")
    onboard_parser.add_argument("--openclaw-provider", action="store_true", help="Run handlers through python3 -m lettuce.openclaw_provider")
    onboard_parser.add_argument("--handler-command", help="Provider command for handler execution")

    setup_parser = subparsers.add_parser("setup", help="Interactive happy-path onboarding for a personal, role-agent, or company-hub Lettuce")
    setup_parser.add_argument("path", nargs="?", help="Lettuce repo path. If omitted, a path is suggested from org/operator")
    setup_parser.add_argument("--default-model", default="claude-sonnet-4", help="Default handler model for new repos")
    setup_parser.add_argument("--repo-type", choices=["personal", "company_hub"], default="personal", help="Repo identity type for newly initialized repos")
    setup_parser.add_argument("--owner-kind", choices=["human_operator", "role_agent"], default="human_operator", help="Identity owner kind for newly initialized repos")
    setup_parser.add_argument("--role-agent-id", help="Required when --owner-kind=role_agent")
    setup_parser.add_argument("--permission-basis", choices=["github-user", "github-app", "machine-user"], default="github-user", help="Bounded GitHub identity behind this repo")
    setup_parser.add_argument("--visibility", default="private", help="Repo visibility label written to lettuce.yml")
    setup_parser.add_argument("--onboarding-path", choices=["solo_founder", "multi_operator"], help="Override the interactive onboarding branch")
    setup_parser.add_argument("--commit", action="store_true", help="Commit scaffold, sources, event, and review proposals to git")
    setup_parser.add_argument("--no-review", action="store_true", help="Publish directly instead of writing first-pass review proposals")
    setup_parser.add_argument("--no-run", action="store_true", help="Only initialize, configure sources, and ingest the first direct event")
    setup_parser.add_argument("--openclaw-provider", action="store_true", help="Run handlers through python3 -m lettuce.openclaw_provider")
    setup_parser.add_argument("--handler-command", help="Provider command for handler execution")

    add_handler_parser = subparsers.add_parser("add-handler", help="Scaffold a markdown handler")
    add_handler_parser.add_argument("template", choices=["lens", "router", "handler"], help="Handler template to scaffold")
    add_handler_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    add_handler_parser.add_argument("--id", dest="handler_id", help="Handler id. Defaults to custom-<template>")
    add_handler_parser.add_argument("--name", help="Handler display name")
    add_handler_parser.add_argument("--subscribes", default="streams/inbox/direct", help="Stream this handler reads")
    add_handler_parser.add_argument("--publishes", help="Stream this handler writes")
    add_handler_parser.add_argument("--body", help="Handler instruction body. If omitted, a starter prompt is used")
    add_handler_parser.add_argument("--model", default="", help="Optional model override written to handler frontmatter")
    add_handler_parser.add_argument("--commit", action="store_true", help="Commit the handler to git")

    add_source_parser = subparsers.add_parser("add-source", help="Import or configure a signal source")
    add_source_parser.add_argument("source_type", choices=["file", "stdin", "direct", "telegram", "email", "fathom", "granola", "transcript", "zoom"], help="Source type to import or configure")
    add_source_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    add_source_parser.add_argument("--input", dest="input_path", help="Input file path for file sources")
    add_source_parser.add_argument("--stream", help="Destination stream. Defaults by source type")
    add_source_parser.add_argument("--title", help="Event title. Defaults to first heading/line or file name")
    add_source_parser.add_argument("--source", help="Source label. Defaults to file:<name> or stdin")
    add_source_parser.add_argument("--body", help="Body text for stdin sources. If omitted for stdin, stdin is read")
    add_source_parser.add_argument("--body-file", help="Read stdin-source body text from a UTF-8 file")
    add_source_parser.add_argument("--name", help="Configured source display name")
    add_source_parser.add_argument("--bot", help="Telegram bot handle or identifier to record")
    add_source_parser.add_argument("--address", help="Email mailbox, forwarding address, or account label to record")
    add_source_parser.add_argument("--workspace", help="Transcript/workspace/account identifier to record")
    add_source_parser.add_argument("--poll", help="Polling cadence hint for pull-based sources")
    add_source_parser.add_argument("--webhook", help="Webhook or relay URL hint to record")
    add_source_parser.add_argument("--access-status", choices=["available_now", "needs_setup", "defer", "unknown"], default="unknown", help="Whether the operator agent can sample this source now")
    add_source_parser.add_argument("--access-owner", default="operator-agent", help="Who owns auth/setup for this source")
    add_source_parser.add_argument("--sample-policy", help="Small-sample policy before bulk ingestion")
    add_source_parser.add_argument("--privacy-notes", help="Privacy or redaction boundary for this source")
    add_source_parser.add_argument("--setup-next-action", help="Smallest setup step if access is not available yet")
    add_source_parser.add_argument("--query", help="Email/search query or source filter to record")
    add_source_parser.add_argument("--label", help="Email label/folder or source grouping to record")
    add_source_parser.add_argument("--source-url", help="Source URL or app URL to record")
    add_source_parser.add_argument("--redaction-notes", help="Redaction notes to preserve during ingest")
    add_source_parser.add_argument("--commit", action="store_true", help="Commit the imported event or source configuration to git")

    subscribe_parser = subparsers.add_parser("subscribe", help="Record a remote/shared stream subscription")
    subscribe_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    subscribe_parser.add_argument("--remote", required=True, help="Remote repo/name/URL to subscribe to")
    subscribe_parser.add_argument("--stream", required=True, help="Remote stream path to subscribe to")
    subscribe_parser.add_argument("--name", help="Subscription display name/id seed")
    subscribe_parser.add_argument("--local-stream", help="Optional local mirror stream path")
    subscribe_parser.add_argument("--policy", help="Optional policy note or policy id")
    subscribe_parser.add_argument("--commit", action="store_true", help="Commit the subscription record to git")

    run_parser = subparsers.add_parser("run-once", help="Process local stream events once")
    run_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    run_parser.add_argument("--stream", default="streams/inbox/direct", help="Stream to process")
    run_parser.add_argument("--commit", action="store_true", help="Commit publishes to git")
    run_parser.add_argument("--review", action="store_true", help="Write handler outputs to reviews/pending instead of publishing directly")
    run_parser.add_argument("--openclaw-provider", action="store_true", help="Run handlers through python3 -m lettuce.openclaw_provider")
    run_parser.add_argument("--handler-command", help="Provider command for handler execution")

    run_alias_parser = subparsers.add_parser("run", help="Process local stream events once")
    run_alias_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    run_alias_parser.add_argument("--stream", default="streams/inbox/direct", help="Stream to process")
    run_alias_parser.add_argument("--commit", action="store_true", help="Commit publishes to git")
    run_alias_parser.add_argument("--review", action="store_true", help="Write handler outputs to reviews/pending instead of publishing directly")
    run_alias_parser.add_argument("--openclaw-provider", action="store_true", help="Run handlers through python3 -m lettuce.openclaw_provider")
    run_alias_parser.add_argument("--handler-command", help="Provider command for handler execution")

    reviews_parser = subparsers.add_parser("reviews", help="List review proposals")
    reviews_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    reviews_parser.add_argument("--status", choices=["pending", "approved", "declined", "all"], default="pending", help="Review status to list")

    approve_parser = subparsers.add_parser("review-approve", help="Approve a pending review and publish it to its target stream")
    approve_parser.add_argument("path", help="Lettuce repo path")
    approve_parser.add_argument("review_id", help="Pending review id")
    approve_parser.add_argument("--operator", default="operator", help="Operator or agent approving the review")
    approve_parser.add_argument("--commit", action="store_true", help="Commit the approval and publish to git")

    decline_parser = subparsers.add_parser("review-decline", help="Decline a pending review without publishing it")
    decline_parser.add_argument("path", help="Lettuce repo path")
    decline_parser.add_argument("review_id", help="Pending review id")
    decline_parser.add_argument("--reason", default="", help="Optional decline reason")
    decline_parser.add_argument("--operator", default="operator", help="Operator or agent declining the review")
    decline_parser.add_argument("--commit", action="store_true", help="Commit the declined review to git")

    status_parser = subparsers.add_parser("status", help="Show local runtime status")
    status_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")

    logs_parser = subparsers.add_parser("logs", help="Show recent runtime logs")
    logs_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    logs_parser.add_argument("--limit", type=int, default=20, help="Number of log entries to show")

    args = parser.parse_args(argv)

    if args.command == "init":
        written = init_repo(
            args.path,
            org=args.org,
            operator=args.operator,
            default_model=args.default_model,
            repo_type=args.repo_type,
            owner_kind=args.owner_kind,
            role_agent_id=args.role_agent_id,
            permission_basis=args.permission_basis,
            visibility=args.visibility,
            exports=[_parse_export(value) for value in args.export] if args.export else None,
            initialize_git=not args.no_git,
        )
        _print_json({"repo": str(Path(args.path).expanduser().resolve()), "files_written": [str(path) for path in written]})
        return 0

    if args.command == "discover":
        handlers = discover_handlers(args.path)
        _print_json(
            {
                "handlers": [
                    {
                        "id": handler.id,
                        "name": handler.name,
                        "type": handler.type,
                        "version": handler.version,
                        "subscribes": [ref.stream for ref in handler.subscribes],
                        "publishes": [ref.stream for ref in handler.publishes],
                    }
                    for handler in handlers
                ]
            }
        )
        return 0

    if args.command == "add-event":
        body = _read_body(args.body, args.body_file)
        path = add_stream_event(args.path, stream=args.stream, title=args.title, body=body, source=args.source, commit=args.commit)
        _print_json({"event_path": str(path)})
        return 0

    if args.command == "ingest-direct":
        body = _read_body(args.body, args.body_file)
        metadata = {"chat_id": args.chat_id} if args.chat_id else None
        result = ingest_direct_signal(
            args.path,
            title=args.title,
            body=body,
            source=args.source,
            surface=args.surface,
            consent_basis=args.consent,
            observed_at=args.observed_at,
            sender=args.sender,
            thread_id=args.thread_id,
            message_id=args.message_id,
            topic=args.topic,
            metadata=metadata,
            commit=args.commit,
        )
        _print_json({"event_path": result.event_path, "title": result.title, "source": result.source, "consent_basis": result.consent_basis})
        return 0

    if args.command == "ingest-email":
        body = _read_body(args.body, args.body_file)
        result = ingest_email_signal(
            args.path,
            subject=args.subject,
            title=args.title,
            body=body,
            source=args.source,
            stream=args.stream,
            consent_basis=args.consent,
            message_id=args.message_id,
            thread_id=args.thread_id,
            email_from=args.email_from,
            email_to=args.email_to,
            email_cc=args.email_cc,
            email_timestamp=args.email_timestamp,
            source_url=args.source_url,
            forwarded_by=args.forwarded_by,
            commit=args.commit,
        )
        _print_json({"event_path": result.event_path, "title": result.title, "source": result.source, "consent_basis": result.consent_basis})
        return 0

    if args.command == "onboard":
        repo_path = Path(args.path).expanduser().resolve()
        body = _read_body(args.body, args.body_file)
        onboarding_path = _normalize_onboarding_path(args.onboarding_path)
        initialized = not (repo_path / "lettuce.yml").exists()
        files_written = init_repo(
            repo_path,
            org=args.org,
            operator=args.operator,
            default_model=args.default_model,
            repo_type=args.repo_type,
            owner_kind=args.owner_kind,
            role_agent_id=args.role_agent_id,
            permission_basis=args.permission_basis,
            visibility=args.visibility,
            exports=[_parse_export(value) for value in args.export] if args.export else None,
            initialize_git=args.commit,
        )
        source_plan_records = [read_source_record(repo_path, source_ref) for source_ref in args.source_record]
        for payload in [_parse_source_plan(value) for value in args.source_plan]:
            source_plan_records.append(_source_plan_record(str(repo_path), payload, commit=args.commit))
        metadata = {"chat_id": args.chat_id} if args.chat_id else None
        direct = ingest_direct_signal(
            repo_path,
            title=args.title,
            body=body,
            source=args.source,
            surface=args.surface,
            consent_basis=args.consent,
            observed_at=args.observed_at,
            sender=args.sender,
            thread_id=args.thread_id,
            message_id=args.message_id,
            topic=args.topic,
            metadata=metadata,
            commit=args.commit,
        )
        handler_command = _resolve_handler_command(args)
        run_result = None if args.no_run else run_once(repo_path, stream="streams/inbox/direct", commit=args.commit, review=args.review, progress=_print_progress, handler_command=handler_command)
        handoff = record_onboarding_handoff(
            repo_path,
            source_plan=source_plan_records,
            first_sample={
                "type": "direct",
                "source": direct.source,
                "stream": "streams/inbox/direct",
                "title": direct.title,
                "event_path": str(Path(direct.event_path).relative_to(repo_path)),
                "event_id": Path(direct.event_path).stem,
                "consent_basis": direct.consent_basis,
                "outcome": _first_sample_outcome(run_result, no_run=args.no_run, review=args.review),
            },
            onboarding_path=onboarding_path,
            multi_operator_plan=_default_multi_operator_plan(args.org, args.operator) if onboarding_path == "multi_operator" else None,
            cadence_hint=args.cadence_hint,
            cadence_trigger=args.cadence_trigger,
            handoff_summary=args.handoff_summary,
            commit=args.commit,
        )
        current = status(repo_path)
        _print_json(
            {
                "repo": str(repo_path),
                "initialized": initialized,
                "files_written": [str(path) for path in files_written],
                "event_path": direct.event_path,
                "source": direct.source,
                "consent_basis": direct.consent_basis,
                "run": None
                if run_result is None
                else {
                    "handlers": run_result.handlers,
                    "events": run_result.events,
                    "runs": [
                        {
                            "handler_id": run.handler_id,
                            "event_id": run.event_id,
                            "skipped": run.skipped,
                            "publishes": [publish.path for publish in run.publishes],
                            "publish_statuses": [publish.status for publish in run.publishes],
                            "review_ids": [publish.review_id for publish in run.publishes if publish.review_id],
                            "notes": run.notes,
                            "errors": run.errors,
                            "committed": run.committed,
                            "duration_ms": run.duration_ms,
                        }
                        for run in run_result.runs
                    ],
                },
                "onboarding": current.onboarding,
                "sources": current.sources,
                "handoff_path": handoff["path"],
                "status": {
                    "handlers": current.handlers,
                    "streams": current.streams,
                    "checkpoints": current.checkpoints,
                    "log_entries": current.log_entries,
                    "agent_instructions_path": current.agent_instructions_path,
                    "sources": current.sources,
                    "onboarding": current.onboarding,
                    "last_log": current.last_log,
                },
            }
        )
        return 0

    if args.command == "setup":
        print("Lettuce is a work-context layer for your agent.")
        print("It keeps company/org signal in a git-backed repo, separate from personal memory, then uses lenses and review gates to turn messy inputs like emails, calls, chats, and docs into durable company context your agent can use later.\n")
        print("I’ll ask a few setup questions, create or connect the repo, configure the first signal sources, and leave you with a summary of what I set up and how I’ll use it going forward.\n")
        if not _ask_yes_no("Want to continue?", default=True):
            print("Stopped. No Lettuce repo was created or changed.")
            return 0

        org = _ask("What company, client, or project is this Lettuce for?")
        if not org:
            raise ValueError("org/project is required")
        operator = _ask("Operator name/handle")
        if not operator:
            raise ValueError("operator is required")
        if args.onboarding_path:
            onboarding_path = _normalize_onboarding_path(args.onboarding_path)
        else:
            onboarding_path = "multi_operator" if _ask_yes_no("Is this for a multi-operator org that expects shared-stream coordination later?", default=False) else "solo_founder"
        repo_input = _ask(
            "Repo path",
            default=_default_repo_path(
                args.path,
                org,
                operator,
                repo_type=args.repo_type,
                owner_kind=args.owner_kind,
                role_agent_id=args.role_agent_id,
            ),
        )
        repo_path = Path(repo_input).expanduser().resolve()
        consent = _ask("Consent basis for the first manual signal", default="operator-direct-request")

        print("\nManual/direct ingestion will be configured by default. Going forward, the operator can say: run Lettuce on this")
        configure_email = _ask_yes_no("Do you already have an email source to record for this Lettuce?", default=False)
        email_name = email_address = email_policy = email_privacy = ""
        if configure_email:
            email_name = _ask("Email source name", default="operator-selected-email")
            email_address = _ask("Mailbox/account/label", default="operator-selected")
            email_policy = _ask("Email sample policy", default="first-5-operator-approved")
            email_privacy = _ask("Email privacy notes", default="skip personal/legal/medical/unrelated mail")

        configure_transcript = _ask_yes_no("Do you already have a call transcript source to record?", default=False)
        transcript_type = transcript_name = transcript_workspace = transcript_policy = transcript_privacy = ""
        if configure_transcript:
            transcript_type = _ask("Transcript source type: fathom, granola, zoom, or transcript", default="transcript").lower()
            if transcript_type not in {"fathom", "granola", "zoom", "transcript"}:
                raise ValueError("transcript source type must be fathom, granola, zoom, or transcript")
            transcript_name = _ask("Transcript source name", default=f"{transcript_type}-selected-transcripts")
            transcript_workspace = _ask("Workspace/account/export label", default="operator-selected")
            transcript_policy = _ask("Transcript sample policy", default="first-3-operator-approved")
            transcript_privacy = _ask("Transcript privacy notes", default="only org-scoped calls with consent/permission")

        default_signal = f"Operator set up Lettuce for {org}. Manual/direct ingestion should be available, source boundaries should be explicit, and durable updates should go through review before brain writes."
        title = _ask("First signal title", default="Lettuce setup signal")
        body = _ask_multiline("Paste the first manual signal for this Lettuce.", default=default_signal)

        initialized = not (repo_path / "lettuce.yml").exists()
        files_written = init_repo(
            repo_path,
            org=org,
            operator=operator,
            default_model=args.default_model,
            repo_type=args.repo_type,
            owner_kind=args.owner_kind,
            role_agent_id=args.role_agent_id,
            permission_basis=args.permission_basis,
            visibility=args.visibility,
            initialize_git=args.commit,
        )
        configured_sources: list[str] = []
        setup_source_plan: list[dict[str, Any]] = []
        manual_source = configure_source(
            repo_path,
            "direct",
            name="manual-direct",
            access_status="available_now",
            sample_policy="operator-forwarded-or-pasted-signals; review before brain writes",
            privacy_notes="skip personal-life context and unrelated org signal; preserve provenance and consent",
            setup_next_action="Operator can say: run Lettuce on this",
            commit=args.commit,
        )
        configured_sources.append(_source_summary("manual/direct", manual_source))
        setup_source_plan.append(read_source_record(repo_path, manual_source.source_id))
        if configure_email:
            email_source = configure_source(
                repo_path,
                "email",
                name=email_name,
                metadata={"address": email_address},
                access_status="available_now",
                sample_policy=email_policy,
                privacy_notes=email_privacy,
                setup_next_action="sample operator-approved email threads before bulk ingest",
                commit=args.commit,
            )
            configured_sources.append(_source_summary("email", email_source))
            setup_source_plan.append(read_source_record(repo_path, email_source.source_id))
        if configure_transcript:
            transcript_source = configure_source(
                repo_path,
                transcript_type,
                name=transcript_name,
                metadata={"workspace": transcript_workspace},
                access_status="available_now",
                sample_policy=transcript_policy,
                privacy_notes=transcript_privacy,
                setup_next_action="sample operator-approved transcripts before bulk ingest",
                commit=args.commit,
            )
            configured_sources.append(_source_summary("transcripts", transcript_source))
            setup_source_plan.append(read_source_record(repo_path, transcript_source.source_id))

        direct = ingest_direct_signal(
            repo_path,
            title=title,
            body=body,
            source="cli.setup",
            surface="cli",
            consent_basis=consent,
            sender=operator,
            commit=args.commit,
        )
        handler_command = _resolve_handler_command(args)
        run_result = None if args.no_run else run_once(repo_path, stream="streams/inbox/direct", commit=args.commit, review=not args.no_review, progress=_print_progress, handler_command=handler_command)
        reviews = list_reviews(repo_path, status="pending")

        print("\nDone.")
        multi_operator_plan = _default_multi_operator_plan(org, operator) if onboarding_path == "multi_operator" else None
        handoff = record_onboarding_handoff(
            repo_path,
            source_plan=setup_source_plan,
            first_sample={
                "type": "direct",
                "source": direct.source,
                "stream": "streams/inbox/direct",
                "title": direct.title,
                "event_path": str(Path(direct.event_path).relative_to(repo_path)),
                "event_id": Path(direct.event_path).stem,
                "consent_basis": direct.consent_basis,
                "outcome": _first_sample_outcome(run_result, no_run=args.no_run, review=not args.no_review),
            },
            onboarding_path=onboarding_path,
            multi_operator_plan=multi_operator_plan,
            handoff_summary=(
                "Solo founder setup: personal Lettuce, manual/direct signal, one source plan, first handler pass, and optional GitHub remote next."
                if onboarding_path == "solo_founder"
                else "Multi-operator setup: local Lettuce is ready; shared-stream discovery, hub selection, and remote mirroring remain recorded intent until the runtime handles them."
            ),
            commit=args.commit,
        )
        current = status(repo_path)
        print(f"I set up Lettuce for {org} at {repo_path}.")
        print(
            f"Repo identity: type `{current.identity.repo_type}`, owner_kind `{current.identity.owner_kind}`, "
            f"permission_basis `{current.identity.permission_basis}`, visibility `{current.identity.visibility}`."
        )
        if current.identity.role_agent_id:
            print(
                f"Role agent id: `{current.identity.role_agent_id}`. "
                "Keep this repo bounded to that GitHub identity's permitted scope."
            )
        if current.identity.repo_type == "company_hub":
            print("This repo is the optional company hub: keep it curated, write shared context under `streams/shared/*`, and do not turn it into a raw-signal dump.")
        else:
            print("Manual/direct ingestion is ready: say “run Lettuce on this” and the agent should capture the signal with provenance, run lenses, and show review proposals before durable brain updates.")
        print(f"Repo-local agent instructions: {current.agent_instructions_path}")
        print("Configured sources:")
        for source in configured_sources:
            print(f"- {source}")
        if not configure_email:
            print("- email not configured yet; forward or select a few org-scoped emails when ready")
        if not configure_transcript:
            print("- transcripts not configured yet; export or select 1-3 org-scoped calls when ready")
        print(f"First signal event: {direct.event_path}")
        if run_result is None:
            print("Handlers were not run because --no-run was set.")
        else:
            print(f"Handlers run: {run_result.handlers}; events processed: {run_result.events}; pending reviews: {len(reviews)}")
        print(f"Logs/checkpoints: {current.log_entries} log entries, {current.checkpoints} checkpoints")
        print(f"Onboarding path: `{onboarding_path}`.")
        if onboarding_path == "solo_founder":
            print("This stays on the simple path: personal repo now, one source plan now, GitHub remote optional next, and shared streams only as future-ready context if the org grows.")
            print("Optional next step: connect this local repo to a private GitHub remote when the operator wants backup, sync, or agent access from another machine.")
        else:
            print("Multi-operator coordination is recorded as intent only: scan the GitHub org in the runtime, surface personal/role-agent/hub candidates, subscribe only to explicit exports, keep any future mirrors under `streams/shared/*`, and run local handlers before promoting shared signal into local brain context.")
        print(f"Onboarding handoff: {handoff['path']}")
        print("Going forward, use this Lettuce for org-scoped work context, not personal memory. Ask before bulk ingesting or writing sensitive updates.")
        print("Next: review pending proposals with `lettuce reviews` and approve/edit/decline the useful ones.")
        if initialized:
            print("Repo initialized from scratch.")
        else:
            print("Existing Lettuce repo reused.")
        print(f"Files written during init: {len(files_written)}")
        return 0

    if args.command == "add-handler":
        path = add_handler(
            args.path,
            args.template,
            handler_id=args.handler_id,
            name=args.name,
            subscribes=args.subscribes,
            publishes=args.publishes,
            body=args.body,
            model=args.model,
            commit=args.commit,
        )
        _print_json({"handler_path": str(path)})
        return 0

    if args.command == "add-source":
        if args.source_type in {"file", "stdin"}:
            if args.source_type == "file" and (args.body is not None or args.body_file):
                raise ValueError("--body and --body-file are only valid for stdin sources")
            text = _read_body(args.body, args.body_file) if args.source_type == "stdin" else None
            result = import_source_event(
                args.path,
                args.source_type,
                input_path=args.input_path,
                text=text,
                title=args.title,
                stream=args.stream or "streams/inbox/direct",
                source=args.source,
                commit=args.commit,
            )
            _print_json(
                {
                    "source_type": result.source_type,
                    "event_path": result.event_path,
                    "title": result.title,
                    "source": result.source,
                }
            )
            return 0
        metadata = {
            key: value
            for key, value in {
                "bot": args.bot,
                "address": args.address,
                "workspace": args.workspace,
                "poll": args.poll,
                "webhook": args.webhook,
                "query": args.query,
                "label": args.label,
                "source_url": args.source_url,
                "redaction_notes": args.redaction_notes,
            }.items()
            if value
        }
        result = configure_source(
            args.path,
            args.source_type,
            name=args.name,
            stream=args.stream,
            metadata=metadata,
            access_status=args.access_status,
            access_owner=args.access_owner,
            sample_policy=args.sample_policy,
            privacy_notes=args.privacy_notes,
            setup_next_action=args.setup_next_action,
            commit=args.commit,
        )
        _print_json(
            {
                "source_type": result.source_type,
                "config_path": result.config_path,
                "stream": result.stream,
                "status": result.status,
                "access_status": result.access_status,
                "access_owner": result.access_owner,
            }
        )
        return 0

    if args.command == "subscribe":
        result = configure_subscription(
            args.path,
            args.remote,
            stream=args.stream,
            name=args.name,
            local_stream=args.local_stream,
            policy=args.policy,
            commit=args.commit,
        )
        _print_json(
            {
                "subscription_path": result.subscription_path,
                "remote": result.remote,
                "stream": result.stream,
                "status": result.status,
            }
        )
        return 0

    if args.command == "reviews":
        reviews = list_reviews(args.path, status=args.status)
        _print_json(
            {
                "reviews": [
                    {
                        "id": review.id,
                        "status": review.status,
                        "path": review.path,
                        "target_stream": review.target_stream,
                        "title": review.title,
                        "handler_id": review.handler_id,
                        "source_event": review.source_event,
                    }
                    for review in reviews
                ]
            }
        )
        return 0

    if args.command == "review-approve":
        result = approve_review(args.path, args.review_id, operator=args.operator, commit=args.commit)
        _print_json({"review_id": result.review_id, "status": result.status, "target_stream": result.stream, "publish_path": result.path, "title": result.title})
        return 0

    if args.command == "review-decline":
        result = decline_review(args.path, args.review_id, reason=args.reason, operator=args.operator, commit=args.commit)
        _print_json({"review_id": result.id, "status": result.status, "path": result.path, "target_stream": result.target_stream, "title": result.title})
        return 0

    if args.command in {"run-once", "run"}:
        result = run_once(args.path, stream=args.stream, commit=args.commit, review=args.review, progress=_print_progress, handler_command=_resolve_handler_command(args))
        _print_json(
            {
                "repo": result.repo,
                "stream": result.stream,
                "handlers": result.handlers,
                "events": result.events,
                "runs": [
                    {
                        "handler_id": run.handler_id,
                        "event_id": run.event_id,
                        "skipped": run.skipped,
                        "publishes": [publish.path for publish in run.publishes],
                        "publish_statuses": [publish.status for publish in run.publishes],
                        "review_ids": [publish.review_id for publish in run.publishes if publish.review_id],
                        "notes": run.notes,
                        "errors": run.errors,
                        "committed": run.committed,
                        "duration_ms": run.duration_ms,
                    }
                    for run in result.runs
                ],
            }
        )
        return 0

    if args.command == "status":
        result = status(args.path)
        _print_json(
            {
                "repo": result.repo,
                "identity": {
                    "repo_type": result.identity.repo_type,
                    "org": result.identity.org,
                    "owner_kind": result.identity.owner_kind,
                    "operator": result.identity.operator,
                    "role_agent_id": result.identity.role_agent_id,
                    "permission_basis": result.identity.permission_basis,
                    "visibility": result.identity.visibility,
                },
                "handlers": result.handlers,
                "streams": result.streams,
                "checkpoints": result.checkpoints,
                "log_entries": result.log_entries,
                "agent_instructions_path": result.agent_instructions_path,
                "sources": result.sources,
                "onboarding": result.onboarding,
                "last_log": result.last_log,
                "freshness": result.freshness,
            }
        )
        return 0

    if args.command == "logs":
        _print_json({"logs": read_logs(args.path, limit=args.limit)})
        return 0

    return 1


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
