#!/usr/bin/env python3
"""Regenerate every panel, then stack a review page. Standard library only."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

STEPS = [
    ("header",  ["header.py"],  True),     # profile, languages, avatar
    ("panels",  ["panels.py"],  True),     # live repository list
    ("shooter", ["shooter.py"], True),     # live contribution calendar
]


def run(args: list[str]) -> bool:
    t0 = time.time()
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    tail = (r.stdout or r.stderr).strip().splitlines()
    for line in tail[-2:]:
        print("   " + line)
    print(f"   {'ok' if r.returncode == 0 else 'FAILED'} in {time.time()-t0:.1f}s")
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="kartic03")
    ap.add_argument("--skip-preview", action="store_true")
    args = ap.parse_args()

    failed = []
    for name, cmd, takes_user in STEPS:
        print(f"-> {name}")
        if not run(cmd + (["--user", args.user] if takes_user else [])):
            failed.append(name)

    if not args.skip_preview and not failed:
        for theme in ("dark", "light"):
            print(f"-> page ({theme})")
            run(["preview.py", "--theme", theme, "--out", f"dist/page-{theme}.svg"])

    if failed:
        print("\nfailed: " + ", ".join(failed))
        return 1
    print("\nall panels rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
