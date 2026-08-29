#!/usr/bin/env python3
"""Render every image asset the app ships with.

    python3 tools/render_assets.py            # everything
    python3 tools/render_assets.py gate slip  # only assets whose name matches

Output goes to assets/.  Each entry names the module function that draws it,
its output size, and whether it keeps an alpha channel.
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artgen import core, scenes, props  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

SCENE_W, SCENE_H = 1920, 1080
# Portrait plates for phones.  A 16:9 backdrop on a 9:19.5 screen loses two
# thirds of its width to the crop, so the tall scenes are composed separately
# rather than cropped.
PORT_W, PORT_H = 1100, 1500
PORT = dict(ground=PORT_H * 0.845, scale=PORT_W / 1150)

# name -> (callable, kwargs, alpha)  alpha: True keeps RGBA, False flattens
# to RGB, "L" writes a single-channel greyscale tile.
ASSETS = {
    "scenes/gate-sky":    (scenes.dusk_sky,     dict(w=SCENE_W, h=SCENE_H), False),
    "scenes/gate-far":    (scenes.gate_far,     dict(w=SCENE_W, h=SCENE_H), True),
    "scenes/gate-mid":    (scenes.gate_mid,     dict(w=SCENE_W, h=SCENE_H), True),
    "scenes/gate-near":   (scenes.gate_near,    dict(w=SCENE_W, h=SCENE_H), True),
    "scenes/hall-bg":     (scenes.hall_bg,      dict(w=SCENE_W, h=SCENE_H), False),
    "scenes/gate-sky-p":  (scenes.dusk_sky,     dict(w=PORT_W, h=PORT_H, **PORT), False),
    "scenes/gate-far-p":  (scenes.gate_far,     dict(w=PORT_W, h=PORT_H, **PORT), True),
    "scenes/gate-mid-p":  (scenes.gate_mid,     dict(w=PORT_W, h=PORT_H, **PORT), True),
    "scenes/gate-near-p": (scenes.gate_near,    dict(w=PORT_W, h=PORT_H, rail_span=0.30, **PORT), True),
    "scenes/hall-bg-p":   (scenes.hall_bg,      dict(w=PORT_W, h=PORT_H), False),
    # the cabinet turns on its side for phones: 4 across, 7 down
    "scenes/drawer-wall-p": (scenes.drawer_wall, dict(w=1000, h=1500, cols=4, rows=7), False),
    "scenes/hall-altar":  (scenes.hall_altar,   dict(w=1500, h=620), True),
    "scenes/hall-near":   (scenes.hall_near,    dict(w=SCENE_W, h=SCENE_H), True),
    "scenes/drawer-wall": (scenes.drawer_wall,  dict(w=1600, h=1000), False),
    "props/buddha":       (props.buddha_statue, dict(w=1000, h=1360), True),
    "props/censer":       (props.censer,        dict(w=900, h=620), True),
    "props/candle":       (props.candle,        dict(w=280, h=760), True),
    "props/incense":      (props.incense,       dict(w=340, h=920, lit=False), True),
    "props/incense-lit":  (props.incense,       dict(w=340, h=920, lit=True), True),
    "props/tube":         (props.siamsee_tube,  dict(w=680, h=1080), True),
    # split plates so the bundle can lag behind the cylinder while shaking
    "props/tube-body":    (props.siamsee_tube,  dict(w=680, h=1080, part="body"), True),
    "props/tube-sticks":  (props.siamsee_tube,  dict(w=680, h=1080, part="sticks"), True),
    "props/stick":        (props.siamsee_stick, dict(w=130, h=1000), True),
    "props/slip":         (props.slip,          dict(w=780, h=1180), True),
    "props/lotus":        (props.lotus,         dict(w=440, h=440), True),
    "props/bell":         (props.temple_bell,   dict(w=440, h=560), True),
    "props/kanok-corner": (props.kanok_corner,  dict(w=460, h=460), True),
    "fx/smoke":           (props.smoke_puff,    dict(w=256, h=256), True),
    "fx/ember":           (props.ember,         dict(w=160, h=160), True),
    "tex/grain":          (props.film_grain,    dict(size=256), "L"),
    "tex/paper":          (props.paper_tile,    dict(size=512), True),
}


def render_one(name):
    fn, kw, has_alpha = ASSETS[name]
    t0 = time.time()
    result = fn(**kw)
    if isinstance(result, tuple):
        rgbf, alpha = result
    else:
        rgbf, alpha = result, None
    img = core.to_pil(rgbf, alpha if has_alpha is True else None)
    if has_alpha == "L":
        # a noise tile has no colour and no alpha; greyscale is a third the size
        img = img.convert("L")
    elif not has_alpha and img.mode == "RGBA":
        img = img.convert("RGB")
    path = os.path.join(OUT, name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)
    kb = os.path.getsize(path) / 1024
    return f"{name:24s} {img.size[0]:>5d}x{img.size[1]:<5d} {kb:8.0f} KB  {time.time() - t0:5.1f}s"


def main(argv):
    names = [n for n in ASSETS if not argv or any(a in n for a in argv)]
    if not names:
        print("no assets matched", argv)
        return 1
    t0 = time.time()
    workers = min(len(names), max(1, (os.cpu_count() or 2)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for line in ex.map(render_one, names):
            print(line, flush=True)
    print(f"\n{len(names)} assets in {time.time() - t0:.1f}s -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
