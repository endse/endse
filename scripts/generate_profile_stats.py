#!/usr/bin/env python3
"""GitHub stats + top-languages cards (assets/github-stats.svg, assets/top-languages.svg).

Aggregates public, non-fork repos of the user AND the org, so the numbers
reflect everything that's actually been built. Run with GH_TOKEN set for a
higher API rate limit:  python scripts/generate_profile_stats.py
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from html import escape
from pathlib import Path

from github_api import ORG, USERNAME, contribution_calendar, get_json, get_paginated

ASSETS = Path(__file__).resolve().parents[1] / "assets"

W, H = 520, 200
SANS = "'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

LANG_COLOURS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "Dart": "#00B4AB",
    "C++": "#f34b7d", "Java": "#b07219", "HTML": "#e34c26", "CSS": "#563d7c", "Go": "#00ADD8",
    "Rust": "#dea584", "Shell": "#89e051", "Jupyter Notebook": "#DA5B0B", "Kotlin": "#A97BFF",
    "Swift": "#F05138", "C": "#555555", "C#": "#178600", "Vue": "#41b883", "Svelte": "#ff3e00",
}
# build/installer/config "languages" that only add noise to a skills card
EXCLUDED = {"Inno Setup", "NSIS", "Batchfile", "Makefile", "Dockerfile", "Procfile", "CMake", "Smarty", "Roff"}
SIZE_WEIGHT, COUNT_WEIGHT = 0.5, 0.5   # same idea as github-readme-stats: one huge repo can't drown the rest
FALLBACK = ["#22d3ee", "#8b5cf6", "#34d399", "#f59e0b", "#f472b6", "#60a5fa", "#a3e635"]


def _card(title: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#161137"/></linearGradient>
<linearGradient id="accent" x1="0" x2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>
<style>
text{{font-family:{SANS}}}.mono{{font-family:{MONO}}}
.in{{animation:in .8s ease-out both}}
@keyframes in{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
.bar{{transform-box:fill-box;transform-origin:left;animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both}}
.live{{animation:blink 2s ease-in-out infinite}}@keyframes blink{{50%{{opacity:.35}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="url(#bg)" stroke="#2d3359"/>
<rect x="24" y="47" width="60" height="2" rx="1" fill="url(#accent)"/>
<text x="24" y="34" fill="#e6edf3" font-size="14" font-weight="700" class="mono">{escape(title)}</text>
<circle cx="{W - 112}" cy="30" r="3.5" fill="#3fb950" class="live"/>
<text x="{W - 24}" y="34" text-anchor="end" fill="#7d8590" font-size="10.5" class="mono">auto-updated</text>
{body}
</svg>'''


def stats_svg(repos: int, stars: int, forks: int, followers: int, contributions: int | None) -> str:
    values = [("public repos", repos), ("stars earned", stars), ("followers", followers),
              ("contributions", contributions if contributions is not None else "—")]
    cells = []
    for i, (label, value) in enumerate(values):
        x = 24 + i * 118
        shown = f"{value:,}" if isinstance(value, int) else value
        cells.append(
            f'<g class="in" style="animation-delay:{i * 0.12:.2f}s">'
            f'<rect x="{x}" y="66" width="106" height="86" rx="10" fill="#ffffff" fill-opacity=".03" stroke="#ffffff" stroke-opacity=".06"/>'
            f'<text x="{x + 53}" y="112" text-anchor="middle" fill="url(#accent)" font-size="28" font-weight="800">{shown}</text>'
            f'<text x="{x + 53}" y="136" text-anchor="middle" fill="#8b949e" font-size="11">{label}</text></g>')
    footer = (f'<text x="{W / 2:g}" y="180" text-anchor="middle" fill="#6e7681" font-size="10.5" class="mono">'
              f'{USERNAME} + {ORG} · {forks:,} forks · contributions = last 12 months</text>')
    return _card("~/github-stats", "".join(cells) + footer)


def languages_svg(sizes: dict[str, int], counts: dict[str, int]) -> str:
    data = {lang: (size ** SIZE_WEIGHT) * (counts[lang] ** COUNT_WEIGHT)
            for lang, size in sizes.items() if lang not in EXCLUDED and size > 0}
    ranked = sorted(data.items(), key=lambda kv: kv[1], reverse=True)[:8]
    total = sum(v for _, v in ranked) or 1
    if not ranked:
        ranked, total = [("No language data yet", 1)], 1
    bar, used = [], 0.0
    for i, (name, size) in enumerate(ranked):
        width = 472 * size / total if i < len(ranked) - 1 else 472 - used
        bar.append(f'<rect x="{24 + used:.2f}" y="66" width="{max(0.0, width):.2f}" height="12" '
                   f'fill="{LANG_COLOURS.get(name, FALLBACK[i % len(FALLBACK)])}"/>')
        used += width
    legend = []
    for i, (name, size) in enumerate(ranked):
        x, y = 28 + (i % 2) * 240, 102 + (i // 2) * 20
        colour = LANG_COLOURS.get(name, FALLBACK[i % len(FALLBACK)])
        legend.append(
            f'<g class="in" style="animation-delay:{0.3 + i * 0.07:.2f}s"><circle cx="{x + 5}" cy="{y - 4}" r="4.5" fill="{colour}"/>'
            f'<text x="{x + 18}" y="{y}" fill="#e6edf3" font-size="12">{escape(name[:22])}</text>'
            f'<text x="{x + 224}" y="{y}" text-anchor="end" fill="#8b949e" font-size="11" class="mono">{size / total * 100:.1f}%</text></g>')
    body = (f'<clipPath id="pill"><rect x="24" y="66" width="472" height="12" rx="6"/></clipPath>'
            f'<g clip-path="url(#pill)"><g class="bar">{"".join(bar)}</g></g>{"".join(legend)}'
            f'<text x="{W / 2:g}" y="190" text-anchor="middle" fill="#6e7681" font-size="10" class="mono">'
            f'weighted by code size + number of repos · {USERNAME} + {ORG}</text>')
    return _card("~/top-languages", body)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    user = get_json(f"https://api.github.com/users/{USERNAME}")
    personal = [r for r in get_paginated(f"https://api.github.com/users/{USERNAME}/repos") if not r.get("fork")]
    try:
        org = [r for r in get_paginated(f"https://api.github.com/orgs/{ORG}/repos") if not r.get("fork")]
    except Exception as error:  # noqa: BLE001
        print(f"Org repo lookup skipped: {error}")
        org = []
    repos = personal + org
    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    forks = sum(int(r.get("forks_count", 0)) for r in repos)

    languages: dict[str, int] = {}
    repo_counts: dict[str, int] = {}
    skipped = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(get_json, r["languages_url"]) for r in repos if r.get("languages_url")]
        for job in as_completed(jobs):
            try:
                for lang, size in (job.result() or {}).items():
                    languages[lang] = languages.get(lang, 0) + int(size)
                    repo_counts[lang] = repo_counts.get(lang, 0) + 1
            except Exception as error:  # noqa: BLE001
                skipped += 1
                print(f"Skipping a language endpoint: {error}")

    try:
        _, contributions = contribution_calendar()
    except Exception as error:  # noqa: BLE001
        print(f"Contribution total skipped: {error}")
        contributions = None

    (ASSETS / "github-stats.svg").write_text(
        stats_svg(len(repos), stars, forks, int(user.get("followers", 0)), contributions), encoding="utf-8")
    (ASSETS / "top-languages.svg").write_text(languages_svg(languages, repo_counts), encoding="utf-8")
    print(f"Stats: personal={len(personal)} org={len(org)} stars={stars} languages={len(languages)} "
          f"contributions={contributions} skipped={skipped}")


if __name__ == "__main__":
    main()
