#!/usr/bin/env python3
"""Render an SVG or HTML file to PNG with headless Edge, optionally posed at a
given point in the animation loop. Review helper."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def edge() -> str:
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    p = shutil.which("msedge") or shutil.which("chrome")
    if not p:
        raise SystemExit("no Edge/Chrome found")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--pose", type=float, default=None,
                    help="seconds into the loop to freeze at")
    ap.add_argument("--w", type=int, default=None)
    ap.add_argument("--h", type=int, default=None)
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    w, h = args.w, args.h

    if args.pose is not None and src.endswith(".svg"):
        txt = open(src, encoding="utf-8").read()
        if w is None:
            w = round(float(re.search(r'<svg[^>]*\swidth="([\d.]+)"', txt).group(1)))
        if h is None:
            h = round(float(re.search(r'<svg[^>]*\sheight="([\d.]+)"', txt).group(1)))
        posed = txt.replace(
            "</style>", f"*{{animation-delay:-{args.pose}s !important}}</style>")
        src = os.path.join(os.path.dirname(src), "_posed_tmp.svg")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(posed)

    if w is None or h is None:
        raise SystemExit("give --w/--h for html, or use --pose on an svg")

    out = os.path.abspath(args.out)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(
        [edge(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={w},{h}", "--virtual-time-budget=2500",
         f"--screenshot={out}",
         "file:///" + src.replace("\\", "/").replace(" ", "%20")],
        capture_output=True, timeout=200)
    if src.endswith("_posed_tmp.svg"):
        os.remove(src)
    print(f"{out}  {'ok' if os.path.exists(out) else 'FAILED'}  ({w}x{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
