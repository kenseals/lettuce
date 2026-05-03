from __future__ import annotations

import argparse
from datetime import datetime
import html
from pathlib import Path
import re

from .brief_html import write_brief_html
from .config import LETTUCE_HOME
from .feedback import write_feedback_template
from .insights import extract_insights
from .lenses import run_lenses
from .notifications import build_notification
from .packet import build_packet, LettucePacket
from .routers import propose_routes
from .signal import load_signal


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64].strip("-") or "signal"


def _run_paths(created_at: datetime, slug: str) -> tuple[str, Path, Path]:
    timestamp = created_at.strftime("%Y%m%dT%H%M%S")
    run_id = f"{timestamp}-{slug}"
    base_dir = LETTUCE_HOME
    run_dir = base_dir / "runs" / created_at.strftime("%Y-%m-%d") / run_id
    notification_path = base_dir / "notifications" / created_at.strftime("%Y-%m-%d") / f"{run_id}.md"
    return run_id, run_dir, notification_path


def _write_index(base_dir: Path) -> Path:
    runs_root = base_dir / "runs"
    packet_paths = sorted(runs_root.glob("*/*/packet.json"), reverse=True)[:25] if runs_root.exists() else []
    rows: list[str] = []
    for packet_json in packet_paths:
        import json

        data = json.loads(packet_json.read_text(encoding="utf-8"))
        packet_md = packet_json.with_name("packet.md")
        brief_html = packet_json.with_name("brief.html")
        rel_packet = packet_md.relative_to(base_dir).as_posix()
        rel_brief = brief_html.relative_to(base_dir).as_posix()
        fired = [lens["lens"] for lens in data.get("lenses", []) if lens.get("fired")]
        routes = [route["path"] for route in data.get("routes", [])]
        approval = "yes" if any(route.get("requires_approval") for route in data.get("routes", [])) else "no"
        rows.append(
            "<tr>"
            f"<td>{html.escape(data.get('created_at', ''))}</td>"
            f"<td>{html.escape((data.get('signal') or {}).get('title', ''))}</td>"
            f"<td>{html.escape((data.get('signal') or {}).get('source', ''))}</td>"
            f"<td>{html.escape(', '.join(fired) or 'none')}</td>"
            f"<td>{html.escape(data.get('mode', ''))}</td>"
            f"<td>{html.escape(', '.join(routes) or 'none')}</td>"
            f"<td>{approval}</td>"
            f"<td><a href=\"{html.escape(rel_brief)}\">brief</a> · <a href=\"{html.escape(rel_packet)}\">packet</a></td>"
            "</tr>"
        )
    html_doc = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Lettuce feed</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; line-height: 1.4; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }
    th { background: #f6f6f6; }
  </style>
</head>
<body>
  <h1>Lettuce feed</h1>
  <p>Recent OpenClaw-native Lettuce operator briefs.</p>
  <table>
    <thead><tr><th>Time</th><th>Title</th><th>Source</th><th>Lenses fired</th><th>Status</th><th>Routes</th><th>Approval</th><th>Packet</th></tr></thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
""".replace("{rows}", "\n      ".join(rows) if rows else "<tr><td colspan=\"8\">No runs yet.</td></tr>")
    index_path = base_dir / "index.html"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(html_doc, encoding="utf-8")
    return index_path


def write_packet_artifacts(packet: LettucePacket, run_dir: Path, notification_path: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    notification_path.parent.mkdir(parents=True, exist_ok=True)
    packet_md = run_dir / "packet.md"
    packet_json = run_dir / "packet.json"
    feedback_json = run_dir / "feedback.json"
    brief_html = run_dir / "brief.html"
    packet_md.write_text(packet.to_markdown(), encoding="utf-8")
    packet_json.write_text(packet.to_json(), encoding="utf-8")
    write_feedback_template(packet.run_id, feedback_json)
    write_brief_html(packet, brief_html)
    notification_path.write_text(packet.notification + "\n", encoding="utf-8")
    index_path = _write_index(LETTUCE_HOME)
    return packet_md, packet_json, feedback_json, brief_html, notification_path, index_path


def run_preview(
    *,
    input_path: str,
    title: str | None,
    source: str,
    mode: str,
    lens_runner: str = "deterministic",
    include_weak_lenses: bool = False,
) -> tuple[LettucePacket, tuple[Path, Path, Path, Path, Path, Path]]:
    if mode != "preview":
        raise SystemExit("Only --mode preview is implemented in Lettuce v0.1")
    signal = load_signal(input_path, title=title, source=source)
    created_at = datetime.now().astimezone()
    run_id, run_dir, notification_path = _run_paths(created_at, _slugify(signal.title))
    insights = extract_insights(signal)
    lens_results = run_lenses(signal, insights=insights, runner=lens_runner, include_weak_lenses=include_weak_lenses)
    routes = propose_routes(signal, lens_results)
    notification = build_notification(signal, lens_results, routes)
    packet = build_packet(
        run_id=run_id,
        created_at=created_at,
        mode=mode,
        signal=signal,
        lens_results=lens_results,
        routes=routes,
        notification=notification,
    )
    paths = write_packet_artifacts(packet, run_dir, notification_path)
    return packet, paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Lettuce solo-operator signal preview.")
    parser.add_argument("--input", required=True, help="Markdown/text signal input path")
    parser.add_argument("--title", help="Optional signal title override")
    parser.add_argument("--source", default="markdown", help="Signal source label")
    parser.add_argument("--mode", choices=["preview"], default="preview")
    parser.add_argument(
        "--lens-runner",
        choices=["deterministic", "ai", "agent"],
        default="deterministic",
        help="Lens runner to use. 'ai'/'agent' use LETTUCE_AI_LENS_COMMAND when configured and safely fall back to deterministic output.",
    )
    parser.add_argument(
        "--include-weak-lenses",
        action="store_true",
        help="Include every loaded lens in the preview packet, even when the deterministic fit score is weak. Useful for dogfood runs where the Claw/model is judging all default lenses.",
    )
    args = parser.parse_args(argv)

    packet, paths = run_preview(
        input_path=args.input,
        title=args.title,
        source=args.source,
        mode=args.mode,
        lens_runner=args.lens_runner,
        include_weak_lenses=args.include_weak_lenses,
    )
    fired = [result.lens for result in packet.lens_results if result.fired]
    print(f"Lettuce preview wrote run {packet.run_id}")
    runners = sorted({result.runner for result in packet.lens_results})
    print(f"Lenses fired: {', '.join(fired) if fired else 'none'}")
    print(f"Lens runner: {', '.join(runners)}")
    print(f"Operator brief: {paths[3]}")
    print(f"Packet markdown: {paths[0]}")
    print(f"Packet JSON: {paths[1]}")
    print(f"Feedback template: {paths[2]}")
    print(f"Brief HTML: {paths[3]}")
    print(f"Notification: {paths[4]}")
    print(f"Feed: {paths[5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
