#!/usr/bin/env python3
"""
Render each panel to PNG with headless Edge, then stitch them into one page
image. Rendering the assembled SVG in a single pass overwhelms the browser
(hundreds of simultaneous animations), so this does it panel by panel.

Review aid only; nothing in the profile depends on it.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

ORDER = ["header", "code", "shooter", "footer"]
GAP = 18
PAD = 22

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge() -> str:
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    p = shutil.which("msedge") or shutil.which("chrome")
    if not p:
        raise SystemExit("no Edge/Chrome found for rendering")
    return p


def size_of(svg: str) -> tuple[int, int]:
    w = float(re.search(r'<svg[^>]*\swidth="([\d.]+)"', svg).group(1))
    h = float(re.search(r'<svg[^>]*\sheight="([\d.]+)"', svg).group(1))
    return round(w), round(h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="dark")
    ap.add_argument("--dir", default="dist")
    ap.add_argument("--pose", type=float, default=11.0,
                    help="seconds into the loop to freeze at")
    ap.add_argument("--out", default="dist/page-preview.png")
    args = ap.parse_args()

    from PIL import Image

    edge = find_edge()
    tmp = os.path.join(args.dir, "_sheet")
    os.makedirs(tmp, exist_ok=True)

    tiles = []
    for name in ORDER:
        src = os.path.join(args.dir, f"{name}-{args.theme}.svg")
        if not os.path.exists(src):
            print(f"  skip {name}")
            continue
        svg = open(src, encoding="utf-8").read()
        w, h = size_of(svg)
        posed = svg.replace(
            "</style>", f"*{{animation-delay:-{args.pose}s !important}}</style>")
        ps = os.path.join(tmp, f"{name}.svg")
        with open(ps, "w", encoding="utf-8") as fh:
            fh.write(posed)
        png = os.path.join(tmp, f"{name}.png")
        if os.path.exists(png):
            os.remove(png)
        subprocess.run(
            [edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={w},{h}", "--virtual-time-budget=2500",
             f"--screenshot={os.path.abspath(png)}",
             "file:///" + os.path.abspath(ps).replace("\\", "/").replace(" ", "%20")],
            capture_output=True, timeout=180)
        if not os.path.exists(png):
            print(f"  {name}: render failed")
            continue
        im = Image.open(png).convert("RGB")
        tiles.append((name, im))
        print(f"  {name:<10} {im.width} x {im.height}")

    if not tiles:
        raise SystemExit("nothing rendered")

    width = max(im.width for _, im in tiles) + PAD * 2
    height = PAD * 2 + sum(im.height for _, im in tiles) + GAP * (len(tiles) - 1)
    bg = (7, 9, 11) if args.theme == "dark" else (255, 255, 255)
    page = Image.new("RGB", (width, height), bg)

    y = PAD
    for _, im in tiles:
        page.paste(im, ((width - im.width) // 2, y))
        y += im.height + GAP

    page.save(args.out)
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB, "
          f"{width} x {height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
