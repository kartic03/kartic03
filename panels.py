#!/usr/bin/env python3
"""
The remaining profile panels, drawn in the same visual system as the header:
dark ground, monospace type, and the two channel colours from the CV
(magenta = computational, green = experimental).

  research   every manuscript on a five-stage publication track, filling to
             wherever it actually is
  toolchain  the two channels side by side, lighting alternately, meeting at
             a merge spine
  code       repository cards, each tied to the paper it backs
  footer     contact strip with a travelling gradient rule

Standard library only.
"""

from __future__ import annotations

import argparse
import html
import os

W = 880
STAGES = ["submitted", "under review", "revision", "in press", "published"]

THEMES = {
    "dark": {
        "bg": "#07090B", "card": "#0C1116", "edge": "#1E2831", "sub": "#101820",
        "ink": "#F2F5F8", "muted": "#A3ADB9", "faint": "#78828E",
        "dry": "#E455C0", "wet": "#2FD98A", "track": "#182029",
        "wash": 1.0,
    },
    "light": {
        "bg": "#FFFFFF", "card": "#FBFBF9", "edge": "#E2E0D9", "sub": "#F4F3EF",
        "ink": "#12161B", "muted": "#454C55", "faint": "#5F6771",
        "dry": "#A81E8C", "wet": "#0F6E44", "track": "#E6E4DD",
        "wash": 0.42,
    },
}

PAPERS = [
    # (short title, venue, stage 1-5, first author, channel)
    ("Blood-brain barrier transport AI", "Brain Network Disorders", 5, True, "dry"),
    ("Cordyanhydride A and hepatic lipogenesis", "Biosci. Biotechnol. Biochem.", 5, True, "wet"),
    ("Recombinant cell-permeable puromycin NAT", "J. Microbiol. Biotechnol.", 5, False, "wet"),
    ("Chrysanthemum morifolium and presbyopia", "Natural Product Sciences", 5, False, "wet"),
    ("ToxBench: leakage-audited benchmark", "BMC Bioinformatics", 4, True, "dry"),
    ("EEG foundation-model shortcut audit", "Scientific Reports", 3, True, "dry"),
    ("Explainable DBS status prediction", "BMC Med. Inform. Decis. Mak.", 3, True, "dry"),
    ("RATAN-PBind: de novo binder nomination", "J. Cheminformatics", 2, True, "dry"),
    ("CSF markers and cognitive decline", "Scientific Reports", 1, True, "dry"),
]

TOOLS_DRY = [
    "ESM-2 / ESMC + sparse autoencoders",
    "RFdiffusion / ProteinMPNN",
    "AlphaFold2-3 / Boltz-1-2 / ESMFold",
    "Schrodinger: docking, MD, screening",
    "PyTorch, retrieval-augmented models",
    "nested CV, calibration, leakage audit",
    "applicability domain, equivalence tests",
]
TOOLS_WET = [
    "human iPSC and ReN progenitors",
    "astrocyte / neuronal differentiation",
    "CRISPR-Cas9 + CRISPResso2 readout",
    "Zeiss LSM 980 confocal, certified",
    "immunofluorescence, live-cell imaging",
    "Gibson cloning, vector design, PCR",
    "expression, affinity chromatography",
]

REPOS = [
    ("RATAN-PBind", "Target-aware nomination of de novo binders", "dry"),
    ("ToxBench", "Leakage-audited toxicology benchmark", "dry"),
    ("eeg-fm-shortcut-audit", "Preregistered EEG foundation-model audit", "dry"),
    ("BBB-Trans-AI", "Sequence-structure BBB peptide prediction", "dry"),
    ("ppmi-csf-cognitive-decline", "CSF markers in the PPMI cohort", "dry"),
    ("DBS-Candidacy-Screening", "Explainable DBS status prediction", "dry"),
    ("DBS-BBB-Multimodal-Fusion", "Wearable, gait and voice fusion", "dry"),
    ("cv", "Curriculum vitae as a live web page", "dry"),
]

LINKS = [
    ("CV", "kartic03.github.io/cv"),
    ("ORCID", "0009-0005-5939-4192"),
    ("EMAIL", "karticmishra03@gmail.com"),
    ("GITHUB", "github.com/kartic03"),
]

MONO = "ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def head(t: dict, h: int, label: str, extra_css: str = "") -> list[str]:
    """Card shell shared by every panel, including the drifting wash."""
    ws = t["wash"]
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" role="img" aria-label="{esc(label)}">',
        "<defs>",
        f'<clipPath id="cc"><rect x="1" y="1" width="{W-2}" height="{h-2}" rx="17"/></clipPath>',
        f'<linearGradient id="eg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity=".5"/>'
        f'<stop offset=".5" stop-color="{t["edge"]}" stop-opacity=".9"/>'
        f'<stop offset="1" stop-color="{t["dry"]}" stop-opacity=".5"/></linearGradient>',
        f'<linearGradient id="w1" gradientUnits="objectBoundingBox" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity="{.22*ws:.3f}"/>'
        f'<stop offset=".48" stop-color="{t["wet"]}" stop-opacity="0"/>'
        f'<stop offset=".62" stop-color="{t["dry"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{t["dry"]}" stop-opacity="{.21*ws:.3f}"/>'
        f'<animateTransform attributeName="gradientTransform" type="rotate" '
        f'from="0 .5 .5" to="360 .5 .5" dur="31s" repeatCount="indefinite"/></linearGradient>',
        "</defs>",
        "<style>"
        f".t{{font:600 12px {MONO};fill:{t['faint']};letter-spacing:.26em}}"
        f".ttl{{font:700 15px {MONO};fill:{t['ink']};letter-spacing:.02em}}"
        f".b{{font:500 11.5px {MONO};fill:{t['ink']}}}"
        f".s{{font:400 10px {MONO};fill:{t['faint']};letter-spacing:.04em}}"
        f".m{{font:400 10.5px {MONO};fill:{t['muted']}}}"
        f".tag{{font:600 8.5px {MONO};letter-spacing:.1em}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        + extra_css + "</style>",
        f'<rect width="{W}" height="{h}" rx="18" fill="{t["bg"]}"/>',
        '<g clip-path="url(#cc)">',
        f'<rect x="1" y="1" width="{W-2}" height="{h-2}" fill="{t["card"]}"/>',
        f'<rect x="1" y="1" width="{W-2}" height="{h-2}" fill="url(#w1)"/>',
        "</g>",
        f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="17" fill="none" '
        f'stroke="url(#eg)" stroke-width="1.4"/>',
    ]
    return o


# ══════════════════════════════════════════════════════════════════════════
def research(t: dict) -> str:
    rows = len(PAPERS)
    row_h = 27
    top = 92          # clears the subtitle; stage labels sit at top-14
    h = top + rows * row_h + 30
    loop = 18.0
    # Rows are always drawn and the bars always sit at their true stage: a
    # README panel that animates in from nothing just reads as broken while it
    # loads. The motion is a highlight travelling down the list instead.
    css = []
    for i in range(rows):
        d = i * 0.42
        css.append("@keyframes rr%d{0%%,%.1f%%{opacity:.62}"
                   "%.1f%%{opacity:1}%.1f%%,100%%{opacity:.62}}"
                   % (i, d / loop * 100, (d + 0.4) / loop * 100,
                      (d + 2.2) / loop * 100))
        css.append(".rr%d{animation:rr%d %.1fs ease-in-out infinite}" % (i, i, loop))
        css.append("@keyframes rf%d{0%%,%.1f%%{opacity:0}"
                   "%.1f%%{opacity:.55}%.1f%%,100%%{opacity:0}}"
                   % (i, d / loop * 100, (d + 0.4) / loop * 100,
                      (d + 2.2) / loop * 100))
        css.append(".rf%d{animation:rf%d %.1fs ease-in-out infinite}" % (i, i, loop))

    o = head(t, h, "Publication pipeline", "".join(css))
    a = o.append
    a(f'<text class="t" x="30" y="38">RESEARCH PIPELINE</text>')
    a(f'<text class="s" x="30" y="56">nine manuscripts &#183; seven first-authored '
      f'&#183; four published, one in press</text>')

    tx = 470          # where the track starts
    tw = 372
    seg = tw / len(STAGES)
    for k, name in enumerate(STAGES):
        a(f'<text class="tag" x="{tx + seg*k + seg/2:.0f}" y="{top-14}" '
          f'text-anchor="middle" fill="{t["faint"]}">{name.upper()}</text>')
        a(f'<line x1="{tx + seg*k:.0f}" y1="{top-8}" x2="{tx + seg*k:.0f}" '
          f'y2="{top + rows*row_h - 8}" stroke="{t["track"]}" stroke-width="1"/>')

    for i, (title, venue, stage, first, ch) in enumerate(PAPERS):
        y = top + i * row_h
        col = t[ch]
        a(f'<g class="rr{i}">')
        a(f'<circle cx="34" cy="{y+2:.0f}" r="3" fill="{col}"/>')
        short = title if len(title) <= 40 else title[:39] + "…"
        a(f'<text class="b" x="46" y="{y+6:.0f}">{esc(short)}</text>')
        a(f'<text class="s" x="46" y="{y+18:.0f}">{esc(venue)}'
          f'{" &#183; first author" if first else ""}</text>')
        a(f'<rect x="{tx}" y="{y-2:.0f}" width="{tw:.0f}" height="7" rx="3.5" '
          f'fill="{t["track"]}"/>')
        a(f'<rect x="{tx}" y="{y-2:.0f}" width="{seg*stage:.0f}" '
          f'height="7" rx="3.5" fill="{col}" opacity=".9"/>')
        a(f'<rect class="rf{i}" x="{tx}" y="{y-2:.0f}" width="{seg*stage:.0f}" '
          f'height="7" rx="3.5" fill="#FFFFFF" opacity="0"/>')
        a("</g>")
    a("</svg>")
    return "".join(o)


# ══════════════════════════════════════════════════════════════════════════
def toolchain(t: dict) -> str:
    n = max(len(TOOLS_DRY), len(TOOLS_WET))
    row_h = 26
    top = 110         # channel headings sit at top-30, clear of the subtitle
    h = top + n * row_h + 26
    loop = 16.0
    css = ["@keyframes spine{0%,100%{opacity:.25}50%{opacity:.8}}",
           ".spine{animation:spine 4s ease-in-out infinite}"]
    for i in range(n):
        for side, off in (("d", 0.0), ("w", 0.55)):
            d = i * 0.5 + off
            css.append("@keyframes t%s%d{0%%,%.1f%%{opacity:.34}"
                       "%.1f%%{opacity:1}%.1f%%,100%%{opacity:.34}}"
                       % (side, i, d / loop * 100, (d + 0.35) / loop * 100,
                          (d + 2.6) / loop * 100))
            css.append(".t%s%d{animation:t%s%d %.1fs ease-in-out infinite}"
                       % (side, i, side, i, loop))

    o = head(t, h, "Toolchain across both channels", "".join(css))
    a = o.append
    a(f'<text class="t" x="30" y="38">TOOLCHAIN</text>')
    a(f'<text class="s" x="30" y="56">most people pick a side. the useful part was '
      f'not picking one.</text>')

    mid = W / 2
    a(f'<line class="spine" x1="{mid}" y1="{top-22}" x2="{mid}" '
      f'y2="{top + n*row_h - 10}" stroke="url(#eg)" stroke-width="1.6"/>')
    a(f'<text class="tag" x="{mid-22:.0f}" y="{top-30}" text-anchor="end" '
      f'fill="{t["dry"]}">COMPUTATIONAL</text>')
    a(f'<text class="tag" x="{mid+22:.0f}" y="{top-30}" '
      f'fill="{t["wet"]}">EXPERIMENTAL</text>')

    for i, s in enumerate(TOOLS_DRY):
        y = top + i * row_h
        a(f'<g class="td{i}">'
          f'<text class="m" x="{mid-24:.0f}" y="{y:.0f}" text-anchor="end">{esc(s)}</text>'
          f'<circle cx="{mid-12:.0f}" cy="{y-4:.0f}" r="2.6" fill="{t["dry"]}"/></g>')
    for i, s in enumerate(TOOLS_WET):
        y = top + i * row_h
        a(f'<g class="tw{i}">'
          f'<circle cx="{mid+12:.0f}" cy="{y-4:.0f}" r="2.6" fill="{t["wet"]}"/>'
          f'<text class="m" x="{mid+24:.0f}" y="{y:.0f}">{esc(s)}</text></g>')
    a("</svg>")
    return "".join(o)


# ══════════════════════════════════════════════════════════════════════════
def code(t: dict) -> str:
    cols, cw, chh, gap = 2, 402, 54, 14
    rows = (len(REPOS) + cols - 1) // cols
    top = 82
    h = top + rows * (chh + gap) + 16
    loop = 14.0
    css = []
    # cards stay put; only the border glow travels, so nothing is ever blank
    for i in range(len(REPOS)):
        d = i * 0.42
        css.append("@keyframes cg%d{0%%,%.1f%%{opacity:0}%.1f%%{opacity:.95}"
                   "%.1f%%,100%%{opacity:0}}"
                   % (i, d / loop * 100, (d + 0.35) / loop * 100,
                      (d + 1.9) / loop * 100))
        css.append(".cg%d{animation:cg%d %.1fs ease-in-out infinite}" % (i, i, loop))

    o = head(t, h, "Repositories", "".join(css))
    a = o.append
    a(f'<text class="t" x="30" y="38">CODE</text>')
    a(f'<text class="s" x="30" y="56">every computational manuscript ships with a '
      f'public repository</text>')

    for i, (name, desc, ch) in enumerate(REPOS):
        cx = 30 + (i % cols) * (cw + 16)
        cy = top + (i // cols) * (chh + gap)
        col = t[ch]
        a('<g>')
        a(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{chh}" rx="10" '
          f'fill="{t["sub"]}" stroke="{t["edge"]}" stroke-width="1"/>')
        a(f'<rect class="cg{i}" x="{cx}" y="{cy}" width="{cw}" height="{chh}" rx="10" '
          f'fill="none" stroke="{col}" stroke-width="1.2" opacity="0"/>')
        a(f'<circle cx="{cx+18}" cy="{cy+21}" r="3.4" fill="#3572A5"/>')
        a(f'<text class="b" x="{cx+30}" y="{cy+25}">{esc(name)}</text>')
        a(f'<text class="s" x="{cx+30}" y="{cy+40}">{esc(desc)}</text>')
        a("</g>")
    a("</svg>")
    return "".join(o)


# ══════════════════════════════════════════════════════════════════════════
def footer(t: dict) -> str:
    h = 96
    css = ["@keyframes slide{0%{transform:translateX(-100%)}"
           "100%{transform:translateX(100%)}}",
           ".sw{animation:slide 7s linear infinite}"]
    o = head(t, h, "Contact", "".join(css))
    a = o.append
    a(f'<defs><clipPath id="rule"><rect x="30" y="30" width="{W-60}" height="2" '
      f'rx="1"/></clipPath>'
      f'<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity="0"/>'
      f'<stop offset=".5" stop-color="{t["dry"]}"/>'
      f'<stop offset="1" stop-color="{t["wet"]}" stop-opacity="0"/>'
      f'</linearGradient></defs>')
    a(f'<rect x="30" y="30" width="{W-60}" height="2" rx="1" fill="{t["track"]}"/>')
    a(f'<g clip-path="url(#rule)"><rect class="sw" x="30" y="30" width="{W-60}" '
      f'height="2" fill="url(#sg)"/></g>')
    x = 30
    for label, val in LINKS:
        a(f'<text class="tag" x="{x}" y="{60}" fill="{t["faint"]}">{label}</text>')
        a(f'<text class="m" x="{x}" y="{76}">{esc(val)}</text>')
        x += max(len(val) * 6.4 + 34, 150)
    a("</svg>")
    return "".join(o)


# research() and toolchain() are kept but not generated: both panels were cut
# from the page. Add either back here if it is ever wanted again.
PANELS = {"code": code, "footer": footer}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="dist")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    for name, fn in PANELS.items():
        for theme in ("dark", "light"):
            svg = fn(THEMES[theme])
            p = os.path.join(args.outdir, f"{name}-{theme}.svg")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(svg)
            print(f"wrote {p}  ({len(svg.encode('utf-8'))/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
