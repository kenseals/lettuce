from __future__ import annotations

import html
from pathlib import Path

from .packet import LettucePacket


def write_brief_html(packet: LettucePacket, path: Path) -> None:
    fired = [result for result in packet.lens_results if result.fired and not result.skipped]
    routes = [route for route in packet.routes if route.requires_approval]
    lens_cards = "\n".join(
        f"""
        <section class=\"card lens\">
          <div class=\"eyebrow\">Lens</div>
          <h3>{html.escape(result.lens.replace('_', ' ').title())}</h3>
          <p>{html.escape(result.finding)}</p>
          <p class=\"muted\">Confidence: {html.escape(result.confidence)} · Fit: {result.fit_score}</p>
          <ul>{''.join(f'<li>{html.escape(item)}</li>' for item in result.evidence[:3])}</ul>
        </section>
        """
        for result in fired
    ) or "<p class=\"muted\">No high-signal lenses fired.</p>"
    insight_cards = "\n".join(
        f"""
        <section class=\"card insight\">
          <div class=\"eyebrow\">{html.escape(insight.kind.replace('_', ' ').title())}</div>
          <h3>{html.escape(insight.text)}</h3>
          <p class=\"muted\">{html.escape(insight.evidence)}</p>
        </section>
        """
        for insight in packet.insights
    ) or "<p class=\"muted\">No concrete decisions, open loops, risks, or opportunities extracted yet.</p>"
    route_cards = "\n".join(
        f"""
        <section class=\"card route\">
          <div class=\"eyebrow\">Recommended update</div>
          <h3>{html.escape(route.path)}</h3>
          <p>{html.escape(route.reason)}</p>
          <pre>{html.escape(route.preview.rstrip())}</pre>
        </section>
        """
        for route in routes
    ) or "<p class=\"muted\">No durable updates recommended.</p>"
    feedback_buttons = "\n".join(
        f"<button title=\"{html.escape(option.description)}\">{html.escape(option.label)}</button>"
        for option in packet.feedback_options
    )
    doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Lettuce brief: {html.escape(packet.signal.title)}</title>
  <style>
    :root {{ color-scheme: light; --green:#315c3a; --mint:#eef8ef; --ink:#142018; --muted:#647067; --line:#d9e7db; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:linear-gradient(180deg,#f7fff8,#ffffff); color:var(--ink); }}
    main {{ max-width:980px; margin:0 auto; padding:40px 20px 64px; }}
    .hero {{ background:var(--mint); border:1px solid var(--line); border-radius:28px; padding:28px; box-shadow:0 12px 40px rgba(49,92,58,.08); }}
    .eyebrow {{ text-transform:uppercase; letter-spacing:.12em; color:var(--green); font-size:12px; font-weight:700; }}
    h1 {{ margin:.25rem 0 1rem; font-size:40px; line-height:1.05; }}
    h2 {{ margin:36px 0 14px; }}
    h3 {{ margin:.25rem 0 .5rem; }}
    .brief {{ white-space:pre-wrap; font-size:18px; line-height:1.55; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }}
    .card {{ background:#fff; border:1px solid var(--line); border-radius:18px; padding:18px; }}
    .muted {{ color:var(--muted); }}
    pre {{ background:#f6f8f6; border:1px solid var(--line); border-radius:12px; padding:12px; white-space:pre-wrap; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; }}
    button {{ border:1px solid var(--green); background:#fff; color:var(--green); border-radius:999px; padding:10px 14px; font-weight:650; }}
    footer {{ margin-top:36px; color:var(--muted); font-size:14px; }}
  </style>
</head>
<body>
<main>
  <section class=\"hero\">
    <div class=\"eyebrow\">Lettuce operator brief</div>
    <h1>{html.escape(packet.signal.title)}</h1>
    <div class=\"brief\">{html.escape(packet.operator_brief)}</div>
  </section>

  <h2>Extracted signal</h2>
  <div class=\"grid\">{insight_cards}</div>

  <h2>Lenses</h2>
  <div class=\"grid\">{lens_cards}</div>

  <h2>Recommended updates</h2>
  <div class=\"grid\">{route_cards}</div>

  <h2>One review moment</h2>
  <p class=\"muted\">Approve, edit, or decline in one pass. This feedback is the learning signal for both router and lenses.</p>
  <div class=\"actions\">{feedback_buttons}</div>

  <footer>
    Preview only. Lettuce wrote local artifacts for review and did not update external systems.
  </footer>
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
