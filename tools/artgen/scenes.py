"""Full scene renders — the backdrops the app walks the visitor through."""
from __future__ import annotations

import math
import numpy as np
from . import core, thai, paint
from .core import Shape, blur_a, rgb, quad, mirror_x, radial_falloff
from .paint import Painter


def _shape(w, h, polys, ss=3):
    s = Shape(w, h, ss)
    for p in polys:
        s.polygon(p)
    return s.mask()


# ==========================================================================
# ท้องฟ้ายามพลบ — the dusk sky the whole entrance sits against
# ==========================================================================


def dusk_sky(w, h, ground=None, scale=None):
    S = scale or w / 1560.0
    ground = ground if ground is not None else h * 0.830
    # keep the band of colour anchored to the horizon rather than the frame
    hz = max(0.30, min(0.95, (ground - 103 * S) / h))
    stops = [(0.00, "#0a1030"), (hz * 0.30, "#1c2050"), (hz * 0.60, "#4a2f5e"), (hz * 0.845, "#96455a"),
             (hz, "#d9743f"), (min(hz + (1 - hz) * 0.55, 0.995), "#f0a44e"), (1.00, "#f7cb84")]
    sky = core.linear_gradient(w, h, stops)

    # stars, thinning out toward the glow on the horizon
    rs = np.random.RandomState(7)
    stars = np.zeros((h, w), dtype=np.float32)
    n = int(w * h / 2600)
    ys = (rs.power(2.2, n) * h * hz * 0.84).astype(np.int32)
    xs = rs.randint(0, w, n)
    mag = rs.power(3.0, n).astype(np.float32)
    stars[ys, xs] = mag
    stars = blur_a(stars, 1.1) * 2.2
    twinkle = np.zeros((h, w), dtype=np.float32)
    k = n // 26
    twinkle[ys[:k], xs[:k]] = mag[:k]
    sky = core.screen(sky, np.ones_like(sky) * rgb("#dfe8ff"), stars)
    sky = core.screen(sky, np.ones_like(sky) * rgb("#ffffff"), blur_a(twinkle, 4.0) * 1.6)

    # clouds: warped fractal bands, underlit by the set sun
    base = core.fbm(w, h, 5, 6, seed=21)
    wx = (core.fbm(w, h, 3, 4, seed=33) - 0.5) * w * 0.05
    wy = (core.fbm(w, h, 3, 4, seed=44) - 0.5) * h * 0.03
    cl = core.warp_field(base, wx, wy)
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32) / h
    band = np.clip(np.sin(yy * 7.0 + cl * 5.0) * 0.5 + 0.5, 0, 1) ** 1.6
    cover = np.clip((cl - 0.44) * 3.0, 0, 1) * band
    cover *= np.clip(1.0 - np.abs(yy - hz * 0.72) * 2.0, 0, 1) ** 0.8
    lit = np.clip(np.gradient(blur_a(cover, 9))[0] * -22.0, 0, 1)
    sky = core.over(sky, core.linear_gradient(w, h, [(0.0, "#3a3560"), (0.55, "#7a4a63"), (1.0, "#c07a55")]), cover * 0.72)
    sky = core.add_light(sky, rgb("#ffb367"), lit * cover * 0.9, 1.0)

    # moon behind thin cloud
    mx, my, mr = w * 0.755, h * hz * 0.21, min(h, w) * 0.042
    disc = Shape(w, h).ellipse((mx - mr, my - mr, mx + mr, my + mr)).mask()
    sky = core.add_light(sky, rgb("#fff3d8"), blur_a(disc, mr * 3.4) * 0.55, 1.0)
    sky = core.over(sky, np.ones_like(sky) * rgb("#fdf6e2"), disc * (1.0 - cover * 0.55))

    # horizon haze
    haze = np.clip((yy - hz * 0.76) / max(1 - hz * 0.76, 1e-3), 0, 1) ** 1.5
    sky = core.add_light(sky, rgb("#ff9a4d"), haze * 0.22, 1.0)
    return sky


# ==========================================================================
# ฉากที่ ๑ — the ubosot seen from the foot of its stairs
# ==========================================================================


def gate_far(w, h, ground=None, scale=None):
    """Distant prang, chedi and treeline — the parallax back plate."""
    S = scale or w / 1560.0
    ground = ground if ground is not None else h * 0.830
    img = core.canvas(w, h, "#000000")
    p = Painter(img, light=(-0.6, -0.8), depth_scale=w / 900.0)
    hz = ground - 103 * S  # horizon, just behind the hall's platform
    masks = []

    far_mat = paint.Material(
        [(0.0, "#6a4b6e"), (0.45, "#4a3355"), (1.0, "#2a1c36")],
        spec=0.06, rim=0.30, rim_color="#ffb877", ambient=0.5, depth=26, grain=0.1, seam=0.2,
        shade_mix=0.6, value=0.4,
    )
    for cxr, sc in ((0.135, 0.85), (0.885, 0.72)):
        m = _shape(w, h, thai.prang(w * cxr, hz, 160 * S * sc, 430 * S * sc))
        p.part(m, far_mat, seed=int(cxr * 100), contact=0.0)
        masks.append(m)
    for cxr, sc in ((0.255, 0.55), (0.775, 0.62), (0.055, 0.42)):
        m = _shape(w, h, thai.chedi(w * cxr, hz, 140 * S * sc, 450 * S * sc))
        p.part(m, far_mat, seed=int(cxr * 200), contact=0.0)
        masks.append(m)

    # treeline: a lumpy noise horizon
    tree = np.zeros((h, w), dtype=np.float32)
    xs = np.arange(w, dtype=np.float32)
    prof = (
        np.sin(xs / w * 26) * 0.22 + np.sin(xs / w * 61 + 1.3) * 0.13
        + np.sin(xs / w * 137 + 2.6) * 0.07 + core.fbm(w, 8, 7, 4, 12)[0] * 0.6
    )
    top = hz - 38 * S - prof * 60 * S
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
    tree = np.clip((yy - top[None, :]) * 0.9, 0, 1)
    tm = blur_a(tree, 2.0)
    p.part(
        tm,
        paint.Material([(0.0, "#3d2a44"), (0.5, "#2a1d31"), (1.0, "#17101c")],
                       spec=0.0, rim=0.22, rim_color="#e08a56", ambient=0.62, depth=40, grain=0.24,
                       grain_cells=30, seam=0.0, shade_mix=0.5, value=0.35),
        seed=5, contact=0.0,
    )
    masks.append(tm)

    a = np.zeros((h, w), dtype=np.float32)
    for m in masks:
        a = np.maximum(a, m)
    # aerial perspective: everything distant sinks toward the sky's colour
    p.img = core.over(p.img, np.ones_like(p.img) * rgb("#7a4a63"), a * 0.30)
    return p.img, blur_a(a, 0.7)


def _ubosot(p: Painter, w, h, cx, scale, glow_out, ground):
    """The ordination hall itself — roof tiers, gable, columns, doorway.

    Everything is placed in units of `scale` measured up from `ground`.
    Tying heights to the frame instead would stretch the building whenever
    the aspect ratio changed.
    """
    S = scale
    masks = []

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    base_y = ground
    wall_top = base_y - 285 * S
    wall_hw = 340 * S

    # --- platform ---------------------------------------------------------
    add(_shape(w, h, [[(cx - wall_hw * 1.30, base_y), (cx + wall_hw * 1.30, base_y),
                       (cx + wall_hw * 1.24, base_y - 26 * S), (cx - wall_hw * 1.24, base_y - 26 * S)]]),
        paint.STONE_WARM, seed=1, contact=0.0)

    # --- wall + doorway ---------------------------------------------------
    add(_shape(w, h, [[(cx - wall_hw, base_y - 22 * S), (cx + wall_hw, base_y - 22 * S),
                       (cx + wall_hw, wall_top), (cx - wall_hw, wall_top)]]),
        paint.STONE_WARM, seed=2, contact=0.4)

    door_hw, door_top = 74 * S, wall_top + 42 * S
    door = _shape(w, h, [
        [(cx - door_hw, base_y - 22 * S), (cx + door_hw, base_y - 22 * S), (cx + door_hw, door_top + 30 * S)]
        + list(reversed(quad((cx - door_hw, door_top + 30 * S), (cx, door_top - 34 * S), (cx + door_hw, door_top + 30 * S), 30)))
    ])
    p.darken(door, 0.94)
    # warm light spilling out of the hall
    p.img = core.add_light(p.img, rgb("#ffa83c"), blur_a(door, 40 * S) * 0.85 * glow_out, 1.0)
    p.img = core.add_light(p.img, rgb("#ffd27a"), door * 0.42 * glow_out, 1.0)
    masks.append(door)

    # กลอนประตู — the door leaves themselves, lit from within
    leafm = _shape(w, h, [
        [(cx - door_hw + 5 * S, base_y - 22 * S), (cx + door_hw - 5 * S, base_y - 22 * S), (cx + door_hw - 5 * S, door_top + 26 * S)]
        + list(reversed(quad((cx - door_hw + 5 * S, door_top + 26 * S), (cx, door_top - 26 * S), (cx + door_hw - 5 * S, door_top + 26 * S), 30)))
    ])
    add(leafm, paint.GOLD_DEEP, seed=4, depth=8, contact=0.0)
    panel = Shape(w, h)
    for sgn in (-1, 1):
        for j in range(3):
            py0 = door_top + (54 + j * 96) * S
            panel.rect((cx + sgn * 8 * S - (0 if sgn > 0 else 54 * S), py0,
                        cx + sgn * 8 * S + (54 * S if sgn > 0 else 0), py0 + 74 * S), radius=6 * S)
    p.darken(blur_a(panel.mask() * leafm, 2.2 * S), 0.34)
    add(_shape(w, h, thai.kanok(cx - door_hw * 0.5, door_top + 100 * S, 40 * S, -90, depth=1)
               + thai.kanok(cx + door_hw * 0.5, door_top + 100 * S, 40 * S, -90, depth=1, flip=True)) * leafm,
        paint.GOLD, seed=5, depth=3, contact=0.2)
    seam = Shape(w, h).line([(cx, door_top - 20 * S), (cx, base_y - 22 * S)], width=max(2.0, 5 * S)).mask() * leafm
    p.img = core.add_light(p.img, rgb("#ffd489"), blur_a(seam, 9 * S) * 1.0 * glow_out, 1.0)

    # gilded door frame
    fr = _shape(w, h, [
        [(cx - door_hw - 15 * S, base_y - 22 * S), (cx + door_hw + 15 * S, base_y - 22 * S), (cx + door_hw + 15 * S, door_top + 30 * S)]
        + list(reversed(quad((cx - door_hw - 15 * S, door_top + 30 * S), (cx, door_top - 52 * S), (cx + door_hw + 15 * S, door_top + 30 * S), 30)))
    ]) * (1 - door)
    add(fr, paint.GOLD, seed=3, depth=6, contact=0.3)

    # side windows, shuttered and gilded
    for sgn in (-1, 1):
        for k in (0.44, 0.78):
            wx = cx + sgn * wall_hw * k
            wy0, wy1, whw = wall_top + 74 * S, base_y - 88 * S, 36 * S
            frame = _shape(w, h, [[(wx - whw - 11 * S, wy0 - 40 * S), (wx + whw + 11 * S, wy0 - 40 * S),
                                   (wx + whw + 11 * S, wy1 + 10 * S), (wx - whw - 11 * S, wy1 + 10 * S)]])
            add(frame, paint.GOLD_DEEP, seed=int(wx) % 90, depth=6, contact=0.35)
            # little gable over each window
            add(_shape(w, h, [[(wx - whw - 14 * S, wy0 - 36 * S), (wx + whw + 14 * S, wy0 - 36 * S), (wx, wy0 - 84 * S)]]),
                paint.GOLD, seed=int(wx) % 91, depth=5, contact=0.3)
            shut = _shape(w, h, [[(wx - whw, wy0), (wx + whw, wy0), (wx + whw, wy1), (wx - whw, wy1)]])
            add(shut, paint.LACQUER_RED, seed=int(wx) % 70, depth=7, contact=0.3)
            add(_shape(w, h, thai.kanok(wx, wy0 + 56 * S, 34 * S, -90, depth=1)) * shut,
                paint.GOLD, seed=int(wx) % 71, depth=3, contact=0.2)
            gap = Shape(w, h).line([(wx, wy0), (wx, wy1)], width=max(1.5, 2.4 * S)).mask() * shut
            p.darken(blur_a(gap, 1.6 * S), 0.55)

    # --- columns along the veranda ---------------------------------------
    for sgn in (-1, 1):
        for k in (1.02, 1.20):
            colx = cx + sgn * wall_hw * k
            polys = thai.column(colx, wall_top + 30 * S, base_y - 22 * S, 42 * S)
            add(_shape(w, h, polys), paint.STONE_WARM, seed=int(colx) % 60, depth=10, contact=0.4)
            add(_shape(w, h, thai.lotus_capital(colx, wall_top + 34 * S, 46 * S, 42 * S)),
                paint.GOLD_DEEP, seed=int(colx) % 40, depth=7, contact=0.3)

    # --- roof tiers, lowest first so the upper ones overlap ---------------
    tiers = ((base_y - 377 * S, 505 * S, 150 * S), (base_y - 465 * S, 428 * S, 155 * S), (base_y - 556 * S, 345 * S, 162 * S))
    for i, (ridge_y, half_w, th) in enumerate(tiers):
        field, bl, br = thai.roof_tier(cx, ridge_y, half_w, th, sweep=0.16)
        rm = add(_shape(w, h, [field]), paint.ROOF_TILE, seed=50 + i, depth=26, contact=0.5)
        # กระเบื้องว่าว — diamond tile courses, the texture that stops the
        # roof reading as moulded plastic
        rows, cols = Shape(w, h), Shape(w, h)
        nrow = 13
        for r in range(1, nrow):
            t = r / nrow
            rows.line([(cx - half_w * (0.16 + 0.94 * t), ridge_y + th * t + 8 * S * t),
                       (cx, ridge_y + th * t * 0.84),
                       (cx + half_w * (0.16 + 0.94 * t), ridge_y + th * t + 8 * S * t)], width=max(1.2, 1.7 * S))
        for c in range(-11, 12):
            fx = c / 11.0
            cols.line([(cx + half_w * fx * 0.62, ridge_y + 2 * S), (cx + half_w * fx, ridge_y + th + 10 * S)],
                      width=max(1.0, 1.2 * S))
        p.darken(blur_a(rows.mask() * rm, 1.4 * S), 0.34)
        p.darken(blur_a(cols.mask() * rm, 1.2 * S), 0.11)
        p.img = core.add_light(p.img, rgb("#ffb877"), blur_a(rows.mask() * rm, 2.6 * S) * 0.10, 1.0)
        # green glazed border along the barge boards
        edge = Shape(w, h)
        edge.line(bl, width=13 * S)
        edge.line(br, width=13 * S)
        add(edge.mask(), paint.ROOF_GREEN, seed=60 + i, depth=6, contact=0.3)
        # ใบระกา + หางหงส์ + ช่อฟ้า
        add(_shape(w, h, thai.bai_raka(cx, ridge_y, cx - half_w, ridge_y + th - th * 0.16, 9, 26 * S)
                   + thai.bai_raka(cx, ridge_y, cx + half_w, ridge_y + th - th * 0.16, 9, 26 * S, flip=True)),
            paint.GOLD_DEEP, seed=70 + i, depth=5, contact=0.25)
        add(_shape(w, h, thai.hang_hong(cx - half_w, ridge_y + th - th * 0.16, 62 * S)
                   + thai.hang_hong(cx + half_w, ridge_y + th - th * 0.16, 62 * S, flip=True)),
            paint.GOLD, seed=80 + i, depth=6, contact=0.25)
        if i == len(tiers) - 1:
            add(_shape(w, h, thai.chofa(cx, ridge_y + 6 * S, 168 * S)), paint.GOLD, seed=90, depth=7, contact=0.2)

    # --- หน้าบัน: the gilded pediment ------------------------------------
    g_ridge, g_hw, g_h = base_y - 556 * S, 345 * S, 162 * S
    gm = _shape(w, h, [thai.gable(cx, g_ridge + 14 * S, g_hw * 0.80, g_h * 0.92)])
    add(gm, paint.LACQUER_RED, seed=95, depth=14, contact=0.45)
    scroll, figure = thai.pediment(cx, g_ridge + 20 * S, g_hw * 0.76, g_h * 0.84)
    add(_shape(w, h, scroll) * gm, paint.GOLD_DEEP, seed=96, depth=3.5, contact=0.25)
    add(_shape(w, h, figure) * gm, paint.GOLD, seed=97, depth=5, contact=0.35)
    return masks


def gate_mid(w, h, glow_out=1.0, ground=None, scale=None):
    S = scale or w / 1560.0
    ground = ground if ground is not None else h * 0.830
    img = core.canvas(w, h, "#000000")
    p = Painter(img, light=(-0.62, -0.78), depth_scale=w / 1400.0)
    masks = _ubosot(p, w, h, w * 0.5, S, glow_out, ground)
    a = np.zeros((h, w), dtype=np.float32)
    for m in masks:
        a = np.maximum(a, m)
    p.img = core.over(p.img, np.ones_like(p.img) * rgb("#5c3a52"), a * 0.10)
    return p.img, blur_a(a, 0.7)


def gate_near(w, h, ground=None, scale=None, rail_span=0.492):
    """Naga stair rails and lanterns, framing the shot from the dark."""
    S = scale or w / 1560.0
    ground = ground if ground is not None else h * 0.830
    img = core.canvas(w, h, "#000000")
    p = Painter(img, light=(-0.55, -0.8), depth_scale=w / 1100.0)
    masks = []

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    # steps rising toward the hall — treads and risers painted as alternating
    # parts, so the flight reads as stairs instead of one grey ramp
    n = 8
    tread, riser = Shape(w, h), Shape(w, h)
    # the flight has to span from the frame bottom up to the platform, however
    # tall that gap happens to be at this aspect ratio
    rise = max(120 * S, h * 1.02 - ground + 26 * S)
    for i in range(n):
        t = i / (n - 1)
        # perspective: each step up is shallower and narrower
        yb = h * 1.02 - rise * (t ** 0.86)
        hh = (rise / 4.8) * (1.0 - 0.42 * t)
        hw = w * (0.50 - 0.185 * t)
        hw2 = w * (0.50 - 0.185 * min(1.0, t + 1.0 / (n - 1)))
        riser.polygon([(w * 0.5 - hw, yb), (w * 0.5 + hw, yb), (w * 0.5 + hw, yb - hh), (w * 0.5 - hw, yb - hh)])
        tread.polygon([(w * 0.5 - hw, yb - hh), (w * 0.5 + hw, yb - hh),
                       (w * 0.5 + hw2, yb - hh - hh * 0.42), (w * 0.5 - hw2, yb - hh - hh * 0.42)])
    step_dark = paint.Material(
        [(0.0, "#7a6857"), (0.4, "#4b3f34"), (1.0, "#221c16")],
        spec=0.08, spec_color="#ffe6c0", spec_power=50, rim=0.16, rim_color="#c99a63",
        ambient=0.30, depth=14, grain=0.3, grain_cells=22, seam=0.4, shade_mix=0.7, value=0.42,
    )
    add(riser.mask(), step_dark, seed=1, depth=8, contact=0.0)
    add(tread.mask(), step_dark, seed=2, depth=6, contact=0.35)

    # พญานาค flanking the stairs
    for sgn in (-1, 1):
        # rail_span is tuned per plate: a portrait plate loses ~37% of its
        # width to the phone crop, so the rails have to sit further in
        x0 = w * (0.5 + sgn * rail_span)
        x1 = w * (0.5 + sgn * rail_span * 0.646)
        m = _shape(w, h, thai.naga_rail(x0, h * 1.045, x1, h * 1.02 - rise * 1.06, 30 * S, flip=sgn < 0))
        add(m, paint.GOLD_DEEP, seed=10 + sgn, depth=9, contact=0.45)

    # โคมไฟ — hanging lanterns, the warm anchors of the frame
    for sgn in (-1, 1):
        lx = w * (0.5 + sgn * 0.452)
        ly = h * 0.185
        post = _shape(w, h, [[(lx - 4 * S, h * 0.0), (lx + 4 * S, h * 0.0), (lx + 4 * S, ly - 52 * S), (lx - 4 * S, ly - 52 * S)]])
        add(post, paint.BRONZE_DARK, seed=20 + sgn, depth=5, contact=0.3)
        body = _shape(w, h, [
            quad((lx - 34 * S, ly - 38 * S), (lx - 46 * S, ly + 8 * S), (lx - 24 * S, ly + 44 * S), 24)
            + [(lx + 24 * S, ly + 44 * S)]
            + quad((lx + 24 * S, ly + 44 * S), (lx + 46 * S, ly + 8 * S), (lx + 34 * S, ly - 38 * S), 24)
        ])
        # tassel
        add(_shape(w, h, [[(lx - 4 * S, ly + 44 * S), (lx + 4 * S, ly + 44 * S), (lx + 7 * S, ly + 86 * S), (lx - 7 * S, ly + 86 * S)]]),
            paint.LACQUER_RED, seed=35 + sgn, depth=5, contact=0.2)
        add(body, paint.LACQUER_RED, seed=30 + sgn, depth=15, contact=0.4)
        p.img = core.add_light(p.img, rgb("#ff9c3a"), blur_a(body, 90 * S) * 0.9, 1.0)
        p.img = core.add_light(p.img, rgb("#ffc76a"), body * 0.75, 1.0)
        cap = _shape(w, h, [[(lx - 38 * S, ly - 36 * S), (lx + 38 * S, ly - 36 * S), (lx + 27 * S, ly - 54 * S), (lx - 27 * S, ly - 54 * S)]])
        add(cap, paint.BRASS, seed=40 + sgn, depth=6, contact=0.3)
        masks.append(blur_a(body, 60 * S) * 0.5)

    # bodhi leaves overhanging the top corners
    rs = np.random.RandomState(3)
    leaves = Shape(w, h)
    for sgn in (1, -1):
        ox = 0 if sgn > 0 else w
        branch = [(ox, h * -0.02), (ox + sgn * w * 0.10, h * 0.03), (ox + sgn * w * 0.22, h * 0.10), (ox + sgn * w * 0.36, h * 0.13)]
        leaves.line(branch, width=9 * S)
        leaves.line([(ox + sgn * w * 0.05, h * -0.02), (ox + sgn * w * 0.12, h * 0.08), (ox + sgn * w * 0.18, h * 0.19)], width=6 * S)
        for i in range(150):
            t = rs.rand()
            bx = ox + sgn * w * (0.005 + 0.30 * t) + rs.randn() * w * 0.026
            by = h * (-0.03 + 0.17 * t) + rs.randn() * h * 0.040
            r = (12 + rs.rand() * 13) * S
            leaves.polygon(
                quad((bx, by + r * 1.5), (bx - r, by + r * 0.2), (bx - r * 0.15, by - r * 0.9), 18)
                + quad((bx - r * 0.15, by - r * 0.9), (bx + r * 0.15, by - r * 0.9), (bx, by + r * 1.5), 8)
                + quad((bx, by + r * 1.5), (bx + r, by + r * 0.2), (bx + r * 0.15, by - r * 0.9), 18)
            )
    lm = leaves.mask()
    # a silhouette, not foliage: it exists to frame the sky, so only the rim
    # catches the lantern light
    add(lm, paint.Material([(0.0, "#4a5a38"), (0.22, "#26301c"), (0.60, "#131a0e"), (1.0, "#060803")],
                           spec=0.16, spec_color="#cfe08a", spec_power=34, rim=0.62, rim_color="#ffb463",
                           ambient=0.10, depth=8, grain=0.24, seam=0.28, shade_mix=0.82, value=0.42),
        seed=50, depth=6, contact=0.25)

    a = np.zeros((h, w), dtype=np.float32)
    for m in masks:
        a = np.maximum(a, m)
    return p.img, blur_a(np.clip(a, 0, 1), 0.7)


def gate_scene(w=1920, h=1080, ground=None, scale=None):
    """Composite preview of the entrance — layers are shipped separately."""
    sky = dusk_sky(w, h, ground=ground, scale=scale)
    far, fa = gate_far(w, h, ground=ground, scale=scale)
    mid, ma = gate_mid(w, h, ground=ground, scale=scale)
    near, na = gate_near(w, h, ground=ground, scale=scale)
    img = core.over(sky, far, fa)
    # aerial haze between the plates is most of what sells the depth
    img = core.over(img, np.ones_like(img) * rgb("#6b3f58"), np.full((h, w), 0.16, np.float32))
    img = core.over(img, mid, ma)
    img = core.over(img, np.ones_like(img) * rgb("#3d2038"), np.full((h, w), 0.10, np.float32))
    img = core.over(img, near, na)
    img = core.finish(img, bloom_amt=0.62, vig=0.5, ca=1.4, exposure=0.92, sat=1.10)
    return core.grade(img, lift=(0.012, 0.004, 0.008), gamma=(1.04, 1.01, 0.95), gain=(1.05, 1.00, 0.94), sat=1.04)


# ==========================================================================
# ฉากที่ ๒ — inside the ubosot
# ==========================================================================


def hall_bg(w=1920, h=1080):
    """Inside the ubosot, in one-point perspective.

    The whole read depends on the vanishing point: floor planks, ceiling
    beams and both colonnades converge on it, which is what turns a flat
    red wall into a room you are standing in.
    """
    S = w / 1920.0
    vx, vy = w * 0.5, h * 0.500          # vanishing point
    far = 0.255                          # scale of the far wall plane

    def persp(x, y, t):
        """Map a near-plane point to depth t (0 near, 1 at the far wall)."""
        k = far + (1.0 - far) * (1.0 - t)
        return vx + (x - vx) * k, vy + (y - vy) * k

    img = core.canvas(w, h, "#0d0503")
    p = Painter(img, light=(-0.55, -0.62), depth_scale=w / 1500.0)

    NEAR_L, NEAR_R = -w * 0.62, w * 1.62
    FLOOR_Y, CEIL_Y = h * 1.34, h * -0.34

    # ---- side walls (drawn first: everything else sits inside them) -----
    for sgn in (-1, 1):
        nx = NEAR_L if sgn < 0 else NEAR_R
        quadpts = [persp(nx, CEIL_Y, 0.0), persp(nx, CEIL_Y, 1.0), persp(nx, FLOOR_Y, 1.0), persp(nx, FLOOR_Y, 0.0)]
        m = Shape(w, h).polygon(quadpts).mask()
        p.part(m, paint.Material(
            [(0.0, "#8a2a18"), (0.30, "#5a1a0f"), (0.68, "#2e0d07"), (1.0, "#0d0402")],
            spec=0.10, spec_color="#ffb877", spec_power=40, rim=0.0,
            ambient=0.16, depth=60, grain=0.14, grain_cells=20, seam=0.0, shade_mix=0.8, value=0.42),
            seed=20 + sgn, depth=70, contact=0.0)
        # windows punched high in each side wall, the source of the shafts
        wins = Shape(w, h)
        for t in (0.16, 0.40, 0.64):
            x0, y0 = persp(nx, CEIL_Y * 0.34 + h * 0.02, t)
            x1, y1 = persp(nx, CEIL_Y * 0.10 + h * 0.42, t + 0.12)
            wins.polygon([(x0, y0), (x1, y0 + (y1 - y0) * 0.10), (x1, y1), (x0, y1 - (y1 - y0) * 0.10)])
        wm = wins.mask() * m
        p.img = core.add_light(p.img, rgb("#ffd9a0"), wm * 0.55, 1.0)
        p.img = core.add_light(p.img, rgb("#ff9c48"), blur_a(wm, 30 * S) * 0.30, 1.0)

    # ---- far wall -------------------------------------------------------
    fl, fb = persp(NEAR_L, FLOOR_Y, 1.0)
    fr, ft = persp(NEAR_R, CEIL_Y, 1.0)
    wall = Shape(w, h).rect((fl, ft, fr, fb)).mask()
    p.part(wall, paint.LACQUER_RED, seed=1, depth=60, contact=0.0)

    # ซุ้มเรือนแก้ว — the gilded arch and rays behind the principal image
    ax, ay = vx, fb - (fb - ft) * 0.30
    ar = (fr - fl) * 0.30
    rays = Shape(w, h)
    for i in range(30):
        a = i / 30.0 * 2 * math.pi
        rays.polygon([(ax, ay), (ax + math.cos(a) * ar * 2.1, ay + math.sin(a) * ar * 2.1),
                      (ax + math.cos(a + 0.055) * ar * 2.1, ay + math.sin(a + 0.055) * ar * 2.1)])
    rm = rays.mask() * wall
    p.img = core.add_light(p.img, rgb("#c98f2e"), blur_a(rm, 26 * S) * 0.20, 1.0)
    arch = Shape(w, h)
    arch.ellipse((ax - ar, ay - ar * 1.28, ax + ar, ay + ar * 1.28))
    am = arch.mask() * wall
    p.part(am - Shape(w, h).ellipse((ax - ar * 0.88, ay - ar * 1.13, ax + ar * 0.88, ay + ar * 1.13)).mask() * am,
           paint.GOLD_DEEP, seed=2, depth=6, contact=0.35)
    orn = Shape(w, h)
    for i in range(22):
        a = -math.pi / 2 + (i - 10.5) * 0.27
        ox, oy = ax + math.cos(a) * ar * 1.02, ay + math.sin(a) * ar * 1.30
        for poly in thai.kanok(ox, oy, ar * 0.20, math.degrees(a), depth=0, flip=math.cos(a) < 0):
            orn.polygon(poly)
    p.part(orn.mask() * wall, paint.GOLD, seed=3, depth=3.5, contact=0.25)

    # ---- floor ----------------------------------------------------------
    floor = Shape(w, h).polygon([(0, h), (w, h), persp(NEAR_R, FLOOR_Y, 1.0), persp(NEAR_L, FLOOR_Y, 1.0)]).mask()
    floor = np.maximum(floor, Shape(w, h).polygon([(0, h * 1.0), (w, h * 1.0), (w, h), (0, h)]).mask())
    p.part(floor, paint.TEAK, seed=5, depth=70, contact=0.0)
    planks = Shape(w, h)
    for i in range(23):
        x0 = NEAR_L + (NEAR_R - NEAR_L) * i / 22.0
        planks.line([persp(x0, FLOOR_Y, 0.0), persp(x0, FLOOR_Y, 1.0)], width=max(1.2, 2.2 * S))
    for j in range(1, 16):
        t = 1.0 - (1.0 - j / 16.0) ** 2.2
        planks.line([persp(NEAR_L, FLOOR_Y, t), persp(NEAR_R, FLOOR_Y, t)], width=max(1.0, 1.6 * S))
    p.darken(blur_a(planks.mask() * floor, 2.0 * S), 0.36)

    # ---- ceiling --------------------------------------------------------
    ceil = Shape(w, h).polygon([(0, 0), (w, 0), persp(NEAR_R, CEIL_Y, 1.0), persp(NEAR_L, CEIL_Y, 1.0)]).mask()
    p.part(ceil, paint.LACQUER_RED, seed=6, depth=70, contact=0.0)
    beams = Shape(w, h)
    for i in range(13):
        x0 = NEAR_L + (NEAR_R - NEAR_L) * i / 12.0
        beams.line([persp(x0, CEIL_Y, 0.0), persp(x0, CEIL_Y, 1.0)], width=max(2.0, 7 * S))
    for j in range(1, 12):
        t = 1.0 - (1.0 - j / 12.0) ** 2.0
        beams.line([persp(NEAR_L, CEIL_Y, t), persp(NEAR_R, CEIL_Y, t)], width=max(1.5, 5 * S))
    p.part(beams.mask() * ceil, paint.GOLD_DEEP, seed=7, depth=5, contact=0.4)
    p.darken(ceil * 0.80, 0.62)

    # ---- colonnades, far pair first ------------------------------------
    for t in (0.80, 0.52, 0.22, 0.0):
        for sgn in (-1, 1):
            x0 = vx + sgn * w * 0.445
            cxp, top = persp(x0, CEIL_Y * 0.30 + h * 0.10, t)
            _, bot = persp(x0, FLOOR_Y * 0.96, t)
            k = far + (1.0 - far) * (1.0 - t)
            cw = 205 * S * k
            m = _shape(w, h, thai.column(cxp, top, bot, cw))
            p.part(m, paint.LACQUER_RED, seed=int(cxp) % 80 + int(t * 90), depth=max(6.0, 22 * k), contact=0.45)
            cap = _shape(w, h, thai.lotus_capital(cxp, top + 8 * S * k, cw * 1.15, cw * 1.0))
            p.part(cap, paint.GOLD_DEEP, seed=int(cxp) % 60, depth=max(4.0, 11 * k), contact=0.35)
            ring = Shape(w, h).rect((cxp - cw * 0.60, bot - cw * 1.05, cxp + cw * 0.60, bot - cw * 0.86)).mask() * m
            p.part(ring, paint.GOLD_DEEP, seed=int(cxp) % 50, depth=max(2.0, 5 * k), contact=0.25)
            # haze thickens with distance
            if t > 0:
                p.img = core.over(p.img, np.ones_like(p.img) * rgb("#54180f"), blur_a(m, 26 * S) * t * 0.42)

    # ---- light ----------------------------------------------------------
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    shafts = np.zeros((h, w), dtype=np.float32)
    for ox, wdt, stg in ((0.20, 0.052, 1.0), (0.325, 0.044, 0.66)):
        band = np.clip(1.0 - np.abs((xx / w + (yy / h) * 0.42 - ox) / wdt), 0, 1) ** 1.7
        band *= np.clip(1.0 - yy / h * 1.05, 0, 1) ** 1.3
        shafts += band * stg
    shafts *= 0.5 + 0.5 * core.fbm(w, h, 3, 4, 9)
    p.img = core.add_light(p.img, rgb("#ffcf85"), blur_a(shafts, 20 * S) * 0.22, 1.0)

    halo = radial_falloff(w, h, 0.5, 0.62, 0.30, 0.34, 1.8)
    p.img = core.add_light(p.img, rgb("#ff9c3a"), halo * 0.34, 1.0)
    p.img = core.add_light(p.img, rgb("#ff8a2e"),
                           radial_falloff(w, h, 0.5, 1.02, 0.55, 0.30, 1.4) * 0.20, 1.0)

    return core.finish(p.img, bloom_amt=0.42, vig=0.58, ca=1.0, exposure=0.90, sat=1.07)


def hall_altar(w=1500, h=620):
    """โต๊ะหมู่บูชา — the tiered altar in front of the principal image."""
    S = w / 1500.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.58, -0.8), depth_scale=w / 1100.0)
    masks = []

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    # three tiers, tallest at the back
    tiers = ((0.500, 0.095, 0.30, 0.34), (0.500, 0.300, 0.40, 0.48), (0.500, 0.520, 0.50, 0.62))
    for i, (cxr, yr, hwr, botr) in enumerate(tiers):
        cx, y0, hw, y1 = w * cxr, h * yr, w * hwr, h * botr
        top = _shape(w, h, [[(cx - hw, y0), (cx + hw, y0), (cx + hw * 0.96, y0 + h * 0.055), (cx - hw * 0.96, y0 + h * 0.055)]])
        add(top, paint.TEAK_LIGHT, seed=10 + i, depth=10, contact=0.45)
        skirt = _shape(w, h, [[(cx - hw * 0.94, y0 + h * 0.05), (cx + hw * 0.94, y0 + h * 0.05),
                               (cx + hw * 0.86, y1), (cx - hw * 0.86, y1)]])
        add(skirt, paint.LACQUER_RED, seed=20 + i, depth=14, contact=0.4)
        orn = Shape(w, h)
        for k in range(7):
            ox = cx + (k - 3) * hw * 0.27
            for poly in thai.kanok(ox, y0 + h * 0.13, h * 0.055, -90, depth=1):
                orn.polygon(poly)
        add(orn.mask() * skirt, paint.GOLD, seed=30 + i, depth=4, contact=0.2)
        add(_shape(w, h, [[(cx - hw * 1.02, y0 - h * 0.012), (cx + hw * 1.02, y0 - h * 0.012),
                           (cx + hw * 1.02, y0 + h * 0.012), (cx - hw * 1.02, y0 + h * 0.012)]]),
            paint.GOLD_DEEP, seed=40 + i, depth=4, contact=0.25)

    # brass candlesticks and vases on the top tier
    for sgn in (-1, 1):
        bx = w * (0.5 + sgn * 0.215)
        stem = _shape(w, h, [[(bx - 7 * S, h * 0.095), (bx + 7 * S, h * 0.095), (bx + 5 * S, h * -0.09), (bx - 5 * S, h * -0.09)]]
                      + [[(bx - 26 * S, h * 0.098), (bx + 26 * S, h * 0.098), (bx + 20 * S, h * 0.062), (bx - 20 * S, h * 0.062)]])
        add(stem, paint.BRASS, seed=50 + sgn, depth=7, contact=0.4)
        vx = w * (0.5 + sgn * 0.335)
        add(_shape(w, h, [
            quad((vx - 30 * S, h * 0.30), (vx - 46 * S, h * 0.16), (vx - 22 * S, h * 0.03), 22)
            + [(vx + 22 * S, h * 0.03)]
            + quad((vx + 22 * S, h * 0.03), (vx + 46 * S, h * 0.16), (vx + 30 * S, h * 0.30), 22)]),
            paint.BRASS, seed=60 + sgn, depth=13, contact=0.4)
        for j in range(5):
            a = -1.35 + j * 0.62
            lx, ly = vx + math.sin(a) * 52 * S, h * 0.02 - math.cos(a) * 46 * S
            add(_shape(w, h, thai.lotus_flower(lx, ly, 26 * S, 2)),
                paint.Material([(0.0, "#ffd9e4"), (0.35, "#f090ad"), (0.72, "#b8436a"), (1.0, "#4a1225")],
                               spec=0.3, spec_color="#fff0f4", rim=0.4, rim_color="#ffc0d0",
                               ambient=0.30, depth=8, grain=0.1, seam=0.35, shade_mix=0.78, value=0.42),
                seed=70 + j + sgn, depth=6, contact=0.3)
            add(_shape(w, h, [[(lx - 3 * S, ly), (lx + 3 * S, ly), (lx + 4 * S, h * 0.05), (lx - 4 * S, h * 0.05)]]),
                paint.Material([(0.0, "#7aa356"), (0.5, "#3f5c2c"), (1.0, "#16210f")],
                               spec=0.15, rim=0.3, rim_color="#b8d488", ambient=0.34, depth=5, seam=0.3),
                seed=80 + j, depth=4, contact=0.2)

    a = np.zeros((h, w), dtype=np.float32)
    for m in masks:
        a = np.maximum(a, m)
    out = core.finish(p.img, bloom_amt=0.3, vig=0.0, ca=0.0, exposure=0.94, sat=1.08)
    return out, blur_a(a, 0.7)


def hall_near(w=1920, h=1080):
    """Foreground floor, mat and the dark pillars that frame the shot."""
    S = w / 1920.0
    img = core.canvas(w, h, "#000000")
    p = Painter(img, light=(-0.5, -0.85), depth_scale=w / 1300.0)
    masks = []

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    # เสื่อ — the woven mat you kneel on
    my = h * 0.905
    mat = _shape(w, h, [[(w * 0.13, h * 1.02), (w * 0.87, h * 1.02), (w * 0.70, my), (w * 0.30, my)]])
    add(mat, paint.Material([(0.0, "#c9a86a"), (0.35, "#9c7b42"), (0.72, "#5e4823"), (1.0, "#241a0c")],
                            spec=0.10, spec_color="#ffeec2", spec_power=50, rim=0.24, rim_color="#e8c07a",
                            ambient=0.34, depth=30, grain=0.30, grain_cells=90, seam=0.3, shade_mix=0.72, value=0.44),
        seed=1, depth=24, contact=0.0)
    weave = Shape(w, h)
    for i in range(46):
        t = i / 45.0
        weave.line([(w * (0.30 + 0.40 * t), my), (w * (0.13 + 0.74 * t), h * 1.02)], width=max(1.0, 1.6 * S))
    for j in range(11):
        t = j / 10.0
        y = my + (h * 1.02 - my) * t
        k = 0.30 - 0.17 * t
        weave.line([(w * (0.5 - k), y), (w * (0.5 + k), y)], width=max(1.0, 1.8 * S))
    p.darken(blur_a(weave.mask() * mat, 1.6 * S), 0.28)
    add(_shape(w, h, [[(w * 0.13, h * 1.02), (w * 0.87, h * 1.02), (w * 0.855, h * 1.0), (w * 0.145, h * 1.0)]]),
        paint.LACQUER_RED, seed=2, depth=6, contact=0.3)

    # dark framing pillars at the very edges
    for sgn in (-1, 1):
        cxp = w * (0.5 + sgn * 0.545)
        m = _shape(w, h, thai.column(cxp, -h * 0.02, h * 1.05, 300 * S))
        add(m, paint.Material([(0.0, "#5c2418"), (0.3, "#361208"), (0.7, "#1a0704"), (1.0, "#080201")],
                              spec=0.18, spec_color="#ffb877", spec_power=30, rim=0.5, rim_color="#ff9c48",
                              ambient=0.12, depth=40, grain=0.14, seam=0.4, shade_mix=0.82, value=0.4),
            seed=10 + sgn, depth=34, contact=0.0)

    a = np.zeros((h, w), dtype=np.float32)
    for m in masks:
        a = np.maximum(a, m)
    out = core.finish(p.img, bloom_amt=0.2, vig=0.0, ca=0.0, exposure=0.88, sat=1.04)
    return out, blur_a(a, 0.7)


# ==========================================================================
# ฉากที่ ๕ — the wall of numbered drawers the slip comes out of
# ==========================================================================


def drawer_wall(w=1600, h=1000, cols=7, rows=4):
    S = w / 1600.0
    img = core.linear_gradient(w, h, [(0.0, "#2a1a10"), (0.5, "#3d2716"), (1.0, "#1a0f08")])
    p = Painter(img, light=(-0.7, -0.6), depth_scale=w / 1400.0)

    frame = Shape(w, h).rect((w * 0.02, h * 0.03, w * 0.98, h * 0.97), radius=10 * S).mask()
    p.part(frame, paint.TEAK, seed=1, depth=26, contact=0.0)

    pad_x, pad_y = w * 0.045, h * 0.075
    gw = (w - pad_x * 2) / cols
    gh = (h - pad_y * 2) / rows
    faces, pulls, plates = Shape(w, h), Shape(w, h), Shape(w, h)
    for r in range(rows):
        for c in range(cols):
            x0 = pad_x + c * gw + gw * 0.05
            y0 = pad_y + r * gh + gh * 0.07
            x1, y1 = x0 + gw * 0.90, y0 + gh * 0.86
            faces.rect((x0, y0, x1, y1), radius=5 * S)
            cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
            pulls.ellipse((cx0 - gw * 0.055, y1 - gh * 0.20, cx0 + gw * 0.055, y1 - gh * 0.08))
            plates.rect((cx0 - gw * 0.20, cy0 - gh * 0.22, cx0 + gw * 0.20, cy0 + gh * 0.02), radius=4 * S)
    p.part(faces.mask(), paint.TEAK_LIGHT, seed=2, depth=9, contact=0.55)
    p.part(plates.mask(), paint.BRASS, seed=3, depth=5, contact=0.4)
    p.part(pulls.mask(), paint.BRASS, seed=4, depth=4, contact=0.4)

    # a warm raking light from the left, as if from the candles on the altar
    p.img = core.add_light(p.img, rgb("#ff9c3a"),
                           radial_falloff(w, h, 0.12, 0.42, 0.72, 0.85, 1.6) * 0.22, 1.0)
    return core.finish(p.img, bloom_amt=0.25, vig=0.42, ca=0.7, exposure=0.92, sat=1.05)
