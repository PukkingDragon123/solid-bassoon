#!/usr/bin/env python3
"""Drop a generated image into the app at the exact size the app expects.

    python3 tools/install_ai_asset.py props/buddha ~/Downloads/buddha.png

Cover-crops to the target aspect, resizes, preserves alpha where the manifest
says the asset needs it, and writes to assets/<key>.png.  Run with no
arguments to list the keys and their prompts.
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "tools", "ai-assets.json")


def load():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def install(key: str, src: str) -> str:
    data = load()
    spec = data["assets"].get(key)
    if spec is None:
        raise SystemExit(f"unknown key {key!r} — run with no arguments to list them")

    tw, th = spec["size"]
    img = Image.open(src)
    img = img.convert("RGBA" if spec["alpha"] else "RGB")

    # cover-crop to the target aspect, then resize
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    nw, nh = max(tw, round(sw * scale)), max(th, round(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    img = img.crop((left, top, left + tw, top + th))

    if spec["alpha"] and img.mode != "RGBA":
        img = img.convert("RGBA")

    out = os.path.join(ROOT, "assets", key + ".png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, optimize=True)
    return out


def main(argv):
    data = load()
    if len(argv) < 2:
        print(f"{'key':24s} {'size':>12s}  alpha  aspect")
        for key, spec in data["assets"].items():
            print(f"{key:24s} {str(tuple(spec['size'])):>12s}  {str(spec['alpha']):5s}  {spec['aspect_ratio']}")
        print("\nStyle prefix for every prompt:\n  " + data["style"])
        print("\nUsage: python3 tools/install_ai_asset.py <key> <image-file>")
        return 0
    if len(argv) < 3:
        print(data["assets"][argv[1]]["prompt"])
        return 0
    print("wrote", install(argv[1], argv[2]))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except BrokenPipeError:
        # piping the listing into head is normal; don't spew a traceback
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(0)
