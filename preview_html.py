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
import os

ORDER = ["header", "code", "shooter", "footer"]

# Panels that are wrapped in a link, the same way the README wraps them.
PANEL_LINK = {"code": "https://github.com/kartic03?tab=repositories"}

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
  img{{width:min(880px,100%);height:auto;display:block;border-radius:18px}}
  /* the code panel is a link, matching the README; the chip inside it is the
     visible affordance, so the wrapper only needs a focus ring */
  a.panel{{display:block;border-radius:18px;outline-offset:3px}}
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

    dark, light, present = {}, {}, []
    for n in ORDER:
        d = os.path.join(args.dir, f"{n}-dark.svg")
        l = os.path.join(args.dir, f"{n}-light.svg")
        if not os.path.exists(d):
            print(f"  skip {n}")
            continue
        dark[n] = uri(d)
        light[n] = uri(l) if os.path.exists(l) else dark[n]
        present.append(n)
        print(f"  {n:<9} {os.path.getsize(d)/1024:6.1f} KB")

    parts = []
    for i, n in enumerate(present):
        tag = f'<img id="p{i}" alt="{n}" src="{dark[n]}">'
        if n in PANEL_LINK:
            tag = (f'<a class="panel" href="{PANEL_LINK[n]}" '
                   f'target="_blank" rel="noopener">{tag}</a>')
        parts.append(tag)
    imgs = "\n".join(parts)

    import json
    html = PAGE.format(imgs=imgs, dark=json.dumps(dark), light=json.dumps(light),
                       names=json.dumps(present))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB, self-contained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
