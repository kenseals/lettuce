from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .handlers import discover_handlers
from .protocol_runtime import add_handler, add_stream_event, approve_review, configure_source, configure_subscription, decline_review, import_source_event, ingest_direct_signal, ingest_email_signal, init_repo, list_reviews, pull_subscriptions, read_logs, run_once, status


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

    init_parser = subparsers.add_parser("init", help="Bootstrap a personal Lettuce repo")
    init_parser.add_argument("path", nargs="?", default=".", help="Repo path to scaffold")
    init_parser.add_argument("--org", required=True, help="Organization slug/name for this Lettuce")
    init_parser.add_argument("--operator", required=True, help="Operator handle/name")
    init_parser.add_argument("--default-model", default="claude-sonnet-4", help="Default handler model")
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
    onboard_parser.add_argument("--openclaw-provider", action="store_true", help="Run handlers through python3 -m lettuce.openclaw_provider")
    onboard_parser.add_argument("--handler-command", help="Provider command for handler execution")

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
    add_source_parser.add_argument("source_type", choices=["file", "stdin", "telegram", "email", "fathom", "granola", "transcript", "zoom"], help="Source type to import or configure")
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

    pull_subscriptions_parser = subparsers.add_parser("pull-subscriptions", help="Import new events from local shared stream subscriptions")
    pull_subscriptions_parser.add_argument("path", nargs="?", default=".", help="Lettuce repo path")
    pull_subscriptions_parser.add_argument("--name", help="Optional subscription id or name to pull")
    pull_subscriptions_parser.add_argument("--commit", action="store_true", help="Commit imported shared-stream events to git")

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
    approve_parser.add_argument("review_id", nargs="?", help="Pending review id")
    approve_parser.add_argument("--first", action="store_true", help="Approve the first pending review")
    approve_parser.add_argument("--operator", default="operator", help="Operator or agent approving the review")
    approve_parser.add_argument("--commit", action="store_true", help="Commit the approval and publish to git")

    decline_parser = subparsers.add_parser("review-decline", help="Decline a pending review without publishing it")
    decline_parser.add_argument("path", help="Lettuce repo path")
    decline_parser.add_argument("review_id", nargs="?", help="Pending review id")
    decline_parser.add_argument("--first", action="store_true", help="Decline the first pending review")
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
        initialized = not (repo_path / "lettuce.yml").exists()
        files_written = init_repo(
            repo_path,
            org=args.org,
            operator=args.operator,
            default_model=args.default_model,
            initialize_git=args.commit,
        )
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
                "status": {
                    "handlers": current.handlers,
                    "streams": current.streams,
                    "checkpoints": current.checkpoints,
                    "log_entries": current.log_entries,
                    "last_log": current.last_log,
                },
            }
        )
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
                "subscription_id": result.subscription_id,
                "name": result.name,
                "remote": result.remote,
                "stream": result.stream,
                "local_stream": result.local_stream,
                "status": result.status,
            }
        )
        return 0

    if args.command == "pull-subscriptions":
        result = pull_subscriptions(args.path, name=args.name, commit=args.commit)
        _print_json(
            {
                "repo": result.repo,
                "subscriptions": result.subscriptions,
                "imported": result.imported,
                "committed": result.committed,
                "pulled": [
                    {
                        "subscription_id": item.subscription_id,
                        "subscription_name": item.subscription_name,
                        "source_repo": item.source_repo,
                        "source_stream": item.source_stream,
                        "source_event_id": item.source_event_id,
                        "imported_event_path": item.imported_event_path,
                        "title": item.title,
                        "committed": item.committed,
                    }
                    for item in result.pulled
                ],
                "notes": result.notes,
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
        review_id = _resolve_review_id(args.path, args.review_id, first=args.first)
        result = approve_review(args.path, review_id, operator=args.operator, commit=args.commit)
        _print_json({"review_id": result.review_id, "status": result.status, "target_stream": result.stream, "publish_path": result.path, "title": result.title})
        return 0

    if args.command == "review-decline":
        review_id = _resolve_review_id(args.path, args.review_id, first=args.first)
        result = decline_review(args.path, review_id, reason=args.reason, operator=args.operator, commit=args.commit)
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
                "handlers": result.handlers,
                "streams": result.streams,
                "checkpoints": result.checkpoints,
                "log_entries": result.log_entries,
                "last_log": result.last_log,
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
