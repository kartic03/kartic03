#!/usr/bin/env python3
"""
Build a self-contained HTML preview of the profile.

Each panel is embedded as a base64 data URI inside an <img>, which matters for
two reasons: it survives being opened from anywhere (no relative paths to
break), and <img> is exactly how GitHub serves these, so CSS and SMIL inside
the file animate while anything external stays blocked. Rendering the panels
as inline <svg> instead would be a prettier file and a less honest preview.
"""

from __future__ import annotations

import argparse
import base64
import json
import os

REPO_CACHE = "dist/.repo-cache.json"

USER = "kartic03"

# The preview mirrors the README exactly, including its links: full-width rows
# on their own line, tiles and chips flowing two and four to a row.
ROWS = [
    ["header"],
    ["shooter"],
    ["code-head"],
    "TILES",                       # expands to repo-0 .. repo-N
    ["code-all"],
    ["link-cv", "link-orcid", "link-email", "link-github"],
]

LINK = {
    # No "header" entry: the profile card deliberately does not navigate.
    # No "shooter" entry either: both go nowhere by design.
    "code-head": f"https://github.com/{USER}?tab=repositories",
    "code-all": f"https://github.com/{USER}?tab=repositories",
    "link-cv": f"https://{USER}.github.io/cv/",
    "link-orcid": "https://orcid.org/0009-0005-5939-4192",
    "link-email": ("https://mail.google.com/mail/?view=cm&amp;fs=1"
                   "&amp;to=hi.kartic@gmail.com"),
    "link-github": f"https://github.com/{USER}",
}

# Match panels.py, and match what GitHub actually gives a profile README.
COLUMN = 828
WIDTH = {"link-": COLUMN // 4, "repo-": COLUMN // 2}   # else full width

# A tile normally links to its repository; the CV tile links to the page it
# deploys. Mirrors REPO_LINK in panels.py.
REPO_LINK = {"cv": f"https://{USER}.github.io/cv/"}

PAGE = """<!DOCTYPE html>
<!-- dark is forced: no prefers-color-scheme query anywhere, so the OS setting
     is ignored and brightfield is opt-in via the toggle -->
<html lang="en" data-t="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kartic — profile preview</title>
<style>
  :root{{--bg:#07090B;--fg:#EAEEF1;--dim:#7D8794;--edge:#1B222A;--chip:#0E141A}}
  html[data-t="light"]{{--bg:#F7F7F4;--fg:#14181C;--dim:#5D646D;--edge:#DEDCD5;--chip:#FFF}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);
    font:14px/1.6 ui-monospace,"Cascadia Mono",Menlo,Consolas,monospace;
    display:flex;flex-direction:column;align-items:center;
    padding:26px 20px 60px;gap:18px;transition:background .25s,color .25s}}
  .bar{{width:min(880px,100%);display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
  .bar .who{{display:inline-flex;align-items:center;gap:.5rem;margin-right:auto;
    font-size:12.5px;letter-spacing:.05em;color:var(--dim)}}
  .bar .who b{{font-weight:700;color:var(--fg)}}
  .bar .who svg{{fill:none;stroke:currentColor;stroke-width:1.15;
    stroke-linejoin:round;flex:none}}
  button{{font:inherit;font-size:11px;letter-spacing:.09em;text-transform:uppercase;
    padding:.4rem .8rem;border-radius:99px;cursor:pointer;background:var(--chip);
    color:var(--dim);border:1px solid var(--edge);
    display:inline-flex;align-items:center;gap:.45rem;
    transition:color .18s,border-color .18s}}
  button:hover{{color:var(--fg)}}
  .bulb{{fill:none;stroke:currentColor;stroke-width:1.25;
    stroke-linecap:round;stroke-linejoin:round;flex:none}}
  .bulb .rays{{opacity:0;transition:opacity .2s}}
  .bulb .glass{{transition:fill .2s,stroke .2s}}
  /* lit only while brightfield is actually on */
  #theme.on{{color:#FFC862;border-color:#8A6A2E}}
  #theme.on .bulb .rays{{opacity:1}}
  #theme.on .bulb .glass{{fill:#FFC862;fill-opacity:.28}}
  /* rows mirror the README: full-width panels alone, tiles two across,
     contact chips four across, wrapping on narrow screens the same way */
  /* 828px with no gap is exactly what the README does: the gutters are
     drawn inside the images, so the preview must not add any of its own */
  .row{{display:flex;flex-wrap:wrap;gap:0;width:min(828px,100%);
    justify-content:flex-start}}
  img{{max-width:100%;height:auto;display:block;border-radius:14px}}
  .row > img, .row > a{{flex:0 1 auto;min-width:0}}
  a.panel{{display:block;border-radius:14px;outline-offset:3px;
    transition:transform .15s}}
  a.panel:hover{{transform:translateY(-2px)}}
  a.panel:focus-visible{{outline:2px solid #E455C0}}
</style>
</head>
<body>
<div class="bar">
  <span class="who">
    <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
      <path d="M3 2.4h8.5a1 1 0 0 1 1 1v10.2H4.4A1.4 1.4 0 0 1 3 12.2V2.4Z"/>
      <path d="M3 11.6h9.5"/>
    </svg>
    <b>kartic03</b>
  </span>
  <button id="theme">
    <svg class="bulb" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
      <g class="rays">
        <path d="M8 .7v1.5M2.8 2.8l1.05 1.05M13.2 2.8l-1.05 1.05M.7 8h1.5M13.8 8h1.5"/>
      </g>
      <path class="glass" d="M8 2.7a4.15 4.15 0 0 0-2.45 7.5c.35.26.55.64.55 1.05v.35h3.8v-.35c0-.41.2-.79.55-1.05A4.15 4.15 0 0 0 8 2.7Z"/>
      <path d="M6.4 13.1h3.2M6.9 14.7h2.2"/>
    </svg>
    <span id="themeLabel">brightfield</span>
  </button>
</div>
{imgs}
<script>
const DARK = {dark};
const LIGHT = {light};
const names = {names};
const root = document.documentElement;
let light = false;
function paint(){{
  names.forEach(function(n,i){{
    document.getElementById("p"+i).src = (light ? LIGHT : DARK)[n];
  }});
}}
document.getElementById("theme").addEventListener("click", function(){{
  light = !light;
  root.dataset.t = light ? "light" : "dark";
  document.getElementById("themeLabel").textContent =
    light ? "fluorescence" : "brightfield";
  this.classList.toggle("on", light);
  paint();
}});
</script>
</body>
</html>
"""


def uri(path: str) -> str:
    with open(path, "rb") as fh:
        return "data:image/svg+xml;base64," + base64.b64encode(fh.read()).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="dist")
    ap.add_argument("--out", default="dist/page.html")
    args = ap.parse_args()

    tiles = sorted(
        (f[:-9] for f in os.listdir(args.dir)
         if f.startswith("repo-") and f.endswith("-dark.svg")),
        key=lambda s: int(s.split("-")[1]))
    repo_href = {}
    if os.path.exists(REPO_CACHE):
        names = [r["name"] for r in json.load(open(REPO_CACHE, encoding="utf-8"))
                 if r["name"].lower() != USER.lower()]
        for i, name in enumerate(names[:len(tiles)]):
            repo_href[f"repo-{i}"] = REPO_LINK.get(
                name, f"https://github.com/{USER}/{name}")

    rows = [tiles if r == "TILES" else r for r in ROWS]
    dark, light, present = {}, {}, []
    for row in rows:
        for n in row:
            d = os.path.join(args.dir, f"{n}-dark.svg")
            if not os.path.exists(d):
                print(f"  skip {n}")
                continue
            l = os.path.join(args.dir, f"{n}-light.svg")
            dark[n] = uri(d)
            light[n] = uri(l) if os.path.exists(l) else dark[n]
            present.append(n)
            print(f"  {n:<26} {os.path.getsize(d)/1024:6.1f} KB")

    idx = {n: i for i, n in enumerate(present)}
    parts = []
    for row in rows:
        row = [n for n in row if n in idx]
        if not row:
            continue
        cells = []
        for n in row:
            w = next((v for p, v in WIDTH.items() if n.startswith(p)), 880)
            tag = (f'<img id="p{idx[n]}" alt="{n}" src="{dark[n]}" '
                   f'style="width:{w}px">')
            href = LINK.get(n) or repo_href.get(n)
            if href:
                tag = (f'<a class="panel" href="{href}" target="_blank" '
                       f'rel="noopener">{tag}</a>')
            cells.append(tag)
        parts.append('<div class="row">' + "".join(cells) + "</div>")
    imgs = "\n".join(parts)

    html = PAGE.format(imgs=imgs, dark=json.dumps(dark), light=json.dumps(light),
                       names=json.dumps(present))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB, self-contained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
