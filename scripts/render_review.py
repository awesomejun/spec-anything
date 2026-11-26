#!/usr/bin/env python3
"""
Dual-Audience Review Bundle Renderer for spec-anything.
Absorbs the hybrid HTML/DOCX/SVG rendering and file:// SSRF-blocking pattern
from Reverse_Spec_and_PRD while keeping 01-12 Markdown/JSON/JSONL as the canonical source.
Outputs:
  - pm-design-review.html : PM & Design executive bundle (01 PRD + 03 scope + 05 screenshots + 11 tokens + SVG flow)
  - dev-qa-parity.html    : Dev & QA engineering bundle (02 SDD + 04 REA + 06 ledger + 07 parity + 09 contracts + 10/08/12)
  - architecture-flow.svg : Clean standalone SVG data/execution flow diagram
  - spec-review.docx      : Optional Word document (when --formats includes docx)
  - pm-design-review.pdf  : Optional PDF via Playwright with file:// network interception blocked (when --formats includes pdf)
"""
import argparse
import base64
import html
import json
import pathlib
import re

import markdown

FILE_SCHEME_RE = re.compile(r'''(?:href|src|url)\s*[=(]\s*["']?file://[^"')\s>]+''', re.I)


def sanitize_block_file_urls(html_body: str) -> tuple[str, int]:
    """Security guard (SSRF / local file inclusion prevention): strip any file:// references."""
    matches = FILE_SCHEME_RE.findall(html_body)
    cleaned = FILE_SCHEME_RE.sub('href="#blocked-local-file-scheme"', html_body)
    return cleaned, len(matches)


def md_to_html(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc"])


def generate_flow_svg(bundle_dir: pathlib.Path, out_svg: pathlib.Path) -> str:
    features = json.loads((bundle_dir / "03_scope" / "features.json").read_text(encoding="utf-8"))
    report = json.loads((bundle_dir / "07_tests" / "parity_report.json").read_text(encoding="utf-8"))
    target_name = html.escape(features["target"]["repo"] + " " + features["target"]["tag"])
    f_cnt = len(features["features"])
    p_pass = report["summary"]["passed"]
    p_tot = report["summary"]["total"]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 230" width="980" height="230" role="img" aria-label="spec-anything verification pipeline">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="980" height="230" rx="12" fill="#f8fafc" stroke="#cbd5e1"/>
  <text x="24" y="34" font-family="ui-sans-serif, system-ui, sans-serif" font-size="16" font-weight="700" fill="#0f172a">spec-anything Closed-Loop Parity Pipeline — {target_name}</text>

  <rect x="24" y="62" width="165" height="96" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.5"/>
  <text x="106" y="88" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" font-weight="700" fill="#0f172a">01 Source + REA</text>
  <text x="106" y="110" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">Static Source Map</text>
  <text x="106" y="128" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">Release SHA-256 (04)</text>
  <text x="106" y="146" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#0f766e">Verified Match</text>

  <line x1="189" y1="110" x2="220" y2="110" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>

  <rect x="224" y="62" width="165" height="96" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.5"/>
  <text x="306" y="88" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" font-weight="700" fill="#0f172a">03 Feature FK</text>
  <text x="306" y="110" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">{f_cnt} Tracked Features</text>
  <text x="306" y="128" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">Anti-Macro Gate</text>
  <text x="306" y="146" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">Single Foreign Key</text>

  <line x1="389" y1="110" x2="420" y2="110" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>

  <rect x="424" y="62" width="165" height="96" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.5"/>
  <text x="506" y="88" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" font-weight="700" fill="#0f172a">05 UI + 06 Ledger</text>
  <text x="506" y="110" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">Live Isolated Runtime</text>
  <text x="506" y="128" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">SSE + SQLite + Restart</text>
  <text x="506" y="146" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">Screenshots + Tokens</text>

  <line x1="589" y1="110" x2="620" y2="110" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>

  <rect x="624" y="62" width="165" height="96" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.5"/>
  <text x="706" y="88" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" font-weight="700" fill="#0f172a">09 Contracts</text>
  <text x="706" y="110" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">OpenAPI 3.1 JSON</text>
  <text x="706" y="128" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">JSON Schemas + DDL</text>
  <text x="706" y="146" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#475569">10 State + 08/12 Plan</text>

  <line x1="789" y1="110" x2="820" y2="110" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>

  <rect x="824" y="62" width="132" height="96" rx="8" fill="#ecfdf5" stroke="#0f766e" stroke-width="2"/>
  <text x="890" y="90" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" font-weight="700" fill="#065f46">07 Parity</text>
  <text x="890" y="114" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="15" font-weight="700" fill="#047857">{p_pass} / {p_tot} PASS</text>
  <text x="890" y="138" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#065f46">Reads 06 JSONL</text>

  <text x="24" y="198" font-family="ui-monospace, SFMono-Regular, monospace" font-size="11" fill="#64748b">Every claim traces back to 03 Feature IDs, [REF: path:line], 05 Screenshot IDs, 06 Observed JSONL, and 07 Executable Verdict.</text>
</svg>
'''
    out_svg.write_text(svg, encoding="utf-8")
    return svg


def build_screenshot_gallery_html(bundle_dir: pathlib.Path) -> str:
    sp = bundle_dir / "05_ui" / "screens.json"
    if not sp.exists():
        return ""
    sdata = json.loads(sp.read_text(encoding="utf-8"))
    cards = []
    for sc in sdata.get("screens", []):
        img_path = bundle_dir / "05_ui" / sc["file"]
        if not img_path.exists():
            continue
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        cards.append(
            f'<figure class="shot-card">'
            f'<img src="data:image/png;base64,{b64}" alt="{html.escape(sc["title"])}"/>'
            f'<figcaption><strong>{html.escape(sc["screen_id"])}</strong> ({html.escape(sc["state"])}) — {html.escape(sc["title"])}'
            f'<br/><span class="muted">Feature: {html.escape(sc["feature_id"])} | Viewport: {html.escape(sc["viewport"])}</span></figcaption>'
            f'</figure>'
        )
    return '<section id="gallery"><h2>Visual Evidence Gallery (05 Screenshots)</h2><div class="gallery-grid">' + "\n".join(cards) + '</div></section>'


def wrap_html(title: str, subtitle: str, nav_items: list, body_sections: str, svg_inline: str) -> str:
    nav_html = "\n".join(f'<a href="#{nid}">{html.escape(label)}</a>' for nid, label in nav_items)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
:root {{
  --bg: #ffffff; --fg: #0f172a; --muted: #475569; --card: #f8fafc; --border: #e2e8f0; --accent: #0f766e; --code-bg: #f1f5f9;
}}
[data-theme="dark"] {{
  --bg: #0b1120; --fg: #e2e8f0; --muted: #94a3b8; --card: #111827; --border: #1e293b; --accent: #2dd4bf; --code-bg: #1e293b;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--fg); line-height: 1.6; display: flex; min-height: 100vh; }}
aside {{ width: 260px; flex-shrink: 0; border-right: 1px solid var(--border); padding: 20px 16px; position: sticky; top: 0; height: 100vh; overflow-y: auto; background: var(--card); }}
aside h1 {{ font-size: 15px; margin: 0 0 6px; }}
aside .sub {{ font-size: 12px; color: var(--muted); margin-bottom: 14px; }}
aside input {{ width: 100%; padding: 7px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--fg); margin-bottom: 12px; font-size: 13px; }}
aside nav a {{ display: block; padding: 6px 8px; border-radius: 6px; color: var(--fg); text-decoration: none; font-size: 13px; margin-bottom: 2px; }}
aside nav a:hover {{ background: var(--border); }}
aside button {{ width: 100%; margin-top: 10px; padding: 7px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--fg); cursor: pointer; font-size: 12px; }}
main {{ flex: 1; max-width: 1060px; padding: 28px 36px; overflow-x: auto; }}
section {{ margin-bottom: 42px; padding-bottom: 24px; border-bottom: 1px solid var(--border); }}
h2 {{ color: var(--accent); margin-top: 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }}
th, td {{ border: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: var(--card); }}
pre {{ background: var(--code-bg); padding: 12px 14px; border-radius: 8px; overflow-x: auto; font-size: 12px; }}
code {{ background: var(--code-bg); padding: 2px 5px; border-radius: 4px; font-size: 12px; }}
pre code {{ padding: 0; background: transparent; }}
.svg-wrap svg {{ max-width: 100%; height: auto; }}
.gallery-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; }}
.shot-card {{ margin: 0; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--card); }}
.shot-card img {{ width: 100%; display: block; border-bottom: 1px solid var(--border); }}
.shot-card figcaption {{ padding: 10px 12px; font-size: 12px; }}
.muted {{ color: var(--muted); }}
@media print {{ aside {{ display: none; }} main {{ max-width: none; padding: 12px; }} }}
</style>
</head>
<body>
<aside>
  <h1>{html.escape(title)}</h1>
  <div class="sub">{html.escape(subtitle)}</div>
  <input id="q" type="search" placeholder="Filter sections..." oninput="filterSecs(this.value)"/>
  <nav>{nav_html}</nav>
  <button onclick="toggleTheme()">Toggle Light / Dark</button>
</aside>
<main>
  <div class="svg-wrap">{svg_inline}</div>
  {body_sections}
</main>
<script>
function toggleTheme() {{
  const cur = document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
}}
function filterSecs(q) {{
  q = (q || '').toLowerCase();
  document.querySelectorAll('main section').forEach(s => {{
    s.style.display = (!q || s.textContent.toLowerCase().includes(q)) ? '' : 'none';
  }});
}}
</script>
</body>
</html>
'''


def render_view(bundle_dir: pathlib.Path, out_html: pathlib.Path, title: str, subtitle: str, doc_list: list, svg_inline: str, include_gallery: bool = False) -> int:
    nav = []
    parts = []
    blocked_total = 0
    if include_gallery:
        nav.append(("gallery", "05 Visual Gallery"))
        parts.append(build_screenshot_gallery_html(bundle_dir))
    for sec_id, label, filename in doc_list:
        fp = bundle_dir / filename
        if not fp.exists():
            continue
        nav.append((sec_id, label))
        raw_html = md_to_html(fp.read_text(encoding="utf-8"))
        safe_html, blocked = sanitize_block_file_urls(raw_html)
        blocked_total += blocked
        parts.append(f'<section id="{sec_id}">{safe_html}</section>')
    out_html.write_text(wrap_html(title, subtitle, nav, "\n".join(parts), svg_inline), encoding="utf-8")
    return blocked_total


def render_docx(bundle_dir: pathlib.Path, out_docx: pathlib.Path):
    from docx import Document
    doc = Document()
    doc.add_heading("spec-anything Executive & Engineering Specification Review", level=0)
    for fn in ["01_PRD.md", "02_SDD.md", "03_scope_matrix.md", "04_reproduction_env.md", "07_parity_tests.md", "12_implementation_sequence.md"]:
        fp = bundle_dir / fn
        if not fp.exists():
            continue
        doc.add_heading(fn.replace(".md", ""), level=1)
        for line in fp.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("```"):
                continue
            if s.startswith("### "):
                doc.add_heading(s[4:], level=3)
            elif s.startswith("## "):
                doc.add_heading(s[3:], level=2)
            elif s.startswith("# "):
                continue
            else:
                doc.add_paragraph(s)
    doc.save(str(out_docx))


def render_pdf_safe(html_path: pathlib.Path, pdf_path: pathlib.Path):
    """Render HTML to PDF via Playwright while strictly aborting external file:// or remote fetches."""
    from playwright.sync_api import sync_playwright
    html_content = html_path.read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort() if route.request.url.startswith(("file://", "http://", "https://")) else route.continue_())
        page.set_content(html_content, wait_until="load")
        page.pdf(path=str(pdf_path), format="A4", print_background=True, margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
        browser.close()


def main():
    ap = argparse.ArgumentParser(description="Render dual-audience HTML, SVG, DOCX, and safe PDF review artifacts")
    ap.add_argument("bundle_dir")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--formats", default="html,docx,pdf", help="Comma-separated formats: html,docx,pdf")
    args = ap.parse_args()

    bdir = pathlib.Path(args.bundle_dir).resolve()
    odir = pathlib.Path(args.outdir).resolve()
    odir.mkdir(parents=True, exist_ok=True)
    fmts = {x.strip().lower() for x in args.formats.split(",") if x.strip()}

    svg_path = odir / "architecture-flow.svg"
    svg_inline = generate_flow_svg(bdir, svg_path)
    outputs = [str(svg_path)]
    blocked_file_urls = 0

    pm_html = odir / "pm-design-review.html"
    dev_html = odir / "dev-qa-parity.html"

    if "html" in fmts or "pdf" in fmts:
        blocked_file_urls += render_view(
            bdir, pm_html,
            "PM & Design Review — spec-anything",
            "01 PRD · 03 Scope · 05 Visual Evidence · 11 UI Tokens",
            [
                ("doc-01", "01 PRD", "01_PRD.md"),
                ("doc-03", "03 Scope Matrix", "03_scope_matrix.md"),
                ("doc-05", "05 UI Reference", "05_ui_reference.md"),
                ("doc-11", "11 UI Implementation", "11_ui_implementation.md"),
            ],
            svg_inline, include_gallery=True,
        )
        blocked_file_urls += render_view(
            bdir, dev_html,
            "Dev & QA Parity Review — spec-anything",
            "02 SDD · 04 REA Audit · 06 Ledger · 07 Parity · 09 Contracts · 10/08/12",
            [
                ("doc-02", "02 SDD", "02_SDD.md"),
                ("doc-04", "04 Reproduction & REA", "04_reproduction_env.md"),
                ("doc-06", "06 Behavior Evidence", "06_behavior_evidence.md"),
                ("doc-07", "07 Parity Tests", "07_parity_tests.md"),
                ("doc-09", "09 Machine Contracts", "09_contracts.md"),
                ("doc-10", "10 Execution & State", "10_execution_and_state.md"),
                ("doc-08", "08 Blueprint", "08_implementation_blueprint.md"),
                ("doc-12", "12 Sequence", "12_implementation_sequence.md"),
            ],
            svg_inline, include_gallery=False,
        )
        outputs += [str(pm_html), str(dev_html)]

    if "docx" in fmts:
        docx_path = odir / "spec-review.docx"
        render_docx(bdir, docx_path)
        outputs.append(str(docx_path))

    if "pdf" in fmts:
        pm_pdf = odir / "pm-design-review.pdf"
        render_pdf_safe(pm_html, pm_pdf)
        outputs.append(str(pm_pdf))

    print(json.dumps({"status": "ok", "blocked_file_urls": blocked_file_urls, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
