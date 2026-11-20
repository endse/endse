#!/usr/bin/env python3
"""Growing contribution snake.

Unlike Platane/snk (fixed 4-segment snake) this one plays real Snake:
it starts as a single head, hunts the nearest contribution square, and grows
as it eats. Darker squares (more commits) give more growth (+1..+4). Growth is
scaled so the snake keeps growing for the whole run and tops out at MAX_LENGTH.

Output: a single self-contained animated SVG (pure CSS keyframes, so it plays
inside GitHub's <img> sandbox).

    python scripts/generate_snake.py            # real data for PROFILE_USER
    python scripts/generate_snake.py --demo     # random grid, no network
"""
from __future__ import annotations

import argparse
import random
from collections import deque
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "contribution-snake.svg"

MAX_LENGTH = 48          # readable cap (segments incl. head)
PITCH, CELL = 16, 12     # grid spacing / square size (px), same as GitHub
ROWS = 7
PAD_X, PAD_TOP, PAD_BOTTOM = 40, 58, 50
OUTRO = 2.6              # seconds: snake fades, board refills, loop restarts

# palette (matches the hero banner)
BG, BORDER, EMPTY = "#0d1117", "#30363d", "#161b22"
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
HEAD, MID, TAIL = (0x22, 0xD3, 0xEE), (0x8B, 0x5C, 0xF6), (0xEC, 0x48, 0x99)
FLASH = "#a5f3fc"

Cell = tuple[int, int]


# --------------------------------------------------------------------------- simulation

def _neighbours(cell: Cell, heading: Cell) -> list[Cell]:
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    if heading in dirs:                     # prefer going straight -> smoother path
        dirs.remove(heading)
        dirs.insert(0, heading)
    return [(cell[0] + dx, cell[1] + dy) for dx, dy in dirs]


def _bfs(start: Cell, heading: Cell, targets: set[Cell], body: list[Cell], cols: int,
         avoid_body: bool) -> list[Cell] | None:
    """Shortest path to the nearest target. A body cell is blocked until that
    segment will have slid off it (segment k frees its cell after len-k steps)."""
    free_at = {c: len(body) - k for k, c in enumerate(body) if k} if avoid_body else {}
    prev: dict[Cell, Cell | None] = {start: None}
    queue = deque([(start, heading, 0)])
    while queue:
        cell, head_dir, dist = queue.popleft()
        if cell in targets:
            path = []
            while cell != start:
                path.append(cell)
                cell = prev[cell]
            return path[::-1]
        for nxt in _neighbours(cell, head_dir):
            x, y = nxt
            if nxt in prev or not (-1 <= x <= cols and -1 <= y <= ROWS):
                continue
            if free_at.get(nxt, 0) > dist + 1:
                continue
            prev[nxt] = cell
            queue.append((nxt, (x - cell[0], y - cell[1]), dist + 1))
    return None


def simulate(levels: dict[Cell, int], cols: int):
    """Returns (head positions per step, length per step, step each cell was eaten)."""
    start: Cell = (-1, ROWS // 2)
    targets = set(levels)
    total_growth = sum(levels.values()) or 1
    scale = min(1.0, (MAX_LENGTH - 1) / total_growth)

    body = [start]
    path, lengths, eaten = [start], [1], {}
    pending, credit, heading = 0, 0.0, (1, 0)
    while targets:
        route = (_bfs(body[0], heading, targets, body, cols, avoid_body=True)
                 or _bfs(body[0], heading, targets, body, cols, avoid_body=False))
        if not route:
            break
        for cell in route:
            heading = (cell[0] - body[0][0], cell[1] - body[0][1])
            body.insert(0, cell)
            if pending > 0 and len(body) <= MAX_LENGTH:
                pending -= 1                # grow: tail stays where it was
            else:
                body.pop()
            if cell in targets:
                targets.discard(cell)
                eaten[cell] = len(path)
                credit += levels[cell] * scale
                gained = int(credit)
                credit -= gained
                pending += gained
            path.append(cell)
            lengths.append(len(body))
    return path, lengths, eaten


# --------------------------------------------------------------------------- rendering

def _mix(a, b, t):
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _segment_colour(i: int) -> str:
    t = i / max(1, MAX_LENGTH - 1)
    return _mix(HEAD, MID, t * 2) if t < 0.5 else _mix(MID, TAIL, (t - 0.5) * 2)


def _pct(value: float) -> str:
    return f"{max(0.0, min(100.0, value)):.3f}".rstrip("0").rstrip(".") + "%"


def _centre(cell: Cell) -> tuple[float, float]:
    return cell[0] * PITCH + CELL / 2, cell[1] * PITCH + CELL / 2


def render(levels: dict[Cell, int], cols: int, total: int | None) -> str:
    path, lengths, eaten = simulate(levels, cols)
    steps = len(path) - 1
    dt = min(0.14, max(0.06, 55 / max(steps, 1)))          # seconds per step
    move = steps * dt
    period = move + OUTRO
    pct = lambda s: _pct(s * dt / period * 100)            # noqa: E731 step -> keyframe %
    end_pct = move / period * 100

    width = cols * PITCH - (PITCH - CELL) + 2 * PAD_X
    height = ROWS * PITCH - (PITCH - CELL) + PAD_TOP + PAD_BOTTOM
    css: list[str] = []

    # head path: keyframes only where the direction changes
    keys = [0]
    for s in range(1, steps):
        a, b, c = path[s - 1], path[s], path[s + 1]
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            keys.append(s)
    keys.append(steps)
    frames = "".join(f"{pct(s)}{{transform:translate({_centre(path[s])[0]:g}px,{_centre(path[s])[1]:g}px)}}"
                     for s in keys)
    css.append(f"@keyframes mv{{{frames}100%{{transform:translate({_centre(path[-1])[0]:g}px,"
               f"{_centre(path[-1])[1]:g}px)}}}}")

    # head rotation (eyes look where it's going)
    angle = {(1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): 270}
    rot_frames, last = [], None
    for s in range(1, steps + 1):
        d = (path[s][0] - path[s - 1][0], path[s][1] - path[s - 1][1])
        if angle[d] != last:
            if last is not None:
                rot_frames.append(f"{pct(s - 1)}{{transform:rotate({last}deg)}}")
            rot_frames.append(f"{pct(s - 1 + 0.25)}{{transform:rotate({angle[d]}deg)}}")
            last = angle[d]
    css.append(f"@keyframes rt{{0%{{transform:rotate(0deg)}}{''.join(rot_frames)}"
               f"100%{{transform:rotate({last or 0}deg)}}}}")

    # whole-snake fade in / out around the loop
    css.append(f"@keyframes fd{{0%{{opacity:0}}{_pct(0.6)}{{opacity:1}}{_pct(end_pct + 0.5)}{{opacity:1}}"
               f"{_pct(end_pct + 30 * (100 - end_pct) / 100)},100%{{opacity:0}}}}")
    refill = end_pct + 55 * (100 - end_pct) / 100

    seg_svg, max_len = [], max(lengths)
    for i in range(max_len - 1, -1, -1):                  # tail first, head drawn on top
        size = CELL - 5 * i / max(1, MAX_LENGTH - 1) if i else CELL + 3
        delay = f"{i * dt:.3f}s"
        if i == 0:
            seg_svg.append(
                f'<g class="sg" style="animation-delay:0s"><g class="hd">'
                f'<rect x="{-size / 2:g}" y="{-size / 2:g}" width="{size:g}" height="{size:g}" rx="5" '
                f'fill="{_segment_colour(0)}" filter="url(#glow)"/>'
                f'<circle cx="2.6" cy="-3" r="2.1" fill="#fff"/><circle cx="2.6" cy="3" r="2.1" fill="#fff"/>'
                f'<circle cx="3.3" cy="-3" r="1.1" fill="#0d1117"/><circle cx="3.3" cy="3" r="1.1" fill="#0d1117"/>'
                f'</g></g>')
            continue
        born = next(s for s, n in enumerate(lengths) if n > i)
        css.append(f"@keyframes v{i}{{0%,{pct(born - 0.01)}{{opacity:0}}{pct(born)},100%{{opacity:1}}}}")
        seg_svg.append(
            f'<g class="sg" style="animation:mv {period:.3f}s linear {delay} infinite backwards,'
            f'v{i} {period:.3f}s step-end infinite">'
            f'<rect x="{-size / 2:.2f}" y="{-size / 2:.2f}" width="{size:.2f}" height="{size:.2f}" '
            f'rx="{min(4, size / 3):.1f}" fill="{_segment_colour(i)}"/></g>')

    # board: squares vanish when eaten (with a bite flash) and refill during the outro
    cells_svg = []
    for (x, y), level in sorted(levels.items()):
        name = f"c{x}_{y}"
        s = eaten.get((x, y))
        attrs = f'x="{x * PITCH}" y="{y * PITCH}" width="{CELL}" height="{CELL}" rx="2.5"'
        if s is None:
            cells_svg.append(f'<rect {attrs} fill="{LEVELS[level]}"/>')
            continue
        css.append(f"@keyframes {name}{{0%,{pct(s - 1)}{{fill:{LEVELS[level]}}}{pct(s - 0.5)}{{fill:{FLASH}}}"
                   f"{pct(s)},{_pct(refill)}{{fill:{EMPTY}}}100%{{fill:{LEVELS[level]}}}}}")
        cells_svg.append(f'<rect {attrs} fill="{LEVELS[level]}" style="animation-name:{name}" class="ce"/>')
    empty_svg = "".join(
        f'<rect x="{x * PITCH}" y="{y * PITCH}" width="{CELL}" height="{CELL}" rx="2.5" fill="{EMPTY}"/>'
        for x in range(cols) for y in range(ROWS) if (x, y) not in levels and (x, y) in _BOARD)

    # live length counter
    counter_svg = []
    for n in range(1, max_len + 1):
        first = next(s for s, v in enumerate(lengths) if v >= n)
        nxt = next((s for s, v in enumerate(lengths) if v > n), None)
        hide = f"{pct(nxt - 0.01)},100%{{opacity:0}}" if nxt is not None else ""
        css.append(f"@keyframes n{n}{{0%{{opacity:0}}{pct(first)}{{opacity:1}}{hide}}}")
        counter_svg.append(f'<text class="nm" style="animation-name:n{n}">{n}</text>')

    total_txt = f"{total:,} contributions in the last year" if total is not None else "last 12 months"
    grid_w = cols * PITCH - (PITCH - CELL)
    legend = "".join(f'<rect x="{34 + k * 15}" y="-9" width="11" height="11" rx="2.5" fill="{c}"/>'
                     for k, c in enumerate(LEVELS))
    style = f"""
text{{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif;fill:#8b949e;font-size:12px}}
.mono{{font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace}}
.ti{{fill:#e6edf3;font-size:14px;font-weight:600}}
.sg{{animation:mv {period:.3f}s linear infinite}}
.hd{{animation:rt {period:.3f}s linear infinite;transform-box:fill-box;transform-origin:center}}
.snake{{animation:fd {period:.3f}s linear infinite}}
.ce{{animation-duration:{period:.3f}s;animation-timing-function:linear;animation-iteration-count:infinite}}
.nm{{opacity:0;fill:#22d3ee;font-weight:700;font-size:13px;animation:none {period:.3f}s step-end infinite}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.nm:last-child{{opacity:1}}}}
""" + "\n".join(css)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">
<title id="t">Contribution snake</title>
<desc id="d">A snake that grows as it eats {USER_LABEL}'s GitHub contribution squares. Generated by scripts/generate_snake.py</desc>
<defs><filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.4" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<style>{style}</style>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>
<circle cx="22" cy="22" r="5" fill="#ff5f57"/><circle cx="38" cy="22" r="5" fill="#febc2e"/><circle cx="54" cy="22" r="5" fill="#28c840"/>
<text x="72" y="26" class="ti mono">~/commit-snake</text>
<text x="{width - 20}" y="26" text-anchor="end">{total_txt}</text>
<g transform="translate({PAD_X},{PAD_TOP})">{empty_svg}{"".join(cells_svg)}<g class="snake">{"".join(seg_svg)}</g></g>
<g transform="translate({PAD_X},{PAD_TOP + ROWS * PITCH + 26})">
<text x="0" y="0">Less</text>{legend}<text x="{34 + 5 * 15 + 4}" y="0">More</text>
<text x="{grid_w / 2:g}" y="0" text-anchor="middle" class="mono">eats commits · grows +1 to +4 per square</text>
<text x="{grid_w - 26}" y="0" text-anchor="end" class="mono">length</text>
<g transform="translate({grid_w},0)" text-anchor="end">{"".join(counter_svg)}</g>
</g>
</svg>'''


_BOARD: set[Cell] = set()
USER_LABEL = "endse"


def load(demo: bool) -> tuple[set[Cell], dict[Cell, int], int, int | None]:
    global USER_LABEL
    if demo:
        rng = random.Random(7)
        today = date.today()
        cols = 53
        board = {(x, y) for x in range(cols) for y in range(ROWS)
                 if not (x == cols - 1 and y > (today.weekday() + 1) % 7)}
        levels = {c: rng.choice([1, 1, 1, 2, 2, 3, 4]) for c in board if rng.random() < 0.3}
        return board, levels, cols, None
    from github_api import USERNAME, contribution_calendar
    USER_LABEL = USERNAME
    days, total = contribution_calendar()
    board = {(d.week, d.weekday) for d in days}
    levels = {(d.week, d.weekday): d.level for d in days if d.level > 0}
    return board, levels, max(d.week for d in days) + 1, total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", action="store_true", help="random data, no network")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    board, levels, cols, total = load(args.demo)
    _BOARD.update(board)
    svg = render(levels, cols, total)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(svg, encoding="utf-8")
    print(f"Snake: {len(levels)} squares, {cols} weeks, {len(svg) / 1024:.0f} KB -> {args.out}")


if __name__ == "__main__":
    main()
