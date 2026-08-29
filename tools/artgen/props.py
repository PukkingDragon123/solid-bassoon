"""Standalone prop renders — transparent PNGs the app can move and light."""
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


def _alpha_union(masks):
    a = np.zeros_like(masks[0])
    for m in masks:
        a = np.maximum(a, m)
    return a


# ==========================================================================
# พระพุทธรูป — the principal Buddha image
# ==========================================================================


def buddha_statue(w=1100, h=1500, height=None, with_base=True):
    height = height or h * 0.56
    cx = w / 2
    lap_y = h * 0.735 if with_base else h * 0.95
    img = core.canvas(w, h, "#0a0704")
    p = Painter(img, light=(-0.5, -0.88), depth_scale=height / 260.0)
    masks = []

    mats = {
        "skin": paint.GOLD,
        "robe": paint.GOLD_DEEP,
        "hair": paint.BRONZE_DARK,
        "flame": paint.GOLD,
    }

    if with_base:
        # the pedestal tucks just under the lap so the figure sits *on* it
        base_top = lap_y + height * 0.020
        base_h = min(h - base_top - 4, height * 0.34)
        groups = {}
        for g, poly in thai.lotus_base(cx, base_top + base_h, height * 0.94, base_h):
            groups.setdefault(g, []).append(poly)
        for i, g in enumerate(("drum", "plinth", "petal_dn", "petal_up")):
            if g not in groups:
                continue
            m = _shape(w, h, groups[g])
            mat = paint.GOLD_DEEP if g in ("drum", "plinth") else paint.GOLD
            p.part(m, mat, seed=20 + i, depth=9 if "petal" in g else 14,
                   contact=0.0 if i == 0 else 0.45)
            masks.append(m)

    for kind, poly, name in thai.buddha(cx, lap_y, height):
        m = _shape(w, h, [poly])
        mat = mats[kind]
        d = {"hair": 9.0, "flame": 8.0}.get(kind, None)
        blend = name in ("chest", "belly")
        soft = blend or name in ("arm_l", "arm_r", "sash", "sash_fold", "lap")
        p.part(
            m if not blend else blur_a(m, height * 0.012),
            paint.GOLD_SOFT if blend else mat,
            seed=hash(name) % 900,
            depth=d,
            contact=0.0 if blend else (0.30 if soft else (0.2 if kind == "flame" else 0.5)),
            contact_radius=height * 0.09 if soft else None,
            opacity=0.62 if blend else 1.0,
        )
        masks.append(m)
        if name == "hair":
            curls = Shape(w, h)
            for (x, y, r) in thai.hair_curls(cx, lap_y, height):
                curls.ellipse((x - r, y - r, x + r, y + r))
            cm = curls.mask() * m
            p.part(cm, paint.BRONZE_DARK, seed=7, depth=3.5, contact=0.5)
        if name == "head":
            _face(p, w, h, cx, lap_y, height, m)

    alpha = _alpha_union(masks)
    # gilding: warm light pooling on the shoulders and knees
    p.img = core.add_light(p.img, rgb("#ffcf7a"), blur_a(alpha, height * 0.05) * alpha * 0.10, 1.0)
    out = core.finish(p.img, bloom_amt=0.28, vig=0.0, ca=0.0, exposure=0.98, sat=1.10)
    return out, blur_a(alpha, 0.6)


def _face(p: Painter, w, h, cx, lap_y, height, head):
    """Downcast eyes, a straight Sukhothai nose and the faint archaic smile."""
    H = height

    def P(u, v):
        return (cx + u * H, lap_y - v * H)

    def sh(polys, lines=()):
        s = Shape(w, h)
        for poly in polys:
            s.polygon(poly)
        for pts, wd in lines:
            s.line(pts, width=wd)
        return s.mask() * head

    # brow ridges — two arcs meeting over the bridge of the nose
    brows = []
    for sgn in (-1, 1):
        a, b, c = P(sgn * 0.012, 0.796), P(sgn * 0.048, 0.816), P(sgn * 0.086, 0.800)
        a2, b2, c2 = P(sgn * 0.012, 0.788), P(sgn * 0.048, 0.806), P(sgn * 0.086, 0.792)
        brows.append(quad(a, b, c, 20) + list(reversed(quad(a2, b2, c2, 20))))
    p.part(sh(brows), paint.GOLD, seed=31, depth=2.6, contact=0.28)

    # eyes: lowered lids, a long almond with an almost flat lower line
    eyes = []
    for sgn in (-1, 1):
        inner, outer = P(sgn * 0.024, 0.775), P(sgn * 0.074, 0.784)
        eyes.append(quad(inner, P(sgn * 0.050, 0.789), outer, 22) + list(reversed(quad(inner, P(sgn * 0.050, 0.773), outer, 22))))
    em = sh(eyes)
    p.darken(blur_a(em, H * 0.0035), 0.40)
    # the bright edge of the upper lid
    lids = []
    for sgn in (-1, 1):
        lids.append(
            quad(P(sgn * 0.024, 0.777), P(sgn * 0.050, 0.790), P(sgn * 0.074, 0.786), 22)
            + list(reversed(quad(P(sgn * 0.024, 0.780), P(sgn * 0.050, 0.794), P(sgn * 0.074, 0.789), 22)))
        )
    p.part(sh(lids), paint.GOLD, seed=32, depth=1.6, contact=0.0)

    # อุณาโลม — the urna between the brows
    ur = Shape(w, h).ellipse((cx - H * 0.011, lap_y - H * 0.830 - H * 0.011, cx + H * 0.011, lap_y - H * 0.830 + H * 0.011)).mask() * head
    p.part(ur, paint.GOLD, seed=33, depth=2.0, contact=0.3)

    # nose: a straight narrow ridge widening to a small rounded tip
    nose = (
        quad(P(-0.013, 0.730), P(-0.011, 0.780), P(-0.006, 0.800), 18)
        + quad(P(-0.006, 0.800), P(0.0, 0.804), P(0.006, 0.800), 8)
        + quad(P(0.006, 0.800), P(0.011, 0.780), P(0.013, 0.730), 18)
        + quad(P(0.013, 0.730), P(0.016, 0.719), P(0.0, 0.716), 14)
        + quad(P(0.0, 0.716), P(-0.016, 0.719), P(-0.013, 0.730), 14)
    )
    p.part(sh([nose]), paint.GOLD, seed=34, depth=2.8, contact=0.34)
    p.darken(blur_a(sh([[P(-0.022, 0.726), P(-0.013, 0.732), P(-0.014, 0.719)],
                        [P(0.022, 0.726), P(0.013, 0.732), P(0.014, 0.719)]]), H * 0.004), 0.4)

    # lips: full lower lip, a cupid's bow above, corners lifted
    upper = (
        quad(P(-0.036, 0.700), P(-0.018, 0.712), P(-0.004, 0.703), 18)
        + quad(P(-0.004, 0.703), P(0.0, 0.708), P(0.004, 0.703), 8)
        + quad(P(0.004, 0.703), P(0.018, 0.712), P(0.036, 0.700), 18)
        + list(reversed(quad(P(-0.036, 0.700), P(0.0, 0.696), P(0.036, 0.700), 24)))
    )
    lower = quad(P(-0.034, 0.699), P(0.0, 0.694), P(0.034, 0.699), 24) + list(
        reversed(quad(P(-0.034, 0.699), P(0.0, 0.678), P(0.034, 0.699), 24))
    )
    p.part(sh([lower]), paint.GOLD, seed=35, depth=3.0, contact=0.3)
    p.part(sh([upper]), paint.GOLD, seed=36, depth=2.2, contact=0.25)
    p.darken(blur_a(sh([], [([P(-0.036, 0.700), P(-0.014, 0.701), P(0.0, 0.699), P(0.014, 0.701), P(0.036, 0.700)],
                            max(2.0, H * 0.0035))]), H * 0.003), 0.5)

    # the three auspicious lines on the throat
    for i, v in enumerate((0.618, 0.596, 0.574)):
        ln = Shape(w, h).line([P(-0.058 + i * 0.004, v + 0.004), P(0.0, v), P(0.058 - i * 0.004, v + 0.004)],
                              width=max(2.0, H * 0.004)).mask()
        p.darken(blur_a(ln, H * 0.003), 0.34)


def render(name, fn, **kw):
    rgbf, a = fn(**kw)
    return name, core.to_pil(rgbf, a)


def _finish_prop(p, masks, *, bloom=0.3, exposure=0.95, sat=1.06, soft=0.6):
    a = np.zeros_like(masks[0])
    for m in masks:
        a = np.maximum(a, m)
    return core.finish(p.img, bloom_amt=bloom, vig=0.0, ca=0.0, exposure=exposure, sat=sat), blur_a(a, soft)


# ==========================================================================
# กระถางธูป — the sand-filled censer the incense is planted in
# ==========================================================================


def censer(w=900, h=620):
    S = w / 900.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.55, -0.8), depth_scale=w / 700.0)
    masks = []
    cx = w / 2

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    # foot ring and three cabriole legs
    for sgn in (-1, 0, 1):
        lx = cx + sgn * w * 0.235
        add(_shape(w, h, [
            quad((lx - 26 * S, h * 0.70), (lx - 40 * S, h * 0.86), (lx - 22 * S, h * 0.96), 20)
            + [(lx + 22 * S, h * 0.96)]
            + quad((lx + 22 * S, h * 0.96), (lx + 40 * S, h * 0.86), (lx + 26 * S, h * 0.70), 20)]),
            paint.BRASS, seed=1 + sgn, depth=10, contact=0.4)
    add(_shape(w, h, [[(cx - w * 0.30, h * 0.955), (cx + w * 0.30, h * 0.955),
                       (cx + w * 0.27, h * 0.995), (cx - w * 0.27, h * 0.995)]]),
        paint.BRASS, seed=5, depth=8, contact=0.35)

    # the bowl
    bowl = _shape(w, h, [
        quad((cx - w * 0.40, h * 0.315), (cx - w * 0.40, h * 0.60), (cx - w * 0.20, h * 0.755), 30)
        + [(cx + w * 0.20, h * 0.755)]
        + quad((cx + w * 0.20, h * 0.755), (cx + w * 0.40, h * 0.60), (cx + w * 0.40, h * 0.315), 30)])
    add(bowl, paint.BRASS, seed=10, depth=26, contact=0.45)
    # chased kanok band around the belly
    band = Shape(w, h)
    for i in range(9):
        bx = cx + (i - 4) * w * 0.083
        for poly in thai.kanok(bx, h * 0.53, w * 0.052, -90, depth=1):
            band.polygon(poly)
    p.darken(blur_a(band.mask() * bowl, 3 * S), 0.34)
    p.part(band.mask() * bowl * 0.55, paint.GOLD, seed=11, depth=3, contact=0.0)

    # everted rim
    add(_shape(w, h, [[(cx - w * 0.435, h * 0.300), (cx + w * 0.435, h * 0.300),
                       (cx + w * 0.400, h * 0.355), (cx - w * 0.400, h * 0.355)]]),
        paint.BRASS, seed=12, depth=9, contact=0.35)

    # ทราย — the sand, heaped a little
    sand = _shape(w, h, [
        quad((cx - w * 0.395, h * 0.330), (cx, h * 0.283), (cx + w * 0.395, h * 0.330), 40)
        + [(cx + w * 0.385, h * 0.395), (cx - w * 0.385, h * 0.395)]])
    add(sand, paint.ASH, seed=13, depth=16, contact=0.5)
    rs = np.random.RandomState(9)
    grit = Shape(w, h)
    for _ in range(700):
        gx = cx + (rs.rand() - 0.5) * w * 0.76
        gy = h * (0.295 + rs.rand() * 0.09)
        r = (1.2 + rs.rand() * 2.4) * S
        grit.ellipse((gx - r, gy - r, gx + r, gy + r))
    p.darken(blur_a(grit.mask() * sand, 1.4 * S), 0.22)

    # ก้านธูปเก่า — burnt-down stubs left from earlier visitors
    for i in range(9):
        sx = cx + (rs.rand() - 0.5) * w * 0.62
        top = h * (0.10 + rs.rand() * 0.14)
        lean = (rs.rand() - 0.5) * w * 0.05
        add(_shape(w, h, [[(sx - 3.2 * S, h * 0.34), (sx + 3.2 * S, h * 0.34),
                           (sx + lean + 2.6 * S, top), (sx + lean - 2.6 * S, top)]]),
            paint.Material([(0.0, "#6b5a4a"), (0.4, "#3a2c22"), (1.0, "#120c08")],
                           spec=0.1, rim=0.3, rim_color="#c99a63", ambient=0.34, depth=4, seam=0.3,
                           shade_mix=0.76, value=0.4),
            seed=20 + i, depth=3, contact=0.3)
    return _finish_prop(p, masks)


# ==========================================================================
# เทียน — the candle you light first
# ==========================================================================


def candle(w=280, h=760):
    S = w / 280.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.5, -0.85), depth_scale=w / 220.0)
    masks = []
    cx = w / 2

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    add(_shape(w, h, [[(cx - w * 0.36, h * 0.985), (cx + w * 0.36, h * 0.985),
                       (cx + w * 0.30, h * 0.930), (cx - w * 0.30, h * 0.930)]]
               + [[(cx - w * 0.22, h * 0.935), (cx + w * 0.22, h * 0.935),
                   (cx + w * 0.17, h * 0.880), (cx - w * 0.17, h * 0.880)]]),
        paint.BRASS, seed=1, depth=8, contact=0.0)
    # the candle body, very slightly tapered, with a soft melted lip
    body = _shape(w, h, [
        [(cx - w * 0.155, h * 0.905), (cx + w * 0.155, h * 0.905)]
        + [(cx + w * 0.135, h * 0.125)]
        + quad((cx + w * 0.135, h * 0.125), (cx + w * 0.10, h * 0.086), (cx, h * 0.082), 18)
        + quad((cx, h * 0.082), (cx - w * 0.10, h * 0.086), (cx - w * 0.135, h * 0.125), 18)])
    add(body, paint.WAX, seed=2, depth=20, contact=0.4)
    # drips down one side
    drip = Shape(w, h)
    for (dy, dl, dx) in ((0.16, 0.16, -0.115), (0.22, 0.10, 0.108), (0.34, 0.13, -0.125)):
        drip.polygon(
            quad((cx + w * dx - 12 * S, h * dy), (cx + w * dx, h * (dy + dl + 0.04)), (cx + w * dx + 12 * S, h * dy), 20))
    add(drip.mask() * body, paint.WAX, seed=3, depth=8, contact=0.25)
    add(_shape(w, h, [[(cx - 2.6 * S, h * 0.088), (cx + 2.6 * S, h * 0.088),
                       (cx + 2.0 * S, h * 0.040), (cx - 2.0 * S, h * 0.040)]]),
        paint.Material([(0.0, "#6b5a48"), (0.5, "#2e2418"), (1.0, "#0d0904")],
                       spec=0.06, rim=0.3, rim_color="#d9a460", ambient=0.36, depth=3, seam=0.3),
        seed=4, depth=2.5, contact=0.3)
    return _finish_prop(p, masks)


# ==========================================================================
# ธูป ๓ ดอก — the three sticks of incense
# ==========================================================================


def incense(w=340, h=920, lit=False):
    S = w / 340.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.5, -0.85), depth_scale=w / 260.0)
    masks = []
    cx = w / 2

    stick_mat = paint.Material(
        [(0.0, "#8a5a46"), (0.35, "#5e3527"), (0.72, "#371d14"), (1.0, "#150a06")],
        spec=0.14, spec_color="#ffcaa0", spec_power=44, rim=0.45, rim_color="#d98f63",
        ambient=0.30, depth=5, grain=0.10, seam=0.34, shade_mix=0.78, value=0.42,
    )
    cane_mat = paint.Material(
        [(0.0, "#d8b070"), (0.4, "#9a7440"), (1.0, "#3f2c14")],
        spec=0.2, spec_color="#ffe9c0", spec_power=40, rim=0.4, rim_color="#e8c288",
        ambient=0.34, depth=4, grain=0.1, seam=0.3, shade_mix=0.76, value=0.42,
    )
    for i, lean in enumerate((-0.085, 0.0, 0.085)):
        sx = cx + w * lean * 0.55
        tipx = cx + w * lean * 2.1
        tw = 5.2 * S
        add_m = _shape(w, h, [[(sx - tw, h * 0.995), (sx + tw, h * 0.995),
                               (tipx + tw * 0.82, h * 0.135), (tipx - tw * 0.82, h * 0.135)]])
        p.part(add_m, cane_mat, seed=1 + i, depth=4, contact=0.3)
        masks.append(add_m)
        coat = _shape(w, h, [[(sx - tw * 1.24, h * 0.700), (sx + tw * 1.24, h * 0.700),
                              (tipx + tw * 1.05, h * 0.128), (tipx - tw * 1.05, h * 0.128)]])
        p.part(coat, stick_mat, seed=10 + i, depth=5, contact=0.3)
        masks.append(coat)
        if lit:
            ember = _shape(w, h, [[(tipx - tw * 1.1, h * 0.128), (tipx + tw * 1.1, h * 0.128),
                                   (tipx + tw * 0.9, h * 0.098), (tipx - tw * 0.9, h * 0.098)]])
            p.img = core.add_light(p.img, rgb("#ff5a1e"), blur_a(ember, 22 * S) * 0.9, 1.0)
            p.img = core.add_light(p.img, rgb("#ffd08a"), ember * 0.9, 1.0)
            masks.append(blur_a(ember, 10 * S))
    return _finish_prop(p, masks, bloom=0.5)


# ==========================================================================
# กระบอกเซียมซี — the bamboo cylinder and its sticks
# ==========================================================================


def siamsee_tube(w=680, h=1080):
    S = w / 680.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.52, -0.82), depth_scale=w / 520.0)
    masks = []
    cx = w / 2

    def add(m, mat, **kw):
        p.part(m, mat, **kw)
        masks.append(m)
        return m

    # the sticks first — the tube is painted over their lower halves
    rs = np.random.RandomState(17)
    sticks, heads = Shape(w, h), Shape(w, h)
    n = 27
    for i in range(n):
        t = (i - (n - 1) / 2) / ((n - 1) / 2)
        top = h * (0.055 + rs.rand() * 0.20)
        bx = cx + t * w * 0.185
        tx = cx + t * w * 0.360 + (rs.rand() - 0.5) * w * 0.02
        sw = 7.0 * S
        sticks.polygon([(bx - sw, h * 0.62), (bx + sw, h * 0.62), (tx + sw * 0.9, top), (tx - sw * 0.9, top)])
        heads.polygon([(tx - sw * 0.9, top), (tx + sw * 0.9, top),
                       (tx + sw * 0.9, top + h * 0.055), (tx - sw * 0.9, top + h * 0.055)])
    add(sticks.mask(), paint.BAMBOO, seed=1, depth=5, contact=0.35)
    add(heads.mask(), paint.LACQUER_RED, seed=2, depth=4, contact=0.3)

    # the cylinder
    tube = _shape(w, h, [[(cx - w * 0.255, h * 0.995), (cx + w * 0.255, h * 0.995),
                          (cx + w * 0.225, h * 0.400), (cx - w * 0.225, h * 0.400)]])
    add(tube, paint.BAMBOO, seed=10, depth=30, contact=0.5)
    # bamboo node rings + the darker mouth
    rings = Shape(w, h)
    for yr in (0.455, 0.640, 0.840):
        rings.rect((cx - w * 0.262, h * yr - 9 * S, cx + w * 0.262, h * yr + 9 * S), radius=6 * S)
    add(rings.mask(), paint.BAMBOO, seed=11, depth=7, contact=0.35)
    mouth = _shape(w, h, [[(cx - w * 0.228, h * 0.398), (cx + w * 0.228, h * 0.398),
                           (cx + w * 0.228, h * 0.432), (cx - w * 0.228, h * 0.432)]])
    p.darken(blur_a(mouth, 5 * S), 0.55)
    masks.append(mouth)
    # a red cord tied round the waist
    add(_shape(w, h, [[(cx - w * 0.262, h * 0.735), (cx + w * 0.262, h * 0.735),
                       (cx + w * 0.262, h * 0.775), (cx - w * 0.262, h * 0.775)]]),
        paint.LACQUER_RED, seed=12, depth=6, contact=0.3)
    # a vertical grain wash so the cylinder reads as bamboo, not plastic
    grain = Shape(w, h)
    for i in range(14):
        gx = cx + (i - 6.5) * w * 0.036
        grain.line([(gx, h * 0.40), (gx + w * 0.006, h * 0.995)], width=max(1.2, 2.0 * S))
    p.darken(blur_a(grain.mask() * tube, 2.4 * S), 0.16)
    return _finish_prop(p, masks)


def siamsee_stick(w=130, h=1000):
    S = w / 130.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.5, -0.85), depth_scale=w / 100.0)
    masks = []
    cx = w / 2
    body = _shape(w, h, [[(cx - w * 0.30, h * 0.998), (cx + w * 0.30, h * 0.998),
                          (cx + w * 0.36, h * 0.055), (cx - w * 0.36, h * 0.055)]])
    p.part(body, paint.BAMBOO, seed=1, depth=9, contact=0.0)
    masks.append(body)
    head = _shape(w, h, [[(cx - w * 0.36, h * 0.052), (cx + w * 0.36, h * 0.052),
                          (cx + w * 0.36, h * 0.300), (cx - w * 0.36, h * 0.300)]])
    p.part(head, paint.LACQUER_RED, seed=2, depth=6, contact=0.3)
    masks.append(head)
    tip = _shape(w, h, [quad((cx - w * 0.30, h * 0.998), (cx, h * 1.02), (cx + w * 0.30, h * 0.998), 18)])
    p.part(tip, paint.BAMBOO, seed=3, depth=5, contact=0.2)
    masks.append(tip)
    return _finish_prop(p, masks)


# ==========================================================================
# ใบเซียมซี — the paper slip, left blank for the app to typeset
# ==========================================================================


def slip(w=780, h=1180):
    S = w / 780.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.4, -0.75), depth_scale=w / 620.0)

    # deckled edge: a rectangle whose border wobbles like torn mulberry paper
    rs = np.random.RandomState(23)
    m0, m1 = w * 0.045, h * 0.030
    pts = []
    for i in range(70):
        pts.append((m0 + (w - 2 * m0) * i / 69.0, m1 + rs.randn() * 3.4 * S))
    for i in range(70):
        pts.append((w - m0 + rs.randn() * 3.4 * S, m1 + (h - 2 * m1) * i / 69.0))
    for i in range(70):
        pts.append((w - m0 - (w - 2 * m0) * i / 69.0, h - m1 + rs.randn() * 3.4 * S))
    for i in range(70):
        pts.append((m0 + rs.randn() * 3.4 * S, h - m1 - (h - 2 * m1) * i / 69.0))
    sheet = _shape(w, h, [pts])
    p.part(sheet, paint.PAPER, seed=1, depth=34, contact=0.0)

    # mulberry fibres suspended in the sheet
    fib = Shape(w, h)
    for _ in range(500):
        fx, fy = rs.rand() * w, rs.rand() * h
        a = rs.rand() * math.pi
        ln = (12 + rs.rand() * 60) * S
        fib.line([(fx, fy), (fx + math.cos(a) * ln, fy + math.sin(a) * ln)], width=max(1.0, 1.4 * S))
    p.darken(blur_a(fib.mask() * sheet, 1.6 * S), 0.10)
    p.img = core.add_light(p.img, rgb("#fff4dc"), blur_a(fib.mask() * sheet, 3.0 * S) * 0.06, 1.0)

    # red double rule and corner seal
    rule = Shape(w, h)
    rule.rect((w * 0.085, h * 0.058, w * 0.915, h * 0.942), radius=6 * S)
    inner = Shape(w, h).rect((w * 0.085 + 7 * S, h * 0.058 + 7 * S, w * 0.915 - 7 * S, h * 0.942 - 7 * S), radius=6 * S).mask()
    rule2 = Shape(w, h).rect((w * 0.100, h * 0.070, w * 0.900, h * 0.930), radius=5 * S).mask()
    inner2 = Shape(w, h).rect((w * 0.100 + 4 * S, h * 0.070 + 4 * S, w * 0.900 - 4 * S, h * 0.930 - 4 * S), radius=5 * S).mask()
    border = np.clip((rule.mask() - inner) + (rule2 - inner2), 0, 1) * sheet
    p.part(border, paint.Material(
        [(0.0, "#d4483a"), (0.5, "#a82a20"), (1.0, "#5c1009")],
        spec=0.1, rim=0.2, rim_color="#ff8a6a", ambient=0.5, depth=3, seam=0.2, shade_mix=0.6, value=0.34),
        seed=2, depth=2.4, contact=0.2)

    # corner kanok in faded red
    orn = Shape(w, h)
    for sgn_x, sgn_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        ox = w * (0.5 + sgn_x * 0.355)
        oy = h * (0.5 + sgn_y * 0.408)
        for poly in thai.kanok(ox, oy, w * 0.085, -90 if sgn_y > 0 else 90, depth=1, flip=sgn_x < 0):
            orn.polygon(poly)
    p.part(orn.mask() * sheet * 0.42, paint.Material(
        [(0.0, "#c86a52"), (0.5, "#a03a28"), (1.0, "#6a1c10")],
        spec=0.05, rim=0.0, ambient=0.6, depth=3, seam=0.0, shade_mix=0.5, value=0.3),
        seed=3, depth=2.0, contact=0.0)

    # อายุกระดาษ — foxing and a faint fold crease
    age = core.fbm(w, h, 4, 5, 31)
    p.img = core.over(p.img, np.ones_like(p.img) * rgb("#c9a870"),
                      np.clip((age - 0.62) * 2.2, 0, 1) * sheet * 0.30)
    crease = np.clip(1.0 - np.abs(np.mgrid[0:h, 0:w][1].astype(np.float32) - w * 0.5) / (7 * S), 0, 1)
    p.darken(crease * sheet, 0.10)
    return _finish_prop(p, [sheet], bloom=0.12, exposure=1.0, sat=1.0)


# ==========================================================================
# small offerings and UI furniture
# ==========================================================================


def lotus(w=440, h=440):
    S = w / 440.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.5, -0.8), depth_scale=w / 340.0)
    masks = []
    petal = paint.Material(
        [(0.0, "#fff0f4"), (0.22, "#ffc6d8"), (0.52, "#ef7fa4"), (0.80, "#a8305a"), (1.0, "#43101f")],
        spec=0.28, spec_color="#fff4f8", spec_power=26, rim=0.5, rim_color="#ffd0dd",
        ambient=0.24, depth=9, grain=0.08, seam=0.42, shade_mix=0.80, value=0.42,
    )
    for row in range(3):
        m = _shape(w, h, thai.lotus_flower(w * 0.5, h * 0.80, w * (0.40 - row * 0.095), 1))
        p.part(m, petal, seed=1 + row, depth=8 - row * 1.5, contact=0.42)
        masks.append(m)
    core_m = Shape(w, h).ellipse((w * 0.44, h * 0.63, w * 0.56, h * 0.72)).mask()
    p.part(core_m, paint.Material([(0.0, "#ffe9a0"), (0.5, "#d9a63a"), (1.0, "#6b4a10")],
                                  spec=0.3, rim=0.3, rim_color="#fff0c0", ambient=0.34, depth=6, seam=0.3),
           seed=9, depth=5, contact=0.3)
    masks.append(core_m)
    return _finish_prop(p, masks)


def temple_bell(w=440, h=560):
    S = w / 440.0
    img = core.canvas(w, h, "#0a0503")
    p = Painter(img, light=(-0.55, -0.8), depth_scale=w / 340.0)
    masks = []
    cx = w / 2
    loop = _shape(w, h, [[(cx - 26 * S, h * 0.16), (cx - 14 * S, h * 0.16), (cx - 14 * S, h * 0.05), (cx - 26 * S, h * 0.05)],
                         [(cx + 14 * S, h * 0.16), (cx + 26 * S, h * 0.16), (cx + 26 * S, h * 0.05), (cx + 14 * S, h * 0.05)],
                         [(cx - 26 * S, h * 0.075), (cx + 26 * S, h * 0.075), (cx + 26 * S, h * 0.035), (cx - 26 * S, h * 0.035)]])
    p.part(loop, paint.BRONZE_DARK, seed=1, depth=6, contact=0.0)
    masks.append(loop)
    body = _shape(w, h, [
        quad((cx - w * 0.11, h * 0.15), (cx - w * 0.30, h * 0.44), (cx - w * 0.37, h * 0.80), 30)
        + [(cx + w * 0.37, h * 0.80)]
        + quad((cx + w * 0.37, h * 0.80), (cx + w * 0.30, h * 0.44), (cx + w * 0.11, h * 0.15), 30)])
    p.part(body, paint.BRASS, seed=2, depth=26, contact=0.4)
    masks.append(body)
    lip = _shape(w, h, [[(cx - w * 0.40, h * 0.795), (cx + w * 0.40, h * 0.795),
                         (cx + w * 0.375, h * 0.855), (cx - w * 0.375, h * 0.855)]])
    p.part(lip, paint.BRASS, seed=3, depth=8, contact=0.3)
    masks.append(lip)
    band = Shape(w, h)
    for i in range(7):
        bx = cx + (i - 3) * w * 0.105
        for poly in thai.kanok(bx, h * 0.63, w * 0.062, -90, depth=0):
            band.polygon(poly)
    p.darken(blur_a(band.mask() * body, 3 * S), 0.32)
    clap = _shape(w, h, [[(cx - 5 * S, h * 0.80), (cx + 5 * S, h * 0.80), (cx + 5 * S, h * 0.93), (cx - 5 * S, h * 0.93)],
                         [(cx - 22 * S, h * 0.905), (cx + 22 * S, h * 0.905), (cx + 18 * S, h * 0.975), (cx - 18 * S, h * 0.975)]])
    p.part(clap, paint.BRONZE_DARK, seed=4, depth=7, contact=0.35)
    masks.append(clap)
    return _finish_prop(p, masks)


def kanok_corner(w=460, h=460):
    S = w / 460.0
    img = core.canvas(w, h, "#000000")
    p = Painter(img, light=(-0.5, -0.8), depth_scale=w / 360.0)
    orn = Shape(w, h)
    for poly in thai.kanok(w * 0.10, h * 0.10, w * 0.55, 42, depth=3):
        orn.polygon(poly)
    for poly in thai.kanok(w * 0.10, h * 0.10, w * 0.34, 78, depth=1):
        orn.polygon(poly)
    for poly in thai.kanok(w * 0.10, h * 0.10, w * 0.34, 6, depth=1, flip=True):
        orn.polygon(poly)
    m = orn.mask()
    p.part(m, paint.GOLD, seed=1, depth=5, contact=0.0)
    return _finish_prop(p, [m], bloom=0.3)


# ==========================================================================
# particle and tiling textures
# ==========================================================================


def smoke_puff(w=256, h=256):
    n = core.fbm(w, h, 3, 5, 55)
    a = radial_falloff(w, h, 0.5, 0.5, 0.5, 0.5, 1.9)
    a = np.clip(a * (0.45 + 0.85 * n) - 0.06, 0, 1) ** 1.25
    a = blur_a(a, 5.0)
    a *= radial_falloff(w, h, 0.5, 0.5, 0.5, 0.5, 1.0)
    body = core.linear_gradient(w, h, [(0.0, "#ffffff"), (1.0, "#cfc6bb")])
    return body, a * 0.92


def ember(w=160, h=160):
    core_a = radial_falloff(w, h, 0.5, 0.5, 0.11, 0.11, 1.2)
    glow_a = radial_falloff(w, h, 0.5, 0.5, 0.5, 0.5, 2.6)
    a = np.clip(core_a + glow_a * 0.55, 0, 1)
    img = core.radial_gradient(w, h, [(0.0, "#fffbe8"), (0.16, "#ffcf6a"), (0.42, "#ff7a1e"), (1.0, "#8a1f00")])
    return img, a


def film_grain(size=512, seed=3):
    """Per-pixel noise — tiles seamlessly because no filter crosses the edge."""
    rs = np.random.RandomState(seed)
    n = rs.normal(0.5, 0.17, (size, size)).astype(np.float32)
    g = np.clip(n, 0, 1)
    return np.dstack([g, g, g]), np.full((size, size), 1.0, np.float32)


def paper_tile(size=512, seed=11):
    """Mirror-tiled fibre texture, so it repeats without a visible seam."""
    q = size // 2
    n = core.fbm(q, q, 5, 5, seed)
    rs = np.random.RandomState(seed)
    fib = Shape(q, q)
    for _ in range(260):
        fx, fy = rs.rand() * q, rs.rand() * q
        a = rs.rand() * math.pi
        ln = (6 + rs.rand() * 26)
        fib.line([(fx, fy), (fx + math.cos(a) * ln, fy + math.sin(a) * ln)], width=1)
    n = np.clip(n * 0.7 + fib.mask() * 0.3, 0, 1)
    top = np.concatenate([n, n[:, ::-1]], axis=1)
    full = np.concatenate([top, top[::-1, :]], axis=0)
    img = core._ramp(full, [(0.0, "#efe0c4"), (0.45, "#f6ecd6"), (1.0, "#fdf7e8")])
    return img, np.full((size, size), 1.0, np.float32)
