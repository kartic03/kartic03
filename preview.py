#!/usr/bin/env python3
"""
Stack every panel into one tall SVG so the whole profile can be reviewed as a
page rather than as loose parts. This is a review aid, not something the README
uses: GitHub gets the individual panels.
"""

from __future__ import annotations

import argparse
import os
import re

ORDER = ["header", "code", "shooter", "footer"]
GAP = 18
PAD = 22


def dims(svg: str) -> tuple[float, float, float]:
    """Rendered width/height, plus the scale from viewBox units. A panel may
    declare a smaller width than its viewBox so it lines up with the others."""
    aw = float(re.search(r'<svg[^>]*\swidth="([\d.]+)"', svg).group(1))
    ah = float(re.search(r'<svg[^>]*\sheight="([\d.]+)"', svg).group(1))
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    scale = aw / float(m.group(1)) if m else 1.0
    return aw, ah, scale


def inner(svg: str) -> str:
    """Strip the outer <svg> wrapper, keeping everything inside."""
    body = svg[svg.index(">", svg.index("<svg")) + 1:]
    return body[: body.rindex("</svg>")]


def namespace(body: str, tag: str) -> str:
    """Every panel reuses ids like cc/eg/w1, so prefix them per panel."""
    ids = set(re.findall(r'\sid="([^"]+)"', body))
    for i in sorted(ids, key=len, reverse=True):
        body = body.replace(f'id="{i}"', f'id="{tag}_{i}"')
        body = body.replace(f"url(#{i})", f"url(#{tag}_{i})")
        body = body.replace(f'href="#{i}"', f'href="#{tag}_{i}"')
    # class names collide too, since each panel numbers its own rows
    classes = set(re.findall(r'\.([a-zA-Z][\w-]*)\s*\{', body))
    classes |= set(re.findall(r'@keyframes\s+([\w-]+)', body))
    for c in sorted(classes, key=len, reverse=True):
        body = re.sub(rf'\.{re.escape(c)}(?=[\s,{{:])', f".{tag}_{c}", body)
        body = re.sub(rf'@keyframes\s+{re.escape(c)}\b', f"@keyframes {tag}_{c}", body)
        body = re.sub(rf'animation:{re.escape(c)}\b', f"animation:{tag}_{c}", body)
        body = re.sub(rf'class="([^"]*\b){re.escape(c)}(\b[^"]*)"',
                      lambda m: f'class="{m.group(1)}{tag}_{c}{m.group(2)}"', body)
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="dark")
    ap.add_argument("--dir", default="dist")
    ap.add_argument("--out", default="dist/page-dark.svg")
    args = ap.parse_args()

    parts, total_h, max_w = [], PAD, 0
    for name in ORDER:
        p = os.path.join(args.dir, f"{name}-{args.theme}.svg")
        if not os.path.exists(p):
            print(f"  skip {name} (missing)")
            continue
        svg = open(p, encoding="utf-8").read()
        w, h, sc = dims(svg)
        max_w = max(max_w, w)
        parts.append((name, w, h, sc, namespace(inner(svg), name)))
        total_h += h + GAP
        print(f"  {name:<10} {w:.0f} x {h:.0f}"
              + (f"  (scaled {sc:.3f})" if abs(sc - 1) > 1e-6 else ""))
    total_h += PAD - GAP

    W = max_w + PAD * 2
    bg = "#07090B" if args.theme == "dark" else "#FFFFFF"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{total_h}" '
           f'viewBox="0 0 {W} {total_h}">',
           f'<rect width="{W}" height="{total_h}" fill="{bg}"/>']
    y = PAD
    for name, w, h, sc, body in parts:
        tf = f"translate({(W - w) / 2:.1f} {y:.1f})"
        if abs(sc - 1) > 1e-6:
            tf += f" scale({sc:.5f})"
        out.append(f'<g transform="{tf}">{body}</g>')
        y += h + GAP
    out.append("</svg>")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("".join(out))
    print(f"wrote {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB, "
          f"{W} x {total_h})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
