#!/usr/bin/env python3
"""
Render a GitHub contribution calendar as a side-scrolling arcade shooter.

The grid starts as a field of identical blocks. A rocket sweeps left to right
firing downward; every block that is NOT a real contribution takes a hit and
explodes, so what survives is the actual commit pattern. When the sweep ends
the surviving cells pulse once together.

The rocket is drawn as real geometry, not a triangle: gradient-shaded fuselage,
red nose cone, glazed porthole, swept fins, engine bell and a three-layer
flicker flame.

No third-party dependencies: standard library only, so the Action needs no
pip install step.
"""

from __future__ import annotations

import argparse
import calendar
import html
import math
import os
import random
import re
import sys
import urllib.request
from dataclasses import dataclass

CONTRIB_URL = "https://github.com/users/{user}/contributions"

# ── grid geometry ─────────────────────────────────────────────────────────
CELL = 11
GAP = 3
PITCH = CELL + GAP
DAYS = 7

PAD_L = 34          # weekday labels
PAD_R = 22
GRID_TOP = 116
LANE_Y = 84.0       # rocket centreline
FOOT = 22          # no caption under the grid, so less room needed

# ── timing (seconds) ──────────────────────────────────────────────────────
LOOP = 24.0
SWEEP_START = 1.7
SWEEP_END = 17.7            # ~0.30 s per column
BULLET_LAG = 0.20           # time of flight, so cells die just after the pass
SHOT_CYCLE = 0.52           # four staggered rounds -> one every 0.13 s
PULSE_AT = 19.1             # synchronised "pattern revealed" beat
HOLD_UNTIL = 21.6

THEMES = {
    "dark": {
        "bg": "#06080A", "panel": "#0C1014",
        "ink": "#EAEEF1", "faint": "#7D8794", "rule": "#1B222A",
        "decoy": "#212B34", "decoy_edge": "#313D48",
        "levels": ["#0f3b2a", "#166b45", "#1fa568", "#2FD98A"],
        "burst": "#FFC46B", "bullet": "#FFE9A8", "bullet_glow": "#FF9E3D",
        "star": "#93A0AE", "neb1": "#123044", "neb2": "#2A1436",
        "glow": "1",
    },
    "light": {
        "bg": "#F7F7F4", "panel": "#FFFFFF",
        "ink": "#14181C", "faint": "#5D646D", "rule": "#DEDCD5",
        "decoy": "#E3E1DA", "decoy_edge": "#CFCCC3",
        "levels": ["#c6e5d4", "#7fc4a2", "#3d9a6e", "#12784C"],
        "burst": "#D07A12", "bullet": "#C25E00", "bullet_glow": "#E89A3C",
        "star": "#B4B0A6", "neb1": "#E7EEF2", "neb2": "#F1E7F0",
        "glow": "0",
    },
}


@dataclass
class Day:
    week: int
    weekday: int
    level: int
    date: str


def fetch(user: str) -> tuple[list[Day], int]:
    """Scrape the public calendar. Per-day counts live in the tool-tips, not on
    the <td>, so the total and the number of active days are different numbers."""
    req = urllib.request.Request(
        CONTRIB_URL.format(user=user),
        headers={"User-Agent": "contrib-arcade/2.0 (+https://github.com/%s)" % user},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        page = r.read().decode("utf-8", "replace")

    total = 0
    for tip in re.findall(r"<tool-tip[^>]*>([^<]*)</tool-tip>", page):
        m = re.match(r"\s*([\d,]+)\s+contribution", tip)
        if m:
            total += int(m.group(1).replace(",", ""))
    if not total:
        m = re.search(r">\s*([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", page)
        total = int(m.group(1).replace(",", "")) if m else 0

    days: list[Day] = []
    for td in re.findall(r"<td[^>]*class=\"ContributionCalendar-day\"[^>]*>", page):
        d = re.search(r'data-date="([\d-]+)"', td)
        lv = re.search(r'data-level="(\d)"', td)
        idn = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', td)
        if d and lv and idn:
            days.append(Day(int(idn.group(2)), int(idn.group(1)),
                            int(lv.group(1)), d.group(1)))
    if not days:
        raise SystemExit("no contribution cells parsed; GitHub markup changed?")
    return days, total


def pct(t: float) -> float:
    return max(0.0, min(100.0, t / LOOP * 100.0))


def month_marks(days: list[Day]) -> list[tuple[int, str]]:
    """First week of each month, for the labels along the top."""
    first: dict[int, str] = {}
    for d in sorted(days, key=lambda x: x.date):
        first.setdefault(d.week, d.date)
    marks, seen = [], None
    for w in sorted(first):
        mon = int(first[w][5:7])
        if mon != seen and w < 51:
            marks.append((w, calendar.month_abbr[mon]))
            seen = mon
    return marks


def build(days: list[Day], theme: str, user: str, total: int, active: int) -> str:
    t = THEMES[theme]
    weeks = max(d.week for d in days) + 1
    grid_w = weeks * PITCH - GAP
    grid_h = DAYS * PITCH - GAP
    # every panel on the page is 880 wide; centre the grid inside that
    W = 880
    H = GRID_TOP + grid_h + FOOT
    x0 = max(PAD_L, (W - grid_w) / 2)
    y0 = GRID_TOP
    rng = random.Random(20260814)

    o: list[str] = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" role="img" aria-label="Contribution calendar for '
      f'@{html.escape(user)} rendered as an arcade shooter: a rocket destroys the '
      f'empty days, leaving the real contribution pattern">')

    # ── gradients ─────────────────────────────────────────────────────────
    a("<defs>")
    # top-down craft: light falls across the hull, so the gradients run in x
    a('<linearGradient id="hull" x1="0" y1="0" x2="1" y2="0">'
      '<stop offset="0" stop-color="#77828F"/><stop offset=".42" stop-color="#F1F4F7"/>'
      '<stop offset=".62" stop-color="#C6CDD6"/><stop offset="1" stop-color="#7A8592"/>'
      '</linearGradient>')
    a('<linearGradient id="wing" x1="0" y1="0" x2="1" y2="0">'
      '<stop offset="0" stop-color="#68727F"/><stop offset=".5" stop-color="#C9D0D9"/>'
      '<stop offset="1" stop-color="#727D8A"/></linearGradient>')
    a('<linearGradient id="nose" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="#FF8A6B"/><stop offset=".45" stop-color="#F2453D"/>'
      '<stop offset="1" stop-color="#B81F28"/></linearGradient>')
    a('<linearGradient id="finq" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="#F2453D"/><stop offset="1" stop-color="#96131F"/>'
      '</linearGradient>')
    a('<radialGradient id="glass" cx=".36" cy=".32" r=".8">'
      '<stop offset="0" stop-color="#DFF6FF"/><stop offset=".45" stop-color="#5FC8F0"/>'
      '<stop offset="1" stop-color="#12556F"/></radialGradient>')
    a(f'<radialGradient id="neb" cx=".5" cy=".5" r=".5">'
      f'<stop offset="0" stop-color="{t["neb1"]}" stop-opacity=".85"/>'
      f'<stop offset="1" stop-color="{t["neb1"]}" stop-opacity="0"/></radialGradient>')
    a(f'<radialGradient id="neb2" cx=".5" cy=".5" r=".5">'
      f'<stop offset="0" stop-color="{t["neb2"]}" stop-opacity=".8"/>'
      f'<stop offset="1" stop-color="{t["neb2"]}" stop-opacity="0"/></radialGradient>')
    a("</defs>")

    # ── styles ────────────────────────────────────────────────────────────
    css: list[str] = [
        ".bg{fill:%s}" % t["bg"],
        ".star{fill:%s}" % t["star"],
        ".dc{fill:%s;stroke:%s;stroke-width:.5}" % (t["decoy"], t["decoy_edge"]),
        ".cell{rx:2.4;ry:2.4}",
        ".nm{font:700 15px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;fill:%s;letter-spacing:.04em}" % t["ink"],
        ".hd{font:500 9px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;fill:%s;letter-spacing:.16em}" % t["faint"],
        ".mo{font:500 8px ui-monospace,Menlo,Consolas,monospace;fill:%s;letter-spacing:.08em}" % t["faint"],
        ".wd{font:500 7.5px ui-monospace,Menlo,Consolas,monospace;fill:%s}" % t["faint"],
        ".ft{font:500 8.5px ui-monospace,Menlo,Consolas,monospace;fill:%s;letter-spacing:.14em}" % t["faint"],
        ".ex{fill:none;stroke:%s;stroke-width:1.05}" % t["burst"],
    ]
    for i, c in enumerate(t["levels"]):
        css.append(".l%d{fill:%s}" % (i + 1, c))

    # rocket sweep
    fly_in = x0 - 74
    fly_out = x0 + grid_w + 74
    css.append(
        "@keyframes fly{0%%,%.3f%%{transform:translateX(%.1fpx)}"
        "%.3f%%{transform:translateX(%.1fpx)}"
        "%.3f%%,100%%{transform:translateX(%.1fpx)}}"
        % (pct(SWEEP_START - 1.3), fly_in, pct(SWEEP_END + 1.3), fly_out,
           pct(HOLD_UNTIL), fly_out)
    )
    css.append(".ship{animation:fly %.1fs linear infinite}" % LOOP)
    css.append("@keyframes bob{0%,100%{transform:translateY(-1.6px)}"
               "50%{transform:translateY(1.6px)}}")
    css.append(".bob{animation:bob 2.6s ease-in-out infinite}")

    # thruster plumes: three layers, mismatched periods so it reads as flicker.
    # They fire upward from the nozzles, so the origin is the bottom of each.
    for i, (dur, sc) in enumerate(((0.13, 0.52), (0.19, 0.62), (0.27, 0.72))):
        css.append("@keyframes fl%d{0%%,100%%{transform:scaleY(1);opacity:.95}"
                   "50%%{transform:scaleY(%.2f);opacity:.6}}" % (i, sc))
        css.append(".fl%d{animation:fl%d %.2fs ease-in-out infinite;"
                   "transform-box:fill-box;transform-origin:50%% 100%%}" % (i, i, dur))

    # bullets
    travel = (y0 + grid_h + 10) - (LANE_Y + 9)
    css.append("@keyframes shot{0%%{transform:translateY(0);opacity:0}"
               "7%%{opacity:1}70%%{opacity:1}"
               "100%%{transform:translateY(%.0fpx);opacity:0}}" % travel)
    css.append(".bl{animation:shot %.3fs linear infinite}" % SHOT_CYCLE)
    for i in range(1, 4):
        css.append(".bl%d{animation-delay:-%.3fs}" % (i, SHOT_CYCLE * i / 4))
    css.append("@keyframes mz{0%,100%{opacity:0;transform:scale(.5)}"
               "18%{opacity:1;transform:scale(1)}}")
    # transform-box must be fill-box: on SVG elements transform-origin resolves
    # against the viewBox by default, which throws the flash across the canvas
    css.append(".mz{animation:mz %.3fs linear infinite;"
               "transform-box:fill-box;transform-origin:center}" % (SHOT_CYCLE / 4))
    css.append("@keyframes tw{0%,100%{opacity:.14}50%{opacity:.7}}")

    # progress bar tracks the sweep
    css.append("@keyframes pg{0%%,%.3f%%{transform:scaleX(0)}"
               "%.3f%%,100%%{transform:scaleX(1)}}"
               % (pct(SWEEP_START), pct(SWEEP_END)))
    css.append(".pg{animation:pg %.1fs linear infinite;"
               "transform-box:fill-box;transform-origin:left center}" % LOOP)
    css.append("@keyframes rv{0%%,%.3f%%{opacity:0}%.3f%%,%.3f%%{opacity:1}"
               "%.3f%%,100%%{opacity:0}}"
               % (pct(SWEEP_END + 0.4), pct(SWEEP_END + 1.1),
                  pct(HOLD_UNTIL - 0.4), pct(HOLD_UNTIL)))
    css.append(".rv{animation:rv %.1fs linear infinite}" % LOOP)

    # per-column destroy / reveal / burst
    step = (SWEEP_END - SWEEP_START) / max(1, weeks - 1)
    for w in range(weeks):
        hit = SWEEP_START + w * step + BULLET_LAG
        h0, h1, h2 = pct(hit - 0.05), pct(hit + 0.05), pct(hit + 0.26)
        end = pct(HOLD_UNTIL)
        # decoy: brief flare, then blown apart
        css.append(
            "@keyframes k%d{0%%,%.3f%%{opacity:1;transform:scale(1)}"
            "%.3f%%{opacity:1;transform:scale(1.5)}"
            "%.3f%%,%.3f%%{opacity:0;transform:scale(.1)}"
            "100%%{opacity:1;transform:scale(1)}}" % (w, h0, h1, h2, end)
        )
        css.append(".k%d{animation:k%d %.1fs linear infinite;"
                   "transform-box:fill-box;transform-origin:center}" % (w, w, LOOP))
        # burst ring
        css.append(
            "@keyframes e%d{0%%,%.3f%%{opacity:0;transform:scale(.25)}"
            "%.3f%%{opacity:.9;transform:scale(.55)}"
            "%.3f%%,100%%{opacity:0;transform:scale(1.5)}}" % (w, h0, h1, h2)
        )
        css.append(".e%d{animation:e%d %.1fs ease-out infinite;"
                   "transform-box:fill-box;transform-origin:center}" % (w, w, LOOP))
        # survivor: lights up, then joins the closing pulse
        pa, pb, pc = pct(PULSE_AT), pct(PULSE_AT + 0.22), pct(PULSE_AT + 0.55)
        css.append(
            "@keyframes r%d{0%%,%.3f%%{opacity:.26;transform:scale(1)}"
            "%.3f%%{opacity:1;transform:scale(1.28)}"
            "%.3f%%{opacity:1;transform:scale(1)}"
            "%.3f%%{opacity:1;transform:scale(1)}"
            "%.3f%%{opacity:1;transform:scale(1.34)}"
            "%.3f%%,%.3f%%{opacity:1;transform:scale(1)}"
            "100%%{opacity:.26;transform:scale(1)}}"
            % (w, h0, h1, pct(hit + 0.34), pa, pb, pc, end)
        )
        css.append(".r%d{animation:r%d %.1fs ease-out infinite;"
                   "transform-box:fill-box;transform-origin:center}" % (w, w, LOOP))

    css.append("@media (prefers-reduced-motion:reduce){"
               "*{animation:none!important}.dc,.ex{opacity:0}}")
    a("<style>%s</style>" % "".join(css))

    # ── backdrop, in the same card shell as every other panel ─────────────
    a(f'<defs><clipPath id="cardclip">'
      f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17"/></clipPath>'
      f'<linearGradient id="edgeg" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{t["levels"][3]}" stop-opacity=".5"/>'
      f'<stop offset=".5" stop-color="{t["rule"]}" stop-opacity=".9"/>'
      f'<stop offset="1" stop-color="#E455C0" stop-opacity=".45"/></linearGradient></defs>')
    a(f'<rect class="bg" width="{W}" height="{H}" rx="18"/>')
    a('<g clip-path="url(#cardclip)">')
    a(f'<ellipse cx="{W*.22:.0f}" cy="{H*.34:.0f}" rx="230" ry="150" fill="url(#neb)"/>')
    a(f'<ellipse cx="{W*.78:.0f}" cy="{H*.62:.0f}" rx="250" ry="160" fill="url(#neb2)"/>')
    for _ in range(96):
        sx, sy = rng.uniform(0, W), rng.uniform(0, H)
        a(f'<circle class="star" cx="{sx:.1f}" cy="{sy:.1f}" '
          f'r="{rng.choice([.5,.6,.8,1.0]):.1f}" style="animation:tw '
          f'{rng.uniform(1.9,4.8):.2f}s ease-in-out {rng.uniform(0,4):.2f}s infinite"/>')
    a("</g>")
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" '
      f'stroke="url(#edgeg)" stroke-width="1.4"/>')

    # ── HUD ───────────────────────────────────────────────────────────────
    a(f'<text class="nm" x="{x0}" y="30">@{html.escape(user)}</text>')
    a(f'<text class="hd" x="{x0}" y="47">{total} CONTRIBUTIONS &#183; '
      f'{len(days) - active} DECOYS</text>')
    # bar runs the full width of the grid, so it reads as the sweep's position;
    # the completion flash moves up onto the HUD line, right-aligned
    bar_w = grid_w
    a(f'<rect x="{x0}" y="57" width="{bar_w:.0f}" height="3" rx="1.5" '
      f'fill="{t["rule"]}"/>')
    a(f'<rect class="pg" x="{x0}" y="57" width="{bar_w:.0f}" height="3" rx="1.5" '
      f'fill="{t["levels"][3]}"/>')
    a(f'<text class="ft rv" x="{x0 + grid_w:.0f}" y="47" text-anchor="end" '
      f'fill="{t["levels"][3]}">PATTERN REVEALED</text>')

    # month + weekday labels
    for w, name in month_marks(days):
        a(f'<text class="mo" x="{x0 + w * PITCH:.0f}" y="{y0 - 8}">{name}</text>')
    for wd, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        a(f'<text class="wd" x="{x0 - 8}" y="{y0 + wd * PITCH + 8.4:.0f}" '
          f'text-anchor="end">{name}</text>')

    # ── grid ──────────────────────────────────────────────────────────────
    a("<g>")
    for d in days:
        x = x0 + d.week * PITCH
        y = y0 + d.weekday * PITCH
        if d.level == 0:
            a(f'<circle class="ex e{d.week}" cx="{x + CELL/2:.1f}" '
              f'cy="{y + CELL/2:.1f}" r="{CELL*.40:.1f}" opacity="0"/>')
            a(f'<rect class="cell dc k{d.week}" x="{x}" y="{y}" width="{CELL}" '
              f'height="{CELL}"><title>{d.date}: no contributions</title></rect>')
        else:
            a(f'<rect class="cell l{d.level} r{d.week}" x="{x}" y="{y}" '
              f'width="{CELL}" height="{CELL}">'
              f'<title>{d.date}: level {d.level}</title></rect>')
    a("</g>")

    # ── fighter: top-down, nose pointing at the grid ──────────────────────
    # Local frame: origin on the ship's centre, +y is down, which is forward.
    # It strafes left to right, thrusters firing back up the way it came.
    gun_y = LANE_Y + 5.4          # muzzle sits at the end of the cannon barrel
    a('<g class="ship">')
    # twin cannon fire, one stream per wing root
    for gx in (-6.2, 6.2):
        for i in range(4):
            cls = "bl" if i == 0 else f"bl bl{i}"
            a(f'<g class="{cls}">'
              f'<rect x="{gx-1.7:.1f}" y="{gun_y:.1f}" width="3.4" height="12" rx="1.7" '
              f'fill="{t["bullet_glow"]}" opacity=".34"/>'
              f'<rect x="{gx-0.7:.1f}" y="{gun_y+1:.1f}" width="1.4" height="9" rx=".7" '
              f'fill="{t["bullet"]}"/></g>')
        a(f'<ellipse class="mz" cx="{gx:.1f}" cy="{gun_y:.1f}" rx="3.4" ry="2.2" '
          f'fill="{t["bullet"]}" opacity="0"/>')

    a('<g class="bob">')
    # thruster plumes, firing up out of the twin nozzles
    for nx in (-3.6, 3.6):
        a(f'<path class="fl2" d="M{nx-2.0:.1f} {LANE_Y-11.4:.1f} '
          f'Q{nx:.1f} {LANE_Y-29:.1f} {nx+2.0:.1f} {LANE_Y-11.4:.1f} Z" '
          f'fill="#FF6A1F" opacity=".62"/>')
        a(f'<path class="fl1" d="M{nx-1.4:.1f} {LANE_Y-11.4:.1f} '
          f'Q{nx:.1f} {LANE_Y-22:.1f} {nx+1.4:.1f} {LANE_Y-11.4:.1f} Z" fill="#FFC24A"/>')
        a(f'<path class="fl0" d="M{nx-0.8:.1f} {LANE_Y-11.4:.1f} '
          f'Q{nx:.1f} {LANE_Y-16.6:.1f} {nx+0.8:.1f} {LANE_Y-11.4:.1f} Z" fill="#FFF3C4"/>')
    # swept wings
    for s in (-1, 1):
        a(f'<path d="M{s*3.0:.1f} {LANE_Y+2:.1f} L{s*13.5:.1f} {LANE_Y-5.5:.1f} '
          f'L{s*12.0:.1f} {LANE_Y-9.2:.1f} L{s*2.8:.1f} {LANE_Y-5:.1f} Z" '
          f'fill="url(#wing)"/>')
        a(f'<path d="M{s*3.0:.1f} {LANE_Y+2:.1f} L{s*13.5:.1f} {LANE_Y-5.5:.1f}" '
          f'stroke="#E03A3A" stroke-width="1.5" stroke-linecap="round" opacity=".9"/>')
        # tail fin
        a(f'<path d="M{s*2.6:.1f} {LANE_Y-8:.1f} L{s*6.0:.1f} {LANE_Y-13.5:.1f} '
          f'L{s*1.4:.1f} {LANE_Y-9.5:.1f} Z" fill="url(#finq)"/>')
        # engine nacelle
        a(f'<rect x="{s*3.6-2.1:.1f}" y="{LANE_Y-11.6:.1f}" width="4.2" height="5.2" '
          f'rx="1.6" fill="#6E7885"/>')
        # wing-root cannon: short and tucked under the wing, not a landing leg
        a(f'<rect x="{s*6.2-0.75:.1f}" y="{LANE_Y-2.4:.1f}" width="1.5" height="7.4" '
          f'rx=".75" fill="#59636F"/>')
        a(f'<rect x="{s*6.2-1.5:.1f}" y="{LANE_Y-3.4:.1f}" width="3.0" height="2.4" '
          f'rx="1.0" fill="#7C8794"/>')
    # hull
    a(f'<path d="M0 {LANE_Y+15:.1f} L3.4 {LANE_Y+2:.1f} L3.1 {LANE_Y-8.6:.1f} '
      f'L-3.1 {LANE_Y-8.6:.1f} L-3.4 {LANE_Y+2:.1f} Z" fill="url(#hull)"/>')
    # nose tip
    a(f'<path d="M0 {LANE_Y+15:.1f} L2.3 {LANE_Y+5.2:.1f} L-2.3 {LANE_Y+5.2:.1f} Z" '
      f'fill="url(#nose)"/>')
    # spine highlight
    a(f'<path d="M0 {LANE_Y+11:.1f} L0 {LANE_Y-7:.1f}" stroke="#FFFFFF" '
      f'stroke-width="1.1" stroke-linecap="round" opacity=".38"/>')
    # canopy
    a(f'<ellipse cx="0" cy="{LANE_Y-1.6:.1f}" rx="2.9" ry="4.4" fill="#5F6B78"/>')
    a(f'<ellipse cx="0" cy="{LANE_Y-1.6:.1f}" rx="2.1" ry="3.6" fill="url(#glass)"/>')
    a(f'<ellipse cx="-0.7" cy="{LANE_Y-2.9:.1f}" rx=".8" ry="1.3" fill="#FFFFFF" '
      f'opacity=".75"/>')
    a("</g></g>")

    a("</svg>")
    return "".join(o)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out-dark", default="dist/shooter-dark.svg")
    ap.add_argument("--out-light", default="dist/shooter-light.svg")
    args = ap.parse_args()

    days, total = fetch(args.user)
    active = sum(1 for d in days if d.level > 0)
    weeks = max(d.week for d in days) + 1
    print(f"{len(days)} days over {weeks} weeks")
    print(f"{total} contributions across {active} active days; "
          f"{len(days) - active} decoys to clear")
    print(f"sweep {SWEEP_START}s -> {SWEEP_END}s "
          f"({(SWEEP_END-SWEEP_START)/weeks:.3f}s per column)")

    for path, theme in ((args.out_dark, "dark"), (args.out_light, "light")):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        svg = build(days, theme, args.user, total, active)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {path}  ({len(svg.encode('utf-8')) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
