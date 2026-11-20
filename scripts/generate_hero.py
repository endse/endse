#!/usr/bin/env python3
"""Animated hero banner (assets/hero.svg).

Self-contained SVG: CSS + SMIL animations only, system fonts, no external
requests, so it renders crisply inside GitHub's <img> sandbox.
Edit the CONFIG block and re-run:  python scripts/generate_hero.py
"""
from __future__ import annotations

from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "assets" / "hero.svg"

# ----------------------------------------------------------------- CONFIG
NAME = "Chirag"
PROMPT = "chirag@dev:~$ whoami"
ROLES = ["AI/ML Engineer", "Full-Stack Developer", "App Developer", "RAG & Agent Systems Builder"]
TAGLINE = "Building useful AI, reliable backends and apps people actually use."
STACK = "python · typescript · dart · fastapi · node · react · flutter · pytorch"
STATUS = "open to full-time & freelance"
# ------------------------------------------------------------------------

W, H = 1200, 320
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
CW = 15.6                     # forced monospace advance at 26px (0.6em) via textLength
ROLE_X, ROLE_Y = 92, 206
TYPE, DELETE, HOLD, GAP = 0.075, 0.035, 1.7, 0.35


def _typing_timeline():
    """Discrete events (t, role, chars) for type -> hold -> delete for every role."""
    events, t = [], 0.0
    for r, role in enumerate(ROLES):
        for n in range(len(role) + 1):
            events.append((t, r, n))
            t += TYPE
        t += HOLD
        for n in range(len(role) - 1, -1, -1):
            events.append((t, r, n))
            t += DELETE
        t += GAP
    return events, t


def _smil(attr: str, values: list, times: list[float], dur: float) -> str:
    key_times = ";".join(f"{x / dur:.4f}" for x in times)
    vals = ";".join(str(v) for v in values)
    return (f'<animate attributeName="{attr}" values="{vals}" keyTimes="{key_times}" '
            f'dur="{dur:.2f}s" calcMode="discrete" repeatCount="indefinite"/>')


def _rotator() -> str:
    events, dur = _typing_timeline()
    times = [e[0] for e in events]
    clip = _smil("width", [round(e[2] * CW, 1) for e in events], times, dur)
    cursor = _smil("x", [round(ROLE_X + e[2] * CW + 2, 1) for e in events], times, dur)
    texts = []
    for r, role in enumerate(ROLES):
        vis = _smil("opacity", [1 if e[1] == r else 0 for e in events], times, dur)
        texts.append(f'<text x="{ROLE_X}" y="{ROLE_Y}" class="role" textLength="{len(role) * CW:g}" '
                     f'lengthAdjust="spacingAndGlyphs" opacity="{1 if r == 0 else 0}">{escape(role)}{vis}</text>')
    return f'''<clipPath id="typed"><rect x="{ROLE_X}" y="{ROLE_Y - 30}" width="0" height="40">{clip}</rect></clipPath>
<text x="56" y="{ROLE_Y}" class="role" fill="#a78bfa">&gt;_</text>
<g clip-path="url(#typed)">{"".join(texts)}</g>
<rect class="cursor" x="{ROLE_X + 2}" y="{ROLE_Y - 22}" width="13" height="27" rx="2">{cursor}</rect>'''


NODES = [(860, 110), (950, 80), (1050, 125), (1120, 92), (905, 205), (1000, 190), (1095, 230), (960, 270), (850, 260)]
EDGES = [(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (2, 5), (3, 6), (4, 5), (5, 6), (4, 7), (5, 7), (7, 8), (4, 8), (2, 6)]
PACKETS = [(0, 1, 2, 3), (8, 4, 5, 6), (7, 5, 2, 3), (0, 4, 7, 8)]


def _network() -> str:
    edges = "".join(
        f'<line x1="{NODES[a][0]}" y1="{NODES[a][1]}" x2="{NODES[b][0]}" y2="{NODES[b][1]}" class="edge" '
        f'style="animation-delay:-{i * 0.37:.2f}s"/>' for i, (a, b) in enumerate(EDGES))
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="{7 if i % 3 == 0 else 5}" class="node {"v" if i % 2 else "c"}" '
        f'style="animation-delay:-{i * 0.45:.2f}s"/>' for i, (x, y) in enumerate(NODES))
    packets = []
    for i, route in enumerate(PACKETS):
        d = "M" + " L".join(f"{NODES[n][0]},{NODES[n][1]}" for n in route)
        packets.append(f'<circle r="3" fill="{"#22d3ee" if i % 2 == 0 else "#f0abfc"}" filter="url(#glow)">'
                       f'<animateMotion dur="{3.2 + i * 0.7:.1f}s" begin="-{i * 1.1:.1f}s" repeatCount="indefinite" '
                       f'path="{d}"/></circle>')
    return f'<g class="net">{edges}{nodes}{"".join(packets)}</g>'


def build() -> str:
    status_w = 58 + len(STATUS) * 7.2
    sx = W - 40 - status_w
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">Hey, I'm {escape(NAME)} - {escape(" / ".join(ROLES[:3]))}</title>
<desc id="desc">{escape(TAGLINE)}</desc>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#070b16"/><stop offset=".55" stop-color="#0c1230"/><stop offset="1" stop-color="#1a1147"/></linearGradient>
<linearGradient id="name" x1="0" x2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#818cf8"/><stop offset="1" stop-color="#c084fc"/></linearGradient>
<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22d3ee" stop-opacity="0"/><stop offset=".5" stop-color="#22d3ee" stop-opacity=".07"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></linearGradient>
<radialGradient id="blobC"><stop offset="0" stop-color="#22d3ee" stop-opacity=".22"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
<radialGradient id="blobV"><stop offset="0" stop-color="#8b5cf6" stop-opacity=".35"/><stop offset="1" stop-color="#8b5cf6" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#94a3b8" stroke-opacity=".06"/></pattern>
<clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
text{{font-family:{SANS}}}
.mono,.role{{font-family:{MONO}}}
.prompt{{fill:#7d8590;font-size:15px}}
.hi{{fill:#f0f6fc;font-size:62px;font-weight:800;letter-spacing:-1px}}
.role{{fill:#67e8f9;font-size:26px;font-weight:600}}
.tag{{fill:#c9d1d9;font-size:19px}}
.stack{{fill:#6e7681;font-size:14px}}
.cursor{{fill:#22d3ee;animation:blink 1s steps(1) infinite}}
.edge{{stroke:#818cf8;stroke-opacity:.45;stroke-width:1.4;stroke-dasharray:6 6;animation:flow 2.4s linear infinite}}
.node{{transform-box:fill-box;transform-origin:center;animation:pulse 2.8s ease-in-out infinite}}
.node.c{{fill:#22d3ee}}.node.v{{fill:#a78bfa}}
.wave{{transform-box:fill-box;transform-origin:70% 80%;animation:wave 2.6s ease-in-out infinite}}
.blob1{{animation:drift 14s ease-in-out infinite alternate}}
.blob2{{animation:drift 18s ease-in-out infinite alternate-reverse}}
.scan{{animation:scan 7s linear infinite}}
.dot{{transform-box:fill-box;transform-origin:center;animation:ping 2s ease-out infinite}}
.fade{{animation:rise .9s ease-out both}}
.d1{{animation-delay:.15s}}.d2{{animation-delay:.3s}}.d3{{animation-delay:.45s}}
@keyframes blink{{50%{{opacity:0}}}}
@keyframes flow{{to{{stroke-dashoffset:-24}}}}
@keyframes pulse{{0%,100%{{transform:scale(1);opacity:.85}}50%{{transform:scale(1.45);opacity:1}}}}
@keyframes wave{{0%,60%,100%{{transform:rotate(0)}}10%,30%{{transform:rotate(16deg)}}20%,40%{{transform:rotate(-8deg)}}}}
@keyframes drift{{to{{transform:translate(60px,30px)}}}}
@keyframes scan{{from{{transform:translateY(-120px)}}to{{transform:translateY({H + 40}px)}}}}
@keyframes ping{{0%{{transform:scale(1);opacity:.7}}100%{{transform:scale(2.8);opacity:0}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<rect width="{W}" height="{H}" fill="url(#grid)"/>
<circle class="blob1" cx="180" cy="40" r="260" fill="url(#blobC)"/>
<circle class="blob2" cx="1000" cy="230" r="320" fill="url(#blobV)"/>
<rect class="scan" y="0" width="{W}" height="90" fill="url(#scan)"/>
{_network()}
</g>
<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="21.5" fill="none" stroke="#818cf8" stroke-opacity=".35" stroke-width="1.5"/>
<circle cx="40" cy="38" r="6" fill="#ff5f57"/><circle cx="60" cy="38" r="6" fill="#febc2e"/><circle cx="80" cy="38" r="6" fill="#28c840"/>
<text x="104" y="43" class="prompt mono">{escape(PROMPT)}</text>
<g class="status">
<rect x="{sx:.0f}" y="22" width="{status_w:.0f}" height="32" rx="16" fill="#0f2a1e" stroke="#2ea043" stroke-opacity=".6"/>
<circle class="dot" cx="{sx + 20:.0f}" cy="38" r="5" fill="#3fb950"/><circle cx="{sx + 20:.0f}" cy="38" r="5" fill="#3fb950"/>
<text x="{sx + 34:.0f}" y="43" class="mono" fill="#7ee787" font-size="13">{escape(STATUS)}</text>
</g>
<g class="fade"><text x="54" y="138" class="hi" textLength="{30.7 * (9 + len(NAME)):.0f}" lengthAdjust="spacingAndGlyphs">Hey, I'm <tspan fill="url(#name)">{escape(NAME)}</tspan></text>
<text x="{54 + 30.7 * (9 + len(NAME)) + 20:.0f}" y="134" font-size="52" class="wave">👋</text></g>
<g class="fade d1">{_rotator()}</g>
<text x="56" y="256" class="tag fade d2">{escape(TAGLINE)}</text>
<text x="56" y="290" class="stack mono fade d3">{escape(STACK)}</text>
</svg>'''


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"Hero: {len(svg) / 1024:.1f} KB -> {OUT}")
