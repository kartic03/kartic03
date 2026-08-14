#!/usr/bin/env python3
"""
A de novo designed three-helix bundle, animated through its whole design and
delivery pipeline as a rotating 3D SVG.

Each stage looks different, because each stage does something different:

  RFdiffusion  a noise cloud condenses into a bare backbone, drawn colourless
  ProteinMPNN  the chain takes its sequence and gains N-to-C spectrum colour
  AlphaFold    the fold is validated: a pLDDT strip fills and the surface
               picks up specular sheen
  transit      the bundle tilts to lie along its long axis, because that is
               how a helical peptide threads a bilayer, and a pore dilates
  delivery     it arrives in neural tissue and the neurons and astrocytes
               light up as it reaches them

Geometry is real: helix radius 2.3 A, rise 1.5 A/residue, 100 deg/residue,
three antiparallel helices at 10 A axis-to-axis. Rotation and tilt are baked
into SMIL path morphs; depth uses a true painter's algorithm so helices
genuinely occlude one another.

Standard library only.
"""

from __future__ import annotations

import argparse
import math
import os
import random

# ── canvas ────────────────────────────────────────────────────────────────
W, H = 1040, 384
CX, CY = 130.0, 172.0
TRAVEL = 700.0
FOCAL = 640.0
LOOP = 28.0

# ── molecular geometry (angstrom -> px) ───────────────────────────────────
A = 6.0
R_HELIX = 2.3 * A
RISE = 1.5 * A
DPHI = math.radians(100.0)
R_BUNDLE = 5.8 * A          # 10 A axis-to-axis
NRES = 18
SAMP = 3
FRAMES = 28
SLOTS = 5

# ── membrane ──────────────────────────────────────────────────────────────
MEM_X = 500.0
LEAFLET = 19.0
N_LIPID = 19
MEM_HALF = 112.0
PORE_MAX = 40.0
PORE_SIGMA = 46.0

# ── timeline (fractions of LOOP) ──────────────────────────────────────────
T_FADE_IN = 0.048
T_TRAVEL0, T_TRAVEL1 = 0.050, 0.900
T_DENOISE = 0.130
T_SEQ = 0.260               # sequence assigned: colour arrives
T_FOLD = 0.380              # validated: sheen + pLDDT
T_TILT0, T_TILT1 = 0.400, 0.470
T_ROT_END = 0.880
T_FADE_OUT = 0.948
T_RESET = 0.965

T_MEM = T_TRAVEL0 + (T_TRAVEL1 - T_TRAVEL0) * (MEM_X - CX) / TRAVEL
PORE_OPEN0, PORE_OPEN1 = T_MEM - 0.055, T_MEM - 0.018
PORE_SHUT0, PORE_SHUT1 = T_MEM + 0.024, T_MEM + 0.075

NEURO_X0, NEURO_X1 = 566.0, 1012.0

THEMES = {
    "dark": {
        "bg": "#07090B", "ink": "#EAEEF1", "faint": "#808892", "rule": "#1D242B",
        "outline": "#07090B", "sheen": "#FFFFFF", "bare": "#4A5560",
        "head": "#4C93B8", "tail": "#2B3A46", "core": "#121A21",
        "neuron": "#2FD98A", "astro": "#57ABBE", "glow": "#2FD98A",
        "chain": ["#E455C0", "#C264D4", "#8E77E0", "#57ABBE", "#2FD98A"],
    },
    "light": {
        "bg": "#FAF9F6", "ink": "#14181C", "faint": "#636A73", "rule": "#DFDDD6",
        "outline": "#FAF9F6", "sheen": "#FFFFFF", "bare": "#A9A69E",
        "head": "#6E9FB8", "tail": "#C4BFB4", "core": "#EFEDE7",
        "neuron": "#0F6E44", "astro": "#2F7E86", "glow": "#2FA372",
        "chain": ["#A81E8C", "#8E3AA8", "#6B4A9E", "#2F7E86", "#0F6E44"],
    },
}

STAGES = [
    ("RFdiffusion", "backbone", 0.13, 145),
    ("ProteinMPNN", "sequence", T_SEQ, 275),
    ("AlphaFold / Boltz-2", "fold", T_FOLD, 380),
    ("blood-brain barrier", "transit", None, 515),
    ("neurons + astrocytes", "delivery", 0.72, 790),
]

SEQ = "SLKEIAKELWKRAEELLKKAQELLKKGNPELAAKVLEIAKRLWEEAKKLLDEAQRLLKSGT"


# ── molecule geometry ─────────────────────────────────────────────────────
def helix(idx: int, up: bool):
    ax = R_BUNDLE * math.cos(math.radians(120.0 * idx))
    az = R_BUNDLE * math.sin(math.radians(120.0 * idx))
    span = (NRES - 1) * RISE
    n = (NRES - 1) * SAMP + 1
    pts = []
    for s in range(n):
        u = s / (n - 1)
        phi = u * (NRES - 1) * DPHI + math.radians(37.0 * idx)
        y = -span / 2 + u * span
        pts.append((ax + R_HELIX * math.cos(phi), y if up else -y,
                    az + R_HELIX * math.sin(phi)))
    return pts


def loop_seg(p0, p1, bulge=1.5, n=7):
    pts = []
    for i in range(n):
        u = i / (n - 1)
        x = p0[0] + (p1[0] - p0[0]) * u
        y = p0[1] + (p1[1] - p0[1]) * u
        z = p0[2] + (p1[2] - p0[2]) * u
        k = math.sin(math.pi * u)
        r = math.hypot(x, z) or 1.0
        x += (x / r) * (bulge - 1.0) * R_BUNDLE * k
        z += (z / r) * (bulge - 1.0) * R_BUNDLE * k
        y += k * 10.0 * (1 if p0[1] > 0 else -1)
        pts.append((x, y, z))
    return pts


def build_segments():
    h0, h1, h2 = helix(0, True), helix(1, False), helix(2, True)
    return [("h", h0), ("l", loop_seg(h0[-1], h1[0])), ("h", h1),
            ("l", loop_seg(h1[-1], h2[0])), ("h", h2)]


def rot_y(p, th):
    x, y, z = p
    c, s = math.cos(th), math.sin(th)
    return (x * c + z * s, y, -x * s + z * c)


def rot_z(p, th):
    """Tilt the whole bundle. Applied after the spin, so the spin stays about
    the bundle's own long axis whatever the tilt."""
    x, y, z = p
    c, s = math.cos(th), math.sin(th)
    return (x * c - y * s, x * s + y * c, z)


def project(p):
    x, y, z = p
    s = FOCAL / (FOCAL - z)
    return (CX + x * s, CY + y * s)


def to_d(pts3):
    return "".join(("M" if i == 0 else "L") + "%.1f %.1f" % project(q)
                   for i, q in enumerate(pts3))


def cloud(pts3, rng):
    out = []
    for (x, y, z) in pts3:
        k = rng.uniform(1.9, 3.3)
        out.append((x * k + rng.uniform(-24, 24), y * 1.15 + rng.uniform(-28, 28),
                    z * k + rng.uniform(-24, 24)))
    return out


def tilt_at(t: float) -> float:
    if t <= T_TILT0:
        return 0.0
    if t >= T_TILT1:
        return math.pi / 2
    u = (t - T_TILT0) / (T_TILT1 - T_TILT0)
    u = u * u * (3 - 2 * u)                    # smoothstep
    return u * math.pi / 2


# ── neural tissue ─────────────────────────────────────────────────────────
def branch(paths, x, y, ang, length, depth, rng, spread=0.62):
    if depth == 0 or length < 5:
        return
    x2 = x + math.cos(ang) * length
    y2 = y + math.sin(ang) * length
    mx = x + math.cos(ang + rng.uniform(-.3, .3)) * length * 0.55
    my = y + math.sin(ang + rng.uniform(-.3, .3)) * length * 0.55
    paths.append(f"M{x:.1f} {y:.1f}Q{mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}")
    for k in (-1, 1):
        branch(paths, x2, y2, ang + k * rng.uniform(.28, spread),
               length * rng.uniform(.55, .72), depth - 1, rng, spread)


def neuron(cx, cy, rng):
    paths = []
    n = rng.randint(5, 6)
    for i in range(n):
        ang = 2 * math.pi * i / n + rng.uniform(-.3, .3)
        branch(paths, cx, cy, ang, rng.uniform(20, 30), 3, rng)
    ax = rng.choice([-1, 1])
    branch(paths, cx, cy, (0 if ax > 0 else math.pi) + rng.uniform(-.2, .2),
           rng.uniform(52, 74), 2, rng, spread=.3)
    return paths, 6.2


def astrocyte(cx, cy, rng):
    paths = []
    n = rng.randint(9, 12)
    for i in range(n):
        ang = 2 * math.pi * i / n + rng.uniform(-.22, .22)
        branch(paths, cx, cy, ang, rng.uniform(13, 20), 2, rng, spread=.85)
    return paths, 4.2


def fmt(ts):
    return ";".join(("%.4f" % t).rstrip("0").rstrip(".") or "0" for t in ts)


def p(x):
    return x * 100.0


# ── svg ───────────────────────────────────────────────────────────────────
def build(theme_name: str, user: str) -> str:
    t = THEMES[theme_name]
    rng = random.Random(90210)
    segs = build_segments()

    frame_t = [T_DENOISE + (T_ROT_END - T_DENOISE) * k / FRAMES
               for k in range(FRAMES + 1)]
    frames, ranks = [], []
    for k, tk in enumerate(frame_t):
        th = 2 * math.pi * k / FRAMES
        ph = tilt_at(tk)
        rot = [[rot_z(rot_y(q, th), ph) for q in pts] for _, pts in segs]
        frames.append(rot)
        order = [i for _, i in sorted(
            (sum(q[2] for q in pts) / len(pts), i) for i, pts in enumerate(rot))]
        rk = [0] * len(segs)
        for slot, i in enumerate(order):
            rk[i] = slot
        ranks.append(rk)

    clouds = [cloud(pts, rng) for _, pts in segs]
    times = [0.0, T_FADE_IN * 0.6] + frame_t + [T_FADE_OUT, T_RESET, 1.0]

    o: list[str] = []
    a = o.append
    # native coords stay 1040 wide; the panel renders at the page's 880 so it
    # lines up with everything else
    OUT_W = 880
    OUT_H = round(H * OUT_W / W)
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{OUT_W}" height="{OUT_H}" '
      f'viewBox="0 0 {W} {H}" role="img" aria-label="A de novo designed three-helix '
      f'bundle is generated from noise, given a sequence, folded, tilted to cross a '
      f'lipid bilayer through a transient pore, and delivered into glowing neural tissue">')

    css = [
        ".bg{fill:%s}" % t["bg"],
        ".t1{font:600 15px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;fill:%s;letter-spacing:.05em}" % t["ink"],
        ".t2{font:400 10px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;fill:%s;letter-spacing:.12em}" % t["faint"],
        ".sq{font:500 7.4px ui-monospace,Menlo,Consolas,monospace;fill:%s;letter-spacing:.33em}" % t["faint"],
        ".lb{font:400 7.5px ui-monospace,Menlo,Consolas,monospace;fill:%s;letter-spacing:.14em}" % t["faint"],
        ".st{font:500 8.8px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;letter-spacing:.1em}",
        ".sb{font:400 8.5px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;fill:%s;letter-spacing:.07em}" % t["faint"],
        ".rail{stroke:%s;stroke-width:1;fill:none}" % t["rule"],
    ]
    css.append("@keyframes mv{0%%,%.1f%%{transform:translateX(0)}"
               "%.1f%%,%.1f%%{transform:translateX(%.0fpx)}"
               "%.2f%%,100%%{transform:translateX(0)}}"
               % (p(T_TRAVEL0), p(T_TRAVEL1), p(T_RESET), TRAVEL, p(T_RESET) + 0.2))
    css.append("@keyframes fade{0%%{opacity:0}%.1f%%{opacity:1}"
               "%.1f%%{opacity:1}%.1f%%,100%%{opacity:0}}"
               % (p(T_FADE_IN), p(T_ROT_END), p(T_FADE_OUT)))
    css.append(".mol{animation:mv %.1fs linear infinite}" % LOOP)
    css.append(".molf{animation:fade %.1fs linear infinite}" % LOOP)

    # ProteinMPNN: bare backbone takes its sequence colour
    for si in range(len(segs)):
        css.append("@keyframes cl%d{0%%,%.1f%%{stroke:%s}%.1f%%,100%%{stroke:%s}}"
                   % (si, p(T_SEQ), t["bare"], p(T_SEQ + 0.055), t["chain"][si]))
        css.append(".cl%d{animation:cl%d %.1fs linear infinite}" % (si, si, LOOP))
    # AlphaFold: validated surface picks up sheen
    css.append("@keyframes shn{0%%,%.1f%%{opacity:0}%.1f%%,100%%{opacity:1}}"
               % (p(T_FOLD), p(T_FOLD + 0.05)))
    css.append(".shn{animation:shn %.1fs linear infinite}" % LOOP)
    # pLDDT strip
    css.append("@keyframes plf{0%%,%.1f%%{transform:scaleY(0)}%.1f%%,100%%{transform:scaleY(1)}}"
               % (p(T_FOLD), p(T_FOLD + 0.07)))
    css.append("@keyframes plo{0%%,%.1f%%{opacity:0}%.1f%%,%.1f%%{opacity:1}%.1f%%,100%%{opacity:0}}"
               % (p(T_FOLD - 0.01), p(T_FOLD + 0.06), p(T_FOLD + 0.30), p(T_FOLD + 0.38)))
    css.append(".plo{animation:plo %.1fs linear infinite}" % LOOP)

    rows = []
    for i in range(N_LIPID):
        dy = (i - (N_LIPID - 1) / 2) * (2 * MEM_HALF / (N_LIPID - 1))
        shift = math.copysign(PORE_MAX * math.exp(-(dy / PORE_SIGMA) ** 2), dy or 1.0)
        rows.append((dy, shift))
        css.append("@keyframes po%d{0%%,%.1f%%{transform:translateY(0)}"
                   "%.1f%%,%.1f%%{transform:translateY(%.1fpx)}"
                   "%.1f%%,100%%{transform:translateY(0)}}"
                   % (i, p(PORE_OPEN0), p(PORE_OPEN1), p(PORE_SHUT0), shift, p(PORE_SHUT1)))
        css.append(".po%d{animation:po%d %.1fs cubic-bezier(.4,0,.25,1) infinite}"
                   % (i, i, LOOP))
    for sgn, nm in ((-1, "u"), (1, "d")):
        css.append("@keyframes co%s{0%%,%.1f%%{transform:translateY(0)}"
                   "%.1f%%,%.1f%%{transform:translateY(%.1fpx)}"
                   "%.1f%%,100%%{transform:translateY(0)}}"
                   % (nm, p(PORE_OPEN0), p(PORE_OPEN1), p(PORE_SHUT0),
                      sgn * PORE_MAX * 0.9, p(PORE_SHUT1)))
        css.append(".co%s{animation:co%s %.1fs cubic-bezier(.4,0,.25,1) infinite}"
                   % (nm, nm, LOOP))

    css.append("@keyframes wr{0%,15%{width:0}30%,100%{width:420px}}")
    css.append(".wr{animation:wr %.1fs linear infinite}" % LOOP)

    stage_t = [s[2] if s[2] is not None else T_MEM for s in STAGES]
    for i, ts in enumerate(stage_t):
        css.append("@keyframes s%d{0%%,%.1f%%{fill:%s}%.1f%%{fill:%s}%.1f%%,100%%{fill:%s}}"
                   % (i, p(ts - 0.02), t["faint"], p(ts + 0.015),
                      t["neuron"] if i >= 3 else t["chain"][0], p(ts + 0.14), t["faint"]))
        css.append(".s%d{animation:s%d %.1fs linear infinite}" % (i, i, LOOP))
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    a("<style>%s</style>" % "".join(css))
    a(f'<defs><clipPath id="cardclip">'
      f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="20"/></clipPath>'
      f'<linearGradient id="edgeg" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{t["chain"][0]}" stop-opacity=".5"/>'
      f'<stop offset=".5" stop-color="{t["rule"]}" stop-opacity=".9"/>'
      f'<stop offset="1" stop-color="{t["chain"][-1]}" stop-opacity=".5"/>'
      f'</linearGradient></defs>')
    a(f'<rect class="bg" width="{W}" height="{H}" rx="21"/>')
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="20" fill="none" '
      f'stroke="url(#edgeg)" stroke-width="1.6"/>')

    # ── defs ──────────────────────────────────────────────────────────────
    a("<defs>")
    for si, (_, pts) in enumerate(segs):
        vals = [to_d(clouds[si]), to_d(clouds[si])]
        vals += [to_d(frames[k][si]) for k in range(FRAMES + 1)]
        vals += [to_d(frames[FRAMES][si]), to_d(clouds[si]), to_d(clouds[si])]
        a(f'<path id="g{si}" fill="none" d="{vals[0]}">'
          f'<animate attributeName="d" dur="{LOOP}s" repeatCount="indefinite" '
          f'calcMode="linear" keyTimes="{fmt(times)}" values="{";".join(vals)}"/></path>')
    a(f'<g id="lipid">'
      f'<path d="M4 0 q7 -2.5 14 -1.5" fill="none" stroke="{t["tail"]}" stroke-width="1.5" stroke-linecap="round"/>'
      f'<path d="M4 0 q7 2.5 14 1.5" fill="none" stroke="{t["tail"]}" stroke-width="1.5" stroke-linecap="round"/>'
      f'<circle r="3.5" fill="{t["head"]}"/>'
      f'<circle r="1.3" cx="-.9" cy="-.9" fill="{t["sheen"]}" opacity=".28"/></g>')
    a('<clipPath id="wrclip"><rect class="wr" x="40" y="60" width="0" height="16"/></clipPath>')
    a("</defs>")

    # ── neural tissue, drawn behind everything on the right ───────────────
    cells = []
    spots = [(612, 108), (700, 232), (790, 96), (700, 150), (886, 214),
             (960, 118), (838, 300), (612, 296), (930, 264)]
    for i, (nx, ny) in enumerate(spots):
        is_neuron = i % 3 != 2
        paths, r = (neuron(nx, ny, rng) if is_neuron else astrocyte(nx, ny, rng))
        cells.append((nx, ny, paths, r, is_neuron))

    for i, (nx, ny, paths, r, is_neuron) in enumerate(cells):
        # each cell lights as the peptide draws level with it
        arrive = T_TRAVEL0 + (T_TRAVEL1 - T_TRAVEL0) * (nx - 42 - CX) / TRAVEL
        arrive = max(T_MEM + 0.01, min(0.90, arrive))
        css_name = f"gl{i}"
        css.append("@keyframes %s{0%%,%.1f%%{opacity:.10}%.1f%%{opacity:1}"
                   "%.1f%%,100%%{opacity:.16}}"
                   % (css_name, p(arrive - 0.03), p(arrive + 0.03), p(min(0.94, arrive + 0.26))))
        col = t["neuron"] if is_neuron else t["astro"]
        d = "".join(paths)
        a(f'<g style="animation:{css_name} {LOOP}s ease-in-out infinite" opacity=".1">'
          f'<path d="{d}" fill="none" stroke="{col}" stroke-width="4.6" '
          f'stroke-linecap="round" opacity=".16"/>'
          f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.15" stroke-linecap="round"/>'
          f'<circle cx="{nx}" cy="{ny}" r="{r + 3.4:.1f}" fill="{col}" opacity=".17"/>'
          f'<circle cx="{nx}" cy="{ny}" r="{r:.1f}" fill="{col}"/>'
          f'<circle cx="{nx - r*.3:.1f}" cy="{ny - r*.35:.1f}" r="{r*.34:.1f}" '
          f'fill="{t["sheen"]}" opacity=".3"/></g>')
    # rebuild style block now that glow keyframes were appended
    o[1] = "<style>%s</style>" % "".join(css)

    # ── membrane ──────────────────────────────────────────────────────────
    a("<g>")
    a(f'<g class="cou"><rect x="{MEM_X-LEAFLET:.0f}" y="{CY-MEM_HALF-14:.0f}" '
      f'width="{2*LEAFLET:.0f}" height="{MEM_HALF+14:.0f}" fill="{t["core"]}"/></g>')
    a(f'<g class="cod"><rect x="{MEM_X-LEAFLET:.0f}" y="{CY:.0f}" '
      f'width="{2*LEAFLET:.0f}" height="{MEM_HALF+14:.0f}" fill="{t["core"]}"/></g>')
    for i, (dy, _) in enumerate(rows):
        y = CY + dy
        a(f'<g class="po{i}">'
          f'<use href="#lipid" transform="translate({MEM_X-LEAFLET:.1f},{y:.1f})"/>'
          f'<use href="#lipid" transform="translate({MEM_X+LEAFLET:.1f},{y:.1f}) scale(-1,1)"/></g>')
    a("</g>")

    # ── bundle ────────────────────────────────────────────────────────────
    a('<g class="molf"><g class="mol">')
    op_times = [0.0] + frame_t + [1.0]
    for slot in range(SLOTS):
        depth = slot / (SLOTS - 1)
        base_w = 12.2 * (0.74 + 0.26 * depth)
        body_o = 0.70 + 0.30 * depth
        sheen_o = 0.05 + 0.28 * depth
        a("<g>")
        for si, (kind, _) in enumerate(segs):
            w = base_w * (1.0 if kind == "h" else 0.68)
            vis = [1 if ranks[0][si] == slot else 0]
            vis += [1 if ranks[k][si] == slot else 0 for k in range(FRAMES + 1)]
            vis += [vis[-1]]
            a(f'<g opacity="{vis[0]}">'
              f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
              f'calcMode="discrete" keyTimes="{fmt(op_times)}" '
              f'values="{";".join(str(v) for v in vis)}"/>'
              f'<use href="#g{si}" stroke="{t["outline"]}" stroke-width="{w+4.4:.1f}" '
              f'stroke-linecap="round" stroke-linejoin="round"/>'
              f'<use class="cl{si}" href="#g{si}" stroke="{t["bare"]}" stroke-width="{w:.1f}" '
              f'stroke-linecap="round" stroke-linejoin="round" opacity="{body_o:.2f}"/>'
              f'<g class="shn" opacity="0"><use href="#g{si}" stroke="{t["sheen"]}" '
              f'stroke-width="{w*.28:.1f}" stroke-linecap="round" stroke-linejoin="round" '
              f'opacity="{sheen_o:.2f}" transform="translate(0,-{w*.20:.1f})"/></g></g>')
        a("</g>")
    a("</g></g>")

    # ── type + pLDDT ──────────────────────────────────────────────────────
    a('<text class="t1" x="40" y="38">de novo peptide design cascade</text>')
    a(f'<text class="t2" x="40" y="54">@{user} &#183; three-helix bundle &#183; doctoral pipeline</text>')
    a(f'<g clip-path="url(#wrclip)"><text class="sq" x="40" y="72">{SEQ}</text></g>')

    a('<g class="plo" opacity="0">')
    a(f'<text class="lb" x="40" y="94">pLDDT</text>')
    for i in range(26):
        v = 0.55 + 0.45 * math.exp(-((i - 13) / 11.0) ** 2) * rng.uniform(.86, 1.0)
        hgt = 16 * v
        bx = 80 + i * 6.4
        col = t["neuron"] if v > .84 else (t["astro"] if v > .7 else t["faint"])
        a(f'<rect x="{bx:.1f}" y="{96-hgt:.1f}" width="4" height="{hgt:.1f}" fill="{col}" '
          f'opacity=".85" style="animation:plf {LOOP}s cubic-bezier(.3,0,.2,1) infinite;'
          f'transform-origin:{bx+2:.1f}px 96px"/>')
    a("</g>")

    rail = 334
    a(f'<line class="rail" x1="40" y1="{rail}" x2="{W-40}" y2="{rail}"/>')
    for i, (name, sub, _, sx) in enumerate(STAGES):
        x = float(sx)
        a(f'<circle class="s{i}" cx="{x:.0f}" cy="{rail}" r="3" fill="{t["faint"]}"/>')
        a(f'<text class="st s{i}" x="{x:.0f}" y="{rail+20}" text-anchor="middle" '
          f'fill="{t["faint"]}">{name}</text>')
        a(f'<text class="sb" x="{x:.0f}" y="{rail+33}" text-anchor="middle">{sub}</text>')
    a("</svg>")
    return "".join(o)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="kartic03")
    ap.add_argument("--out-dark", default="dist/structure-dark.svg")
    ap.add_argument("--out-light", default="dist/structure-light.svg")
    args = ap.parse_args()
    print(f"tilt to horizontal {T_TILT0:.2f} -> {T_TILT1:.2f}")
    print(f"midplane reached at {T_MEM:.3f}; pore {PORE_OPEN0:.3f} -> reseal {PORE_SHUT1:.3f}")
    for path, theme in ((args.out_dark, "dark"), (args.out_light, "light")):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        svg = build(theme, args.user)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {path}  ({len(svg.encode('utf-8')) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
