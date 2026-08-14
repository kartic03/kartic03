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
import json
import os
import urllib.request

API = "https://api.github.com"
REPO_CACHE = "dist/.repo-cache.json"

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

# Most of these repositories have no description set on GitHub, so the panel
# would render blank rows. These fill the gap and are used only when GitHub
# returns nothing; set a real description on the repo and it wins automatically.
DESC_FALLBACK = {
    "RATAN-PBind": "Target-aware nomination of de novo binders",
    "Toxbench": "Leakage-audited toxicology benchmark",
    "ToxBench": "Leakage-audited toxicology benchmark",
    "eeg-fm-shortcut-audit": "Preregistered EEG foundation-model audit",
    "BBB-Trans-AI": "Sequence-structure BBB peptide prediction",
    "ppmi-csf-cognitive-decline": "CSF markers in the PPMI cohort",
    "DBS-Candidacy-Screening": "Explainable DBS status prediction",
    "DBS-BBB-Multimodal-Fusion": "Wearable, gait and voice fusion",
    "cv": "Curriculum vitae as a live web page",
    "kartic03": "This profile, generated",
}

LANG_DOT = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "HTML": "#E34C26",
    "Shell": "#89E051", "R": "#198CE7", "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6", "C": "#555555", "C++": "#F34B7D",
    "Java": "#B07219", "Rust": "#DEA584", "Go": "#00ADD8", "CSS": "#563D7C",
}

MAX_CARDS = 8

# A tile normally links to its repository. These go somewhere more useful:
# the CV repository is a deployment, and the page it deploys is the point.
REPO_LINK = {"cv": "https://kartic03.github.io/cv/"}


def fetch_repos(user: str) -> list[dict]:
    """Live repository list, newest activity first, cached against API failure.

    Without this the code panel is a hardcoded list that goes stale the moment a
    repository is added or renamed.
    """
    try:
        hdrs = {"User-Agent": "profile-panels/1.0"}
        tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if tok:
            hdrs["Authorization"] = f"Bearer {tok}"
        req = urllib.request.Request(
            f"{API}/users/{user}/repos?per_page=100&sort=pushed", headers=hdrs)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.loads(r.read().decode("utf-8"))
        repos = [{"name": x["name"],
                  "desc": (x.get("description") or "").strip(),
                  "lang": x.get("language") or ""}
                 for x in raw if not x.get("fork")]
        if not repos:
            raise RuntimeError("no repositories returned")
        os.makedirs(os.path.dirname(REPO_CACHE) or ".", exist_ok=True)
        with open(REPO_CACHE, "w", encoding="utf-8") as fh:
            json.dump(repos, fh, indent=1)
        return repos
    except Exception as exc:                               # noqa: BLE001
        if not os.path.exists(REPO_CACHE):
            raise SystemExit(f"repo list failed and no cache: {exc}")
        print(f"!! repo list failed ({exc}); using {REPO_CACHE}")
        return json.load(open(REPO_CACHE, encoding="utf-8"))

# key, label, shown value, where it actually goes. Each becomes its own image,
# because four destinations cannot live inside one <img>.
LINKS = [
    ("cv", "CV", "kartic03.github.io/cv", "https://kartic03.github.io/cv/"),
    ("orcid", "ORCID", "0009-0005-5939-4192",
     "https://orcid.org/0009-0005-5939-4192"),
    # Gmail's compose window rather than mailto:, which depends on the visitor
    # having a desktop mail client configured and often does nothing at all.
    #   u/0/    the first signed-in account, rather than an account chooser
    #   tf=cm   compose inside the full Gmail interface. The older view=cm
    #           opens a bare standalone compose popup with no Gmail around it.
    #   fs=1    full screen, not the small corner window
    # &amp; because this goes straight into an href attribute.
    ("email", "EMAIL", "karticmishra03@gmail.com",
     "https://mail.google.com/mail/u/0/?fs=1&amp;tf=cm"
     "&amp;to=karticmishra03@gmail.com"),
    ("github", "GITHUB", "github.com/kartic03", "https://github.com/kartic03"),
]

MONO = "ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def head(t: dict, h: int, label: str, extra_css: str = "",
         w: int = W, rx: int = 18, pad_l: int = 0, pad_r: int = 0) -> list[str]:
    """Card shell shared by every panel, including the drifting wash.

    pad_l/pad_r leave transparent margin inside the image. Gutters between
    side-by-side panels have to be drawn, not spaced: whitespace between two
    images in a README is unpredictable, and any of it pushes a pair past the
    column width and drops the second one onto its own line. With the gutter
    inside the image, every row spans exactly the same width and the edges of
    every panel line up down the page.

    Coordinates passed by callers are relative to the card, not the image.
    """
    ws = t["wash"]
    W = w - pad_l - pad_r
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">',
        "<defs>",
        f'<clipPath id="cc"><rect x="1" y="1" width="{W-2}" height="{h-2}" rx="{rx-1}"/></clipPath>',
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
        f'<g transform="translate({pad_l},0)">',
        f'<rect width="{W}" height="{h}" rx="{rx}" fill="{t["bg"]}"/>',
        '<g clip-path="url(#cc)">',
        f'<rect x="1" y="1" width="{W-2}" height="{h-2}" fill="{t["card"]}"/>',
        f'<rect x="1" y="1" width="{W-2}" height="{h-2}" fill="url(#w1)"/>',
        "</g>",
        f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="{rx-1}" fill="none" '
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
    a("</g></svg>")
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
    a("</g></svg>")
    return "".join(o)


# ══════════════════════════════════════════════════════════════════════════
def code_head(t: dict, shown: int) -> str:
    """Eyebrow strip above the repository tiles."""
    o = head(t, 76, "Repositories")
    a = o.append
    a('<text class="t" x="30" y="34">CODE</text>')
    a(f'<text class="s" x="30" y="54">every computational manuscript ships with a '
      f'public repository &#183; {shown} most recently pushed</text>')
    a("</g></svg>")
    return "".join(o)


# A profile README column is 831px at its widest. Every row on the page spans
# exactly COLUMN, so a tile pair, a chip row and a full-width panel all share
# the same left and right edge. Slots divide COLUMN evenly; the gutter is
# drawn inside each slot rather than spaced between images.
COLUMN = 828                       # divides by both 2 and 4
TILE_W, TILE_H = COLUMN // 2, 62   # 414
TILE_GUTTER = 10


def repo_tile(t: dict, r: dict, i: int) -> str:
    """One repository, as its own image so the README can link it to its repo.

    An SVG served through <img> cannot carry a link, and GitHub's sanitiser
    drops inline <svg>, <object> and image maps alike. One card per file is the
    only way each repository can point somewhere different.
    """
    css = ["@keyframes glow%d{0%%,%.1f%%{opacity:0}%.1f%%{opacity:.9}"
           "%.1f%%,100%%{opacity:0}}"
           % (i, i * 3.0, i * 3.0 + 2.5, i * 3.0 + 15.0),
           ".gl%d{animation:glow%d 14s ease-in-out infinite}" % (i, i)]
    # Left column carries the gutter on its right, right column on its left,
    # so the pair butts up to exactly COLUMN with a clean gap down the middle.
    half = TILE_GUTTER // 2
    pl, pr = (0, half) if i % 2 == 0 else (half, 0)
    cw = TILE_W - pl - pr
    o = head(t, TILE_H, r["name"], "".join(css), w=TILE_W, rx=12,
             pad_l=pl, pad_r=pr)
    a = o.append
    desc = r.get("desc") or DESC_FALLBACK.get(r["name"], "")
    if len(desc) > 50:
        desc = desc[:49].rstrip() + "…"
    dot = LANG_DOT.get(r.get("lang", ""), t["faint"])
    a(f'<rect class="gl{i}" x="1" y="1" width="{cw-2}" height="{TILE_H-2}" rx="11" '
      f'fill="none" stroke="{t["dry"]}" stroke-width="1.2" opacity="0"/>')
    a(f'<circle cx="22" cy="27" r="3.4" fill="{dot}"/>')
    a(f'<text class="b" x="34" y="31">{esc(r["name"])}</text>')
    a(f'<text class="s" x="34" y="47">{esc(desc)}</text>')
    a("</g></svg>")
    return "".join(o)


def code_all(t: dict, total: int) -> str:
    """Closing strip under the tiles, linked to the full repositories tab."""
    css = ["@keyframes arrow{0%,72%,100%{transform:translateX(0)}"
           "82%{transform:translateX(3px)}}",
           ".ar{animation:arrow 3.4s ease-in-out infinite;transform-box:fill-box}"]
    h = 46
    o = head(t, h, f"All {total} repositories", "".join(css))
    a = o.append
    a(f'<text class="tag" x="30" y="27" fill="{t["faint"]}">'
      f'PINNED BY MOST RECENT PUSH</text>')
    lbl = f"ALL {total} REPOSITORIES"
    cwid = len(lbl) * 5.95 + 40
    cx, cy, cht = W - 30 - cwid, 12, 22
    a(f'<rect x="{cx:.0f}" y="{cy}" width="{cwid:.0f}" height="{cht}" rx="11" '
      f'fill="{t["sub"]}" stroke="{t["edge"]}" stroke-width="1"/>'
      f'<text class="tag" x="{cx+13:.0f}" y="{cy+14}" fill="{t["dry"]}">{lbl}</text>'
      f'<text class="tag ar" x="{cx+cwid-19:.0f}" y="{cy+14}" '
      f'fill="{t["dry"]}">&#8594;</text>')
    a("</g></svg>")
    return "".join(o)


def code(t: dict, repos: list | None = None, total: int | None = None) -> str:
    total = len(repos or []) if total is None else total
    repos = (repos or [])[:MAX_CARDS]
    cols, cw, chh, gap = 2, 402, 54, 14
    rows = (len(repos) + cols - 1) // cols
    top = 82
    h = top + rows * (chh + gap) + 38     # the extra 22 is the "all repos" chip
    loop = 14.0
    css = ["@keyframes arrow{0%,72%,100%{transform:translateX(0)}"
           "82%{transform:translateX(3px)}}",
           ".ar{animation:arrow 3.4s ease-in-out infinite;transform-box:fill-box}"]
    # cards stay put; only the border glow travels, so nothing is ever blank
    for i in range(len(repos)):
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
      f'public repository &#183; {len(repos)} most recently pushed</text>')

    for i, r in enumerate(repos):
        name = r["name"]
        desc = r.get("desc") or DESC_FALLBACK.get(name, "")
        if len(desc) > 46:
            desc = desc[:45].rstrip() + "…"
        dot = LANG_DOT.get(r.get("lang", ""), t["faint"])
        cx = 30 + (i % cols) * (cw + 16)
        cy = top + (i // cols) * (chh + gap)
        a('<g>')
        a(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{chh}" rx="10" '
          f'fill="{t["sub"]}" stroke="{t["edge"]}" stroke-width="1"/>')
        a(f'<rect class="cg{i}" x="{cx}" y="{cy}" width="{cw}" height="{chh}" rx="10" '
          f'fill="none" stroke="{t["dry"]}" stroke-width="1.2" opacity="0"/>')
        a(f'<circle cx="{cx+18}" cy="{cy+21}" r="3.4" fill="{dot}"/>')
        a(f'<text class="b" x="{cx+30}" y="{cy+25}">{esc(name)}</text>')
        a(f'<text class="s" x="{cx+30}" y="{cy+40}">{esc(desc)}</text>')
        a("</g>")

    # "all repositories" chip. An SVG served through <img> cannot carry its own
    # link, so the README wraps this whole panel in an <a> to the repositories
    # tab; the chip is what tells a reader the panel is clickable at all.
    lbl = f"ALL {total} REPOSITORIES"
    cwid = len(lbl) * 5.95 + 40           # 8.5px mono at .1em, plus padding
    cxx, cyy, cht = W - 30 - cwid, h - 38, 22
    a(f'<g><rect x="{cxx:.0f}" y="{cyy}" width="{cwid:.0f}" height="{cht}" rx="11" '
      f'fill="{t["sub"]}" stroke="{t["edge"]}" stroke-width="1"/>'
      f'<text class="tag" x="{cxx+13:.0f}" y="{cyy+14}" fill="{t["dry"]}">{lbl}</text>'
      f'<text class="tag ar" x="{cxx+cwid-19:.0f}" y="{cyy+14}" '
      f'fill="{t["dry"]}">&#8594;</text></g>')
    a("</g></svg>")
    return "".join(o)


# ══════════════════════════════════════════════════════════════════════════
CHIP_W, CHIP_H = COLUMN // 4, 72   # 207
CHIP_GUTTER = 8


def link_chip(t: dict, label: str, val: str, i: int) -> str:
    """One contact link. The travelling rule that used to run the width of the
    footer now sits inside each chip, offset so the four still read as a set."""
    css = ["@keyframes slide{0%{transform:translateX(-100%)}"
           "100%{transform:translateX(100%)}}",
           ".sw{animation:slide 7s linear infinite;animation-delay:-%.2fs}"
           % (i * 1.75)]
    # Four equal cards with three equal gutters, the whole row spanning COLUMN:
    # card k sits at k*(card+gutter), and its slot starts at k*CHIP_W.
    card = (COLUMN - 3 * CHIP_GUTTER) // 4
    pl = i * (card + CHIP_GUTTER) - i * CHIP_W
    pr = CHIP_W - pl - card
    o = head(t, CHIP_H, f"{label}: {val}", "".join(css), w=CHIP_W, rx=12,
             pad_l=pl, pad_r=pr)
    a = o.append
    rw = card - 32
    a(f'<defs><clipPath id="rule"><rect x="16" y="20" width="{rw}" height="2" '
      f'rx="1"/></clipPath>'
      f'<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity="0"/>'
      f'<stop offset=".5" stop-color="{t["dry"]}"/>'
      f'<stop offset="1" stop-color="{t["wet"]}" stop-opacity="0"/>'
      f'</linearGradient></defs>')
    a(f'<rect x="16" y="20" width="{rw}" height="2" rx="1" fill="{t["track"]}"/>')
    a(f'<g clip-path="url(#rule)"><rect class="sw" x="16" y="20" width="{rw}" '
      f'height="2" fill="url(#sg)"/></g>')
    a(f'<text class="tag" x="16" y="42" fill="{t["faint"]}">{label}</text>')
    a(f'<text class="m" x="16" y="60">{esc(val)}</text>')
    a("</g></svg>")
    return "".join(o)


# research() and toolchain() are kept but not generated: both panels were cut
# from the page. Add either back here if it is ever wanted again.


README = """<!-- Generated by panels.py. Edit the generator, not this file: every
     build overwrites it, because the repository tiles and their links come
     from the live repository list.

     Dark is forced. There is no <picture>/prefers-color-scheme switch: the
     panels are designed as dark cards and read as intentional on a light
     GitHub theme. The light SVGs are still generated for the preview page. -->

<!-- Every image is wrapped in an <a> on purpose. GitHub auto-links any image
     that is not already inside one to the raw file in the repo, so an
     unwrapped panel opens as a still SVG when you click it. An <a> with no
     href does not work: the sanitiser strips it and the auto-link returns.
     So the header points at this profile - the page it is already on - which
     is the closest thing to a panel that does not go anywhere.

     The target="_blank" below is stripped by GitHub's sanitiser, so links
     open in the same tab here whatever this file says. It is kept because it
     is the correct intent and it does work in dist/page.html and in any
     other renderer. Ctrl-click or middle-click for a new tab on GitHub. -->

<a href="https://github.com/{user}"><img alt="Kartic - AI protein design to expression and in vitro validation" src="./dist/header-dark.svg" width="{col}"></a>

<a href="https://github.com/{user}?tab=repositories" target="_blank" rel="noopener noreferrer"><img alt="Code" src="./dist/code-head-dark.svg" width="{col}"></a>

{tiles}

<a href="https://github.com/{user}?tab=repositories" target="_blank" rel="noopener noreferrer"><img alt="All {total} repositories" src="./dist/code-all-dark.svg" width="{col}"></a>

<a href="https://github.com/{user}/{user}" target="_blank" rel="noopener noreferrer"><img alt="Contribution calendar as an arcade shooter: empty days destroyed, contribution pattern revealed" src="./dist/shooter-dark.svg" width="{col}"></a>

{links}

<!--
  Every panel is generated, not hand-drawn.

    header.py     profile card; language shares come from the GitHub API and
                  the avatar is inlined as a data URI, because an SVG that
                  references an external image renders empty once GitHub
                  proxies it through Camo
    panels.py     repository tiles, contact chips, and this README
    shooter.py    contribution calendar as an arcade shooter
    preview.py    stacks every panel into one page for review

  Each repository is its own image inside its own <a>. That is not a style
  choice: an SVG served through <img> cannot carry links, and GitHub's
  sanitiser drops inline <svg>, <object> and image maps, so one card per file
  is the only way each card can point somewhere different. code() in
  panels.py still builds the single-framed-panel version, which looks better
  but sends every card to the same place.

  Every row spans the same width, and gutters are drawn inside the images
  rather than spaced between them, so nothing depends on how wide a browser
  renders the whitespace between two inline images.

  Cut from the page but still in the source, each one line from returning:
  structure.py (de novo design cascade), and research() and toolchain() in
  panels.py.

  Regenerate everything:   python build.py
  Rebuild one panel:       python shooter.py --user kartic03

  .github/workflows/build.yml refreshes the data-driven panels daily.
-->
"""


def write(path: str, svg: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="kartic03")
    ap.add_argument("--outdir", default="dist")
    ap.add_argument("--readme", default="README.md")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    repos = fetch_repos(args.user)
    # The profile repository is this README's own home. It is real work, but a
    # tile linking to the page you are already looking at is noise, and it was
    # costing a genuine repository its slot.
    repos = [r for r in repos if r["name"].lower() != args.user.lower()]
    total = len(repos)
    pinned = repos[:MAX_CARDS]
    print(f"{total} repositories; pinning the {len(pinned)} newest-pushed")
    if total > MAX_CARDS:
        rest = ", ".join(r["name"] for r in repos[MAX_CARDS:])
        print(f"   behind the chip ({total - MAX_CARDS}): {rest}")
    blank = [r["name"] for r in pinned
             if not r["desc"] and r["name"] not in DESC_FALLBACK]
    if blank:
        print("!! no description on GitHub and no fallback: " + ", ".join(blank))

    # A stale repo-N tile would outlive the repository it was named for, and
    # the single-panel code-*.svg is no longer referenced by anything.
    for f in os.listdir(args.outdir):
        if f.startswith("repo-") and f.endswith(".svg"):
            os.remove(os.path.join(args.outdir, f))
        elif f in ("code-dark.svg", "code-light.svg"):
            os.remove(os.path.join(args.outdir, f))

    n = 0
    for theme in ("dark", "light"):
        t = THEMES[theme]
        write(os.path.join(args.outdir, f"code-head-{theme}.svg"),
              code_head(t, len(pinned)))
        write(os.path.join(args.outdir, f"code-all-{theme}.svg"),
              code_all(t, total))
        for i, r in enumerate(pinned):
            write(os.path.join(args.outdir, f"repo-{i}-{theme}.svg"),
                  repo_tile(t, r, i))
        for i, (key, label, val, _) in enumerate(LINKS):
            write(os.path.join(args.outdir, f"link-{key}-{theme}.svg"),
                  link_chip(t, label, val, i))
        n += 2 + len(pinned) + len(LINKS)
    print(f"wrote {n} panel files to {args.outdir}/")

    # Two tiles a line, and no whitespace between the two <a> tags: a newline
    # there would render as a space and push the pair past the column.
    cells = []
    for i, r in enumerate(pinned):
        name = r["name"]
        href = REPO_LINK.get(name, f"https://github.com/{args.user}/{name}")
        cells.append(f'<a href="{href}" target="_blank" rel="noopener noreferrer">'
                     f'<img alt="{esc(name)}" '
                     f'src="./dist/repo-{i}-dark.svg" width="{TILE_W}"></a>')
    rows = ["".join(cells[i:i + 2]) for i in range(0, len(cells), 2)]
    # No whitespace between chips either: the gutters are drawn inside them.
    links = "".join(
        f'<a href="{href}" target="_blank" rel="noopener noreferrer">'
        f'<img alt="{label}: {esc(val)}" '
        f'src="./dist/link-{key}-dark.svg" width="{CHIP_W}"></a>'
        for key, label, val, href in LINKS)

    with open(args.readme, "w", encoding="utf-8") as fh:
        fh.write(README.format(user=args.user, total=total, col=COLUMN,
                               tiles="\n".join(rows), links=links))
    print(f"wrote {args.readme}  ({len(pinned)} cards, {len(LINKS)} contact chips)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
