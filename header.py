#!/usr/bin/env python3
"""
Render a profile header card as a self-contained SVG.

The avatar is downloaded and inlined as a data URI, because GitHub proxies
README images through Camo and an SVG referencing an external bitmap simply
renders empty. Language shares come from the real GitHub API byte counts, not
from a guess.

Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import urllib.request

API = "https://api.github.com"

# GitHub's own language colours, so the dots match what people expect
LANG_COLOUR = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "HTML": "#E34C26",
    "Shell": "#89E051", "R": "#198CE7", "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6", "C": "#555555", "C++": "#F34B7D",
    "Java": "#B07219", "Rust": "#DEA584", "Go": "#00ADD8", "CSS": "#563D7C",
    "Julia": "#A270BA", "MATLAB": "#E16737", "Nextflow": "#3AC486",
}

W, H = 880, 214
PAD = 30
AV_R = 44
AV_CX = PAD + 22 + AV_R
TX = AV_CX + AV_R + 30

THEMES = {
    "dark": {
        "bg": "#07090B", "card": "#0C1116", "edge": "#1E2831",
        "ink": "#F2F5F8", "muted": "#A3ADB9", "faint": "#78828E",
        "dry": "#E455C0", "wet": "#2FD98A",
        "pill": "#121A21", "pill_edge": "#22303B", "ring": "#2FD98A",
    },
    "light": {
        "bg": "#FFFFFF", "card": "#FBFBF9", "edge": "#E2E0D9",
        "ink": "#12161B", "muted": "#454C55", "faint": "#5F6771",
        "dry": "#A81E8C", "wet": "#0F6E44",
        "pill": "#FFFFFF", "pill_edge": "#DAD7CF", "ring": "#0F6E44",
        # a light ground shows the wash far more than a dark one does
        "wash": 0.42,
    },
}


CACHE = "dist/.profile-cache.json"


def api(path: str):
    """Authenticated when a token is around: unauthenticated GitHub allows only
    60 requests an hour, and this script makes one per repository."""
    hdrs = {"User-Agent": "profile-header/1.0"}
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        hdrs["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, headers=hdrs)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def avatar_data_uri(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-header/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        mime = r.headers.get_content_type() or "image/png"
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def gather(user: str):
    """Fetch profile and language data, caching the result.

    A failed language call used to be swallowed, which produced a header with
    no language pills and still reported success. Now any failure falls back to
    the last good cache, and if there is no cache it stops rather than shipping
    a header that is quietly missing half its content.
    """
    try:
        u = api(f"/users/{user}")
        repos = api(f"/users/{user}/repos?per_page=100")
        totals: dict[str, int] = {}
        missing = []
        for r in repos:
            if r.get("fork"):
                continue
            try:
                for k, v in api(f"/repos/{user}/{r['name']}/languages").items():
                    totals[k] = totals.get(k, 0) + int(v)
            except Exception as exc:                       # noqa: BLE001
                missing.append(f"{r['name']} ({exc})")
        if missing:
            raise RuntimeError("language lookup failed for: " + ", ".join(missing))
        if not totals:
            raise RuntimeError("no language data returned")
        payload = {"user": u, "repo_count": u.get("public_repos", len(repos)),
                   "totals": totals}
        os.makedirs(os.path.dirname(CACHE) or ".", exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
    except Exception as exc:                               # noqa: BLE001
        if not os.path.exists(CACHE):
            raise SystemExit(f"GitHub API failed and no cache to fall back on: {exc}")
        print(f"!! API failed ({exc})")
        print(f"!! falling back to {CACHE}")
        payload = json.load(open(CACHE, encoding="utf-8"))
        u, totals = payload["user"], payload["totals"]

    grand = sum(totals.values()) or 1
    langs = [(k, v * 100.0 / grand)
             for k, v in sorted(totals.items(), key=lambda kv: -kv[1])]
    return u, u.get("public_repos", 0), langs


def text_w(s: str, size: float) -> float:
    """Monospace advance, near enough for pill sizing."""
    return len(s) * size * 0.6


# 16x16 line icons, drawn rather than pulled in: an SVG that references an
# external icon set renders empty once GitHub proxies it.
ICONS = {
    "org": ('<path d="M2 14V3.1h5.5V14M8.7 14V6.5H14V14M1 14h14" '
            'fill="none" stroke="currentColor" stroke-width="1.15" '
            'stroke-linejoin="round"/>'
            '<path d="M3.5 5.3h1M5.4 5.3h1M3.5 7.6h1M5.4 7.6h1M3.5 9.9h1M5.4 9.9h1'
            'M10.2 8.7h1M12.1 8.7h1M10.2 11h1M12.1 11h1" '
            'stroke="currentColor" stroke-width="1.05" stroke-linecap="round"/>'),
    "loc": ('<path d="M8 14.6s4.5-4.5 4.5-7.8a4.5 4.5 0 1 0-9 0c0 3.3 4.5 7.8 4.5 7.8Z" '
            'fill="none" stroke="currentColor" stroke-width="1.15" '
            'stroke-linejoin="round"/>'
            '<circle cx="8" cy="6.6" r="1.75" fill="none" stroke="currentColor" '
            'stroke-width="1.15"/>'),
    "repo": ('<path d="M3 2.4h8.5a1 1 0 0 1 1 1v10.2H4.4A1.4 1.4 0 0 1 3 12.2V2.4Z" '
             'fill="none" stroke="currentColor" stroke-width="1.15" '
             'stroke-linejoin="round"/>'
             '<path d="M3 11.6h9.5" fill="none" stroke="currentColor" '
             'stroke-width="1.15"/>'),
}
ICON_PX = 12.5

# Language marks, simplified to read at 13px. Drawn here for the same reason as
# the meta icons: an external icon set will not load inside a README SVG.
LANG_ICON = {
    "Python": (
        '<path d="M8.1 1.1c-.7 0-1.4.06-2 .17-1.7.3-2 .93-2 2.1v1.5h4v.5H2.6'
        'c-1.2 0-2.2.7-2.5 2-.35 1.6-.37 2.5 0 4.1.28 1.2.95 2 2.1 2h1.4v-1.8'
        'c0-1.4 1.2-2.6 2.6-2.6h4c1.1 0 2-.9 2-2V3.4c0-1.1-.9-1.9-2-2.1'
        '-.7-.1-1.4-.17-2.1-.17ZM5.9 2.4a.78.78 0 1 1 0 1.56.78.78 0 0 1 0-1.56Z" '
        'fill="#3776AB"/>'
        '<path d="M7.9 14.9c.7 0 1.4-.06 2-.17 1.7-.3 2-.93 2-2.1v-1.5h-4v-.5h5.5'
        'c1.2 0 2.2-.7 2.5-2 .35-1.6.37-2.5 0-4.1-.28-1.2-.95-2-2.1-2h-1.4v1.8'
        'c0 1.4-1.2 2.6-2.6 2.6h-4c-1.1 0-2 .9-2 2v3.4c0 1.1.9 1.9 2 2.1'
        '.7.1 1.4.17 2.1.17ZM10.1 13.6a.78.78 0 1 1 0-1.56.78.78 0 0 1 0 1.56Z" '
        'fill="#FFD343"/>'),
    # filled crescents vanish at this size, so the rings are stroked instead
    "Jupyter Notebook": (
        '<circle cx="8" cy="2.4" r="1.55" fill="#F37726"/>'
        '<path d="M2.5 6.1Q8 10.6 13.5 6.1" fill="none" stroke="#F37726" '
        'stroke-width="1.9" stroke-linecap="round"/>'
        '<path d="M2.5 11.7Q8 7.2 13.5 11.7" fill="none" stroke="#F37726" '
        'stroke-width="1.9" stroke-linecap="round"/>'
        '<circle cx="3.0" cy="13.7" r="1.35" fill="#9E9E9E"/>'),
    "HTML": (
        '<path d="M2.4 1.4h11.2l-1.02 11.3L8 14.6l-4.58-1.9z" fill="#E34C26"/>'
        '<path d="M8 2.6v11l3.6-1.5.83-9.5z" fill="#F06529"/>'
        '<path d="M4.6 4.3h6.8l-.13 1.5H6.2l.1 1.5h4.86l-.4 4.4L8 12.5l-2.76-.8'
        '-.19-2.1h1.5l.1 1.05L8 11l1.36-.36.14-1.6H4.98z" fill="#EBEBEB"/>'),
    "Shell": (
        '<rect x="1.3" y="2.6" width="13.4" height="10.8" rx="1.8" fill="none" '
        'stroke="#89E051" stroke-width="1.2"/>'
        '<path d="M4.3 6.1 6.8 8.3 4.3 10.5" fill="none" stroke="#89E051" '
        'stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M8.3 10.7h3.4" fill="none" stroke="#89E051" stroke-width="1.3" '
        'stroke-linecap="round"/>'),
    "R": ('<ellipse cx="8" cy="7.2" rx="6.6" ry="4.6" fill="none" stroke="#198CE7" '
          'stroke-width="1.3"/>'
          '<path d="M6.2 11.6V4.9h2.6a1.9 1.9 0 0 1 0 3.8H7.2l2.6 2.9" fill="none" '
          'stroke="#198CE7" stroke-width="1.4" stroke-linejoin="round"/>'),
}
LANG_PX = 13.0


def build(theme: str, u: dict, langs: list, avatar: str,
          tagline: str, meta: list) -> str:
    t = THEMES[theme]
    ws = t.get("wash", 1.0)          # wash strength, per theme

    def op(v: float) -> str:
        return f"{v * ws:.3f}"
    name = u.get("name") or u["login"]
    o: list[str] = []
    a = o.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" role="img" aria-label="Profile header for '
      f'@{html.escape(u["login"])}">')

    a("<defs>")
    a(f'<clipPath id="av"><circle cx="{AV_CX}" cy="{H/2:.0f}" r="{AV_R}"/></clipPath>')
    a(f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity=".55"/>'
      f'<stop offset=".5" stop-color="{t["edge"]}" stop-opacity=".9"/>'
      f'<stop offset="1" stop-color="{t["dry"]}" stop-opacity=".55"/></linearGradient>')
    a(f'<clipPath id="cardclip">'
      f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17"/></clipPath>')
    a(f'<radialGradient id="au1" cx=".5" cy=".5" r=".5">'
      f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity="{op(.30)}"/>'
      f'<stop offset="1" stop-color="{t["wet"]}" stop-opacity="0"/></radialGradient>')
    a(f'<radialGradient id="au2" cx=".5" cy=".5" r=".5">'
      f'<stop offset="0" stop-color="{t["dry"]}" stop-opacity="{op(.26)}"/>'
      f'<stop offset="1" stop-color="{t["dry"]}" stop-opacity="0"/></radialGradient>')
    # two counter-rotating gradient washes; where they cross the hue shifts,
    # which is what makes it read as motion rather than a static sheen
    a(f'<linearGradient id="wash1" gradientUnits="objectBoundingBox" '
      f'x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{t["wet"]}" stop-opacity="{op(.30)}"/>'
      f'<stop offset=".45" stop-color="{t["wet"]}" stop-opacity="0"/>'
      f'<stop offset=".62" stop-color="{t["dry"]}" stop-opacity="0"/>'
      f'<stop offset="1" stop-color="{t["dry"]}" stop-opacity="{op(.28)}"/>'
      f'<animateTransform attributeName="gradientTransform" type="rotate" '
      f'from="0 .5 .5" to="360 .5 .5" dur="26s" repeatCount="indefinite"/>'
      f'</linearGradient>')
    a(f'<linearGradient id="wash2" gradientUnits="objectBoundingBox" '
      f'x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{t["dry"]}" stop-opacity="{op(.22)}"/>'
      f'<stop offset=".5" stop-color="{t["wet"]}" stop-opacity="{op(.10)}"/>'
      f'<stop offset="1" stop-color="{t["dry"]}" stop-opacity="{op(.22)}"/>'
      f'<animateTransform attributeName="gradientTransform" type="rotate" '
      f'from="360 .5 .5" to="0 .5 .5" dur="37s" repeatCount="indefinite"/>'
      f'</linearGradient>')
    a(f'<linearGradient id="ringg" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{t["wet"]}"/>'
      f'<stop offset="1" stop-color="{t["dry"]}"/></linearGradient>')
    a("</defs>")

    a("<style>"
      f".n{{font:700 40px ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace;fill:{t['ink']};letter-spacing:-.02em}}"
      f".h{{font:500 12px ui-monospace,Menlo,Consolas,monospace;fill:{t['faint']};letter-spacing:.34em}}"
      f".tg{{font:400 14px ui-monospace,Menlo,Consolas,monospace;fill:{t['muted']};letter-spacing:.01em}}"
      f".mt{{font:500 10.5px ui-monospace,Menlo,Consolas,monospace;fill:{t['faint']};letter-spacing:.1em}}"
      f".pl{{font:500 11px ui-monospace,Menlo,Consolas,monospace;fill:{t['muted']}}}"
      f".pc{{font:500 11px ui-monospace,Menlo,Consolas,monospace;fill:{t['faint']}}}"
      "@keyframes drift{0%,100%{transform:translate(0,0)}50%{transform:translate(26px,-12px)}}"
      "@keyframes drift2{0%,100%{transform:translate(0,0)}50%{transform:translate(-30px,10px)}}"
      ".a1{animation:drift 15s ease-in-out infinite}"
      ".a2{animation:drift2 19s ease-in-out infinite}"
      "@keyframes spin{to{transform:rotate(360deg)}}"
      f".rg{{animation:spin 26s linear infinite;transform-origin:{AV_CX}px {H/2:.0f}px}}"
      "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
      "</style>")

    a(f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>')
    # every background layer is clipped to the card, or the blobs bleed past
    # the rounded corners
    a('<g clip-path="url(#cardclip)">')
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" fill="{t["card"]}"/>')
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" fill="url(#wash1)"/>')
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" fill="url(#wash2)"/>')
    a(f'<ellipse class="a1" cx="{W*.30:.0f}" cy="{H*.30:.0f}" rx="300" ry="150" fill="url(#au1)"/>')
    a(f'<ellipse class="a2" cx="{W*.78:.0f}" cy="{H*.74:.0f}" rx="320" ry="160" fill="url(#au2)"/>')
    a("</g>")
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" '
      f'stroke="url(#edge)" stroke-width="1.4"/>')

    # avatar with a slowly rotating gradient ring
    a(f'<circle class="rg" cx="{AV_CX}" cy="{H/2:.0f}" r="{AV_R+5}" fill="none" '
      f'stroke="url(#ringg)" stroke-width="2" stroke-dasharray="118 26" opacity=".9"/>')
    a(f'<circle cx="{AV_CX}" cy="{H/2:.0f}" r="{AV_R+1.5}" fill="{t["card"]}"/>')
    a(f'<image href="{avatar}" x="{AV_CX-AV_R}" y="{H/2-AV_R:.0f}" '
      f'width="{AV_R*2}" height="{AV_R*2}" clip-path="url(#av)" '
      f'preserveAspectRatio="xMidYMid slice"/>')

    # identity block
    a(f'<text class="h" x="{TX}" y="60">@{html.escape(u["login"]).upper()}</text>')
    a(f'<text class="n" x="{TX}" y="102">{html.escape(name)}</text>')
    a(f'<text class="tg" x="{TX}" y="126">{html.escape(tagline)}</text>')

    # language pills, real shares
    px = TX
    lsc = LANG_PX / 16.0
    for lang, share in langs[:4]:
        label = lang if len(lang) <= 16 else lang[:15] + "…"
        pct = f"{share:.1f}%"
        icon = LANG_ICON.get(lang)
        lead = LANG_PX + 8 if icon else 20        # logo needs more room than a dot
        w = 11 + lead + text_w(label, 11) + 10 + text_w(pct, 11) + 14
        a(f'<rect x="{px:.0f}" y="146" width="{w:.0f}" height="26" rx="13" '
          f'fill="{t["pill"]}" stroke="{t["pill_edge"]}" stroke-width="1"/>')
        if icon:
            a(f'<g transform="translate({px+10:.1f} {159 - LANG_PX/2:.1f}) '
              f'scale({lsc:.4f})">{icon}</g>')
            tx0 = px + 10 + lead
        else:
            a(f'<circle cx="{px+13:.0f}" cy="159" r="3.6" '
              f'fill="{LANG_COLOUR.get(lang, t["faint"])}"/>')
            tx0 = px + 22
        a(f'<text class="pl" x="{tx0:.0f}" y="163">{html.escape(label)}</text>')
        a(f'<text class="pc" x="{tx0+text_w(label,11)+8:.0f}" y="163">{pct}</text>')
        px += w + 8

    # meta strip: icon + label per item, laid out right-aligned as a block
    fs, gap, sep = 10.5, 6.0, 20.0
    widths = [ICON_PX + gap + text_w(txt, fs) for _, txt in meta]
    total = sum(widths) + sep * (len(meta) - 1)
    mx = W - PAD - total
    baseline = H - 22
    scale = ICON_PX / 16.0
    for (key, txt), wpx in zip(meta, widths):
        a(f'<g transform="translate({mx:.1f} {baseline - 9.6:.1f}) scale({scale:.4f})" '
          f'color="{t["faint"]}" opacity=".95">{ICONS[key]}</g>')
        a(f'<text class="mt" x="{mx + ICON_PX + gap:.1f}" y="{baseline}">'
          f'{html.escape(txt)}</text>')
        mx += wpx + sep
    a("</svg>")
    return "".join(o)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="kartic03")
    # in vitro, not in vivo: the bench work is cell culture, not animal work
    ap.add_argument(
        "--tagline",
        default="AI protein design → expression → in vitro validation")
    ap.add_argument("--out-dark", default="dist/header-dark.svg")
    ap.add_argument("--out-light", default="dist/header-light.svg")
    args = ap.parse_args()

    u, repo_count, langs = gather(args.user)
    avatar = avatar_data_uri(u["avatar_url"])   # not the API, so not rate-limited
    print(f"avatar inlined: {len(avatar)/1024:.0f} KB base64")
    print("languages: " + ", ".join(f"{k} {v:.1f}%" for k, v in langs[:5]))

    meta = []
    if u.get("company"):
        meta.append(("org", u["company"].lstrip("@")))
    if u.get("location"):
        meta.append(("loc", u["location"]))
    meta.append(("repo", f"{repo_count} repositories"))

    if not langs:
        raise SystemExit("refusing to write a header with no language pills")

    for path, theme in ((args.out_dark, "dark"), (args.out_light, "light")):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        svg = build(theme, u, langs, avatar, args.tagline, meta)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {path}  ({len(svg.encode('utf-8'))/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
