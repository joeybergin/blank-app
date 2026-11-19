"""Styling and HTML snippets that make the app look like cashgenerator.co.uk."""

from __future__ import annotations

import html
import re
import json

from .config import BLUE, NAVY, STORE, YELLOW

_CSS = f"""
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{ --cg-blue:{BLUE}; --cg-navy:{NAVY}; --cg-yellow:{YELLOW}; }}
html, body, .stApp, .stMarkdown, p, h1, h2, h3, h4, label, button, input, textarea {{
  font-family: 'Montserrat', sans-serif;
}}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
.stApp {{ background:#f4f6fa; }}
.block-container {{ padding-top: 4.2rem; max-width: 1200px; }}
h1, h2, h3, h4 {{ color: var(--cg-blue); font-weight: 800 !important; letter-spacing:-.2px; }}

/* Top navigation bar */
header[data-testid="stHeader"] {{ background: var(--cg-blue); }}
header[data-testid="stHeader"] a, header[data-testid="stHeader"] span,
header[data-testid="stHeader"] p {{ color:#fff !important; font-weight:600; }}
header[data-testid="stHeader"] svg {{ fill:#fff; color:#fff; }}
[data-testid="stTopNavLink"][aria-current="page"],
[data-testid="stTopNavLink"]:hover {{ background: rgba(255,184,28,.22) !important; }}

/* Buttons */
.stButton > button, .stLinkButton > a, .stFormSubmitButton > button {{
  border-radius: 6px; font-weight: 700; border: 2px solid var(--cg-blue);
}}
.stButton > button[kind^="primary"], .stFormSubmitButton > button[kind^="primary"],
.stLinkButton > a[kind^="primary"] {{
  background: var(--cg-yellow); color: #111 !important; border-color: var(--cg-yellow);
}}
.stButton > button[kind^="primary"]:hover, .stLinkButton > a[kind^="primary"]:hover {{
  background: #f0a500; border-color:#f0a500; color:#111 !important;
}}
.stButton > button[kind^="secondary"], .stLinkButton > a[kind^="secondary"] {{
  color: var(--cg-blue) !important; background:#fff;
}}

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] {{ background:#fff; border-radius:10px; }}
.cg-card-title {{ font-weight:700; font-size:.92rem; line-height:1.3; min-height:2.6em;
  color:#1a1a1a; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
.cg-price {{ color: var(--cg-blue); font-size:1.35rem; font-weight:800; }}
.cg-was {{ color:#888; text-decoration: line-through; font-size:.9rem; margin-left:.4rem; }}
.cg-member {{ font-size:.78rem; color:#0a7a2f; font-weight:600; }}
.cg-badge {{ display:inline-block; padding:2px 8px; border-radius:20px; font-size:.7rem; font-weight:700;
  margin-right:4px; background:#e8eefb; color:var(--cg-blue); }}
.cg-badge.sale {{ background:#d61f26; color:#fff; }}
.cg-badge.new {{ background:var(--cg-yellow); color:#111; }}
.cg-img {{ width:100%; aspect-ratio:1/1; object-fit:contain; background:#fff; border-radius:8px; }}
.cg-noimg {{ width:100%; aspect-ratio:1/1; display:flex; align-items:center; justify-content:center;
  font-size:3rem; background:#eef2fa; border-radius:8px; }}

/* Hero */
.cg-hero {{ background: linear-gradient(120deg, {BLUE} 0%, {NAVY} 100%); color:#fff; border-radius:14px;
  padding: 28px 30px; display:flex; gap:24px; align-items:center; flex-wrap:wrap; }}
.cg-hero h1 {{ color:#fff; margin:0 0 6px; font-size:2rem; line-height:1.15; }}
.cg-hero p {{ margin:0; opacity:.92; }}
.cg-hero .accent {{ color: var(--cg-yellow); }}
.cg-hero img {{ height:70px; background:#fff; border-radius:10px; padding:8px 12px; }}
.cg-strip {{ background: var(--cg-yellow); color:#111; font-weight:700; border-radius:8px;
  padding:10px 16px; text-align:center; margin: 12px 0; }}
.cg-tile {{ background:#fff; border-radius:12px; padding:18px; border-top:5px solid var(--cg-yellow);
  height:100%; box-shadow:0 1px 3px rgba(0,0,0,.06); }}
.cg-tile h4 {{ margin:.2rem 0 .3rem; font-size:1.02rem; }}
.cg-tile p {{ margin:0; color:#333; font-size:.9rem; }}
.cg-tile .ic {{ font-size:1.6rem; }}
.cg-voucher {{ border:3px dashed var(--cg-blue); border-radius:12px; background:#fffbe9; padding:16px;
  text-align:center; margin:8px 0; }}
.cg-voucher .code {{ font-size:1.6rem; font-weight:800; letter-spacing:2px; color:var(--cg-blue); }}
.cg-member-card {{ border-radius:16px; padding:22px; color:#fff; max-width:420px;
  background: linear-gradient(135deg, {BLUE}, {NAVY}); box-shadow:0 6px 18px rgba(0,51,160,.35); }}
.cg-member-card .tier {{ color:var(--cg-yellow); font-weight:800; font-size:1.1rem; }}
.cg-member-card .num {{ font-size:1.3rem; letter-spacing:3px; font-weight:700; margin:14px 0 6px; }}
.cg-footer {{ margin-top:40px; background:var(--cg-blue); color:#fff; border-radius:12px; padding:20px 24px;
  font-size:.88rem; }}
.cg-footer a {{ color: var(--cg-yellow) !important; }}
@media (max-width: 640px) {{
  .cg-hero {{ padding:20px; }} .cg-hero h1 {{ font-size:1.5rem; }} .cg-hero img {{ height:52px; }}
}}
</style>
"""


# Markdown ends an HTML block at the first blank line, so strip blank lines and comments.
CSS = "\n".join(l for l in re.sub(r"/\*.*?\*/", "", _CSS).splitlines() if l.strip())


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def gbp(x: float) -> str:
    return f"£{x:,.2f}"


def hero(title: str, subtitle: str, logo: bool = True) -> str:
    img = f'<img src="{STORE["logo"]}" alt="Cash Generator">' if logo else ""
    return f'<div class="cg-hero">{img}<div><h1>{title}</h1><p>{subtitle}</p></div></div>'


def tile(icon: str, title: str, text: str) -> str:
    return (f'<div class="cg-tile"><div class="ic">{icon}</div><h4>{esc(title)}</h4>'
            f'<p>{esc(text)}</p></div>')


def wheel_html(labels: list[str], target: int | None, spin_id: int, result_html: str = "") -> str:
    """Self-contained animated prize wheel. If target is set it spins and lands on it."""
    colours = [BLUE, YELLOW]
    return f"""
<!doctype html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&display=swap" rel="stylesheet">
<style>
 body {{ margin:0; font-family:Montserrat, sans-serif; display:flex; flex-direction:column; align-items:center; }}
 .wrap {{ position:relative; width:340px; height:340px; margin-top:22px; }}
 svg#wheel {{ width:100%; height:100%; transition: transform 5.2s cubic-bezier(.12,.75,.12,1); }}
 .pointer {{ position:absolute; top:-18px; left:50%; transform:translateX(-50%); width:0; height:0;
   border-left:18px solid transparent; border-right:18px solid transparent; border-top:34px solid #d61f26;
   filter: drop-shadow(0 2px 2px rgba(0,0,0,.35)); z-index:2; }}
 .hub {{ position:absolute; inset:0; margin:auto; width:64px; height:64px; border-radius:50%; background:#fff;
   border:5px solid {YELLOW}; display:flex; align-items:center; justify-content:center; color:{BLUE};
   font-weight:800; font-size:13px; box-shadow:0 2px 6px rgba(0,0,0,.3); }}
 #result {{ margin-top:16px; min-height:40px; text-align:center; opacity:0; transition:opacity .6s; }}
 #result.show {{ opacity:1; }}
 @media (max-width:380px) {{ .wrap {{ width:280px; height:280px; }} }}
</style></head><body>
<div class="wrap"><div class="pointer"></div>
<svg id="wheel" viewBox="-160 -160 320 320"></svg><div class="hub">SPIN</div></div>
<div id="result">{result_html}</div>
<script>
const labels = {json.dumps(labels)};
const colours = {json.dumps(colours)};
const target = {json.dumps(target)};
const svg = document.getElementById('wheel');
const n = labels.length, seg = 360 / n, R = 150;
function pt(a, r) {{ const t = (a - 90) * Math.PI / 180; return [r * Math.cos(t), r * Math.sin(t)]; }}
let s = '<circle r="158" fill="{NAVY}"/>';
labels.forEach((l, i) => {{
  const a0 = i * seg, a1 = (i + 1) * seg, [x0, y0] = pt(a0, R), [x1, y1] = pt(a1, R);
  const fill = colours[i % 2], txt = i % 2 ? '#111' : '#fff', mid = a0 + seg / 2;
  s += `<path d="M0 0 L${{x0}} ${{y0}} A${{R}} ${{R}} 0 0 1 ${{x1}} ${{y1}} Z" fill="${{fill}}" stroke="#fff" stroke-width="2"/>`;
  s += `<text transform="rotate(${{mid}}) translate(0 -${{R * 0.62}}) rotate(90)" fill="${{txt}}"
        font-size="13" font-weight="800" text-anchor="middle" dominant-baseline="middle">${{l}}</text>`;
}});
for (let i = 0; i < n * 2; i++) {{ const [x, y] = pt(i * seg / 2, 154);
  s += `<circle cx="${{x}}" cy="${{y}}" r="3" fill="#fff"/>`; }}
svg.innerHTML = s;
const res = document.getElementById('result');
if (target !== null) {{
  const jitter = (Math.random() - 0.5) * seg * 0.6;
  const final = 360 * 7 + (360 - (target * seg + seg / 2)) + jitter;
  requestAnimationFrame(() => requestAnimationFrame(() => {{ svg.style.transform = `rotate(${{final}}deg)`; }}));
  svg.addEventListener('transitionend', () => res.classList.add('show'));
}} else {{ res.classList.add('show'); }}
</script><!-- spin {spin_id} --></body></html>
"""
