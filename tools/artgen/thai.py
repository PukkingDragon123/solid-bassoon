"""Thai temple forms drawn as point lists.

Every generator returns polygons (lists of (x, y) pixel tuples) so the caller
can rasterise them into a `core.Shape` and light them however it likes.

Coordinates are screen-space: +x right, +y DOWN.
"""
from __future__ import annotations

import math
from .core import bezier, quad, mirror_x


# --------------------------------------------------------------------------
# ลายกนก — kanok, the flame tendril that covers every gable and pediment
# --------------------------------------------------------------------------


def kanok(x: float, y: float, size: float, angle: float = -90.0, depth: int = 3, curl: float = 1.0, flip: bool = False):
    """A kanok flame: a tapering leaf whose tip hooks over, sprouting smaller
    flames off its back.  `angle` is the direction the tip points, degrees.

    Drawn as one closed outline — an inner spiral filled as its own polygon
    just reads as a blob at ornament scale.
    """
    polys = []
    a = math.radians(angle)
    s = -1.0 if flip else 1.0
    ux, uy = math.cos(a), math.sin(a)          # along the flame
    px, py = -math.sin(a) * s, math.cos(a) * s  # across it

    def P(u, v):
        return (x + ux * u * size + px * v * size, y + uy * u * size + py * v * size)

    outer = (
        bezier(P(0.0, 0.24), P(0.34, 0.30), P(0.68, 0.21), P(0.93, 0.02), 26)
        + bezier(P(0.93, 0.02), P(1.05, -0.07), P(1.00, -0.20), P(0.84, -0.20), 18)
        + bezier(P(0.84, -0.20), P(0.90, -0.10), P(0.84, -0.02), P(0.70, 0.02), 16)
        + bezier(P(0.70, 0.02), P(0.46, 0.08), P(0.22, 0.02), P(0.02, -0.14), 24)
        + bezier(P(0.02, -0.14), P(-0.06, -0.04), P(-0.05, 0.12), P(0.0, 0.24), 16)
    )
    polys.append(outer)

    if depth > 0:
        for i, (u, v, sc, da) in enumerate(((0.24, 0.24, 0.44, 30), (0.50, 0.19, 0.34, 22), (0.72, 0.12, 0.24, 16))):
            if i >= depth:
                break
            bx, by = P(u, v)
            polys += kanok(bx, by, size * sc * curl, angle + (da if not flip else -da), depth - 2, curl, flip)
    return polys


def garuda(cx: float, cy: float, size: float):
    """ครุฑ — Garuda with wings spread, the figure at the centre of a gable.

    `size` is the wingspan; `cy` is the waist.  Back-to-front polygon order.
    """
    S = size

    def P(u, v):
        return (cx + u * S, cy - v * S)

    polys = []
    # wings, swept up and out with three scalloped feather ranks
    for sgn in (-1, 1):
        for rank, (reach, rise, thick) in enumerate(((0.46, 0.46, 0.10), (0.36, 0.36, 0.09), (0.26, 0.25, 0.08))):
            top = quad(P(sgn * 0.07, 0.06), P(sgn * reach * 0.62, rise * 1.28), P(sgn * reach, rise), 26)
            bot = quad(P(sgn * reach, rise), P(sgn * reach * 0.58, rise * 0.42), P(sgn * 0.07, 0.06 - thick), 26)
            polys.append(top + bot)
            # feather tips
            for i in range(4):
                t_ = 0.42 + i * 0.16
                fx = sgn * reach * t_
                fy = rise * (0.30 + t_ * 0.72)
                polys.append(quad(P(fx, fy), P(sgn * (reach * t_ + 0.06), fy + 0.10), P(fx + sgn * 0.02, fy - 0.06), 14))
    # tail fan
    for i in range(5):
        u = (i - 2) * 0.045
        polys.append(quad(P(u - 0.028, -0.10), P(u * 2.4, -0.40), P(u + 0.028, -0.10), 20))
    # legs and talons
    for sgn in (-1, 1):
        polys.append(
            quad(P(sgn * 0.05, -0.06), P(sgn * 0.15, -0.16), P(sgn * 0.13, -0.30), 20)
            + quad(P(sgn * 0.13, -0.30), P(sgn * 0.09, -0.34), P(sgn * 0.05, -0.28), 14)
            + quad(P(sgn * 0.05, -0.28), P(sgn * 0.08, -0.16), P(sgn * 0.02, -0.06), 16)
        )
        for k in (0.0, 0.05, 0.10):
            polys.append(quad(P(sgn * (0.05 + k), -0.29), P(sgn * (0.08 + k), -0.37), P(sgn * (0.09 + k), -0.28), 12))
    # torso
    polys.append(
        quad(P(-0.075, -0.09), P(-0.095, 0.04), P(-0.085, 0.15), 22)
        + quad(P(-0.085, 0.15), P(0.0, 0.20), P(0.085, 0.15), 20)
        + quad(P(0.085, 0.15), P(0.095, 0.04), P(0.075, -0.09), 22)
        + quad(P(0.075, -0.09), P(0.0, -0.12), P(-0.075, -0.09), 14)
    )
    # arms raised in a wai
    for sgn in (-1, 1):
        polys.append(
            quad(P(sgn * 0.08, 0.13), P(sgn * 0.21, 0.16), P(sgn * 0.235, 0.30), 22)
            + quad(P(sgn * 0.235, 0.30), P(sgn * 0.215, 0.34), P(sgn * 0.185, 0.30), 14)
            + quad(P(sgn * 0.185, 0.30), P(sgn * 0.175, 0.19), P(sgn * 0.075, 0.10), 20)
        )
    # neck + beaked head
    polys.append([P(-0.030, 0.17), P(0.030, 0.17), P(0.026, 0.235), P(-0.026, 0.235)])
    polys.append(
        quad(P(-0.052, 0.225), P(-0.062, 0.305), P(0.0, 0.335), 24)
        + quad(P(0.0, 0.335), P(0.062, 0.305), P(0.052, 0.225), 24)
        + quad(P(0.052, 0.225), P(0.0, 0.208), P(-0.052, 0.225), 14)
    )
    polys.append(
        quad(P(-0.014, 0.268), P(-0.030, 0.250), P(-0.020, 0.228), 16)
        + quad(P(-0.020, 0.228), P(0.004, 0.238), P(0.014, 0.262), 16)
    )
    # crown — the tiered มงกุฎ
    polys.append(
        quad(P(-0.058, 0.318), P(-0.048, 0.372), P(0.0, 0.392), 20)
        + quad(P(0.0, 0.392), P(0.048, 0.372), P(0.058, 0.318), 20)
        + quad(P(0.058, 0.318), P(0.0, 0.300), P(-0.058, 0.318), 14)
    )
    polys.append(quad(P(-0.026, 0.385), P(0.0, 0.470), P(0.026, 0.385), 22) + quad(P(0.026, 0.385), P(0.0, 0.372), P(-0.026, 0.385), 10))
    for sgn in (-1, 1):
        polys += kanok(cx + sgn * 0.055 * S, cy - 0.34 * S, S * 0.10, -90 + sgn * 40, depth=0, flip=sgn < 0)
    return polys


def pediment(cx: float, apex_y: float, half_w: float, height: float, with_garuda: bool = True):
    """หน้าบัน — a dense, symmetric filigree filling a temple gable.

    A central stem with alternating flames, scroll runs following each raking
    edge, and filler flames in the corners: the read of real na ban carving
    comes from density, so this deliberately overfills.
    """
    polys = []
    figure = []
    base_y = apex_y + height

    if with_garuda:
        figure += garuda(cx, base_y - height * 0.40, height * 0.92)
    else:
        polys.append([(cx - half_w * 0.03, base_y), (cx + half_w * 0.03, base_y),
                      (cx + half_w * 0.012, apex_y + height * 0.16), (cx - half_w * 0.012, apex_y + height * 0.16)])

    # scroll runs hugging each raking edge, angled along the slope
    slope = math.degrees(math.atan2(height, half_w))
    for sgn in (-1, 1):
        for i, t in enumerate((0.20, 0.38, 0.56, 0.74, 0.90)):
            ex = cx + sgn * half_w * t
            ey = apex_y + height * t
            sz = height * (0.15 + t * 0.15)
            polys += kanok(ex, ey + height * 0.055, sz, -90 - sgn * (90 - slope) * 0.72 + sgn * i * 4,
                           depth=1, flip=sgn > 0)
        # a second, finer rank tucked inside the first
        for i, t in enumerate((0.30, 0.50, 0.70, 0.86)):
            ex = cx + sgn * half_w * t * 0.72
            ey = apex_y + height * (t * 0.80 + 0.14)
            polys += kanok(ex, ey, height * (0.10 + t * 0.09), -90 - sgn * 34 - sgn * i * 8, depth=0, flip=sgn > 0)

    # corner fillers along the base line
    for sgn in (-1, 1):
        for t in (0.50, 0.70, 0.88):
            polys += kanok(cx + sgn * half_w * t, base_y - height * 0.015, height * 0.20, -90 + sgn * 24, depth=1, flip=sgn < 0)
    return polys, figure


def kanok_band(x0: float, y0: float, x1: float, y1: float, n: int, size: float, flip: bool = False):
    """A run of kanok along a line — barge boards, frames, pediment edges."""
    polys = []
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    for i in range(n):
        t = (i + 0.5) / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        polys += kanok(x, y, size * (1.0 - 0.25 * t), ang - 90, depth=1, flip=flip)
    return polys


# --------------------------------------------------------------------------
# roof furniture
# --------------------------------------------------------------------------


def chofa(x: float, y: float, h: float, flip: bool = False):
    """ช่อฟ้า — the slender bird-beak finial crowning the ridge."""
    s = -1.0 if flip else 1.0

    def P(u, v):
        return (x + u * h * s, y - v * h)

    body = (
        quad(P(0.0, 0.0), P(0.10, 0.10), P(0.13, 0.26), 18)
        + quad(P(0.13, 0.26), P(0.17, 0.52), P(0.02, 0.78), 22)
        + quad(P(0.02, 0.78), P(-0.10, 0.96), P(-0.30, 1.00), 20)
        + quad(P(-0.30, 1.00), P(-0.16, 0.90), P(-0.12, 0.74), 16)
        + quad(P(-0.12, 0.74), P(-0.04, 0.50), P(-0.06, 0.26), 18)
        + quad(P(-0.06, 0.26), P(-0.09, 0.10), P(-0.16, 0.0), 14)
    )
    crest = quad(P(0.02, 0.62), P(0.16, 0.72), P(0.05, 0.86), 16) + quad(P(0.05, 0.86), P(0.02, 0.72), P(0.02, 0.62), 8)
    foot = [P(-0.20, 0.0), P(0.17, 0.0), P(0.15, -0.09), P(-0.18, -0.09)]
    return [body, crest, foot]


def bai_raka(x0, y0, x1, y1, n: int, size: float, flip: bool = False):
    """ใบระกา — the serrated fins marching down the barge board."""
    polys = []
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    s = -1.0 if flip else 1.0
    nx, ny = -uy * s, ux * s
    for i in range(n):
        t = (i + 0.5) / n
        bx, by = x0 + dx * t, y0 + dy * t
        k = size * (0.55 + 0.45 * (1.0 - t))
        tip = (bx + nx * k * 1.15 + ux * k * 0.55, by + ny * k * 1.15 + uy * k * 0.55)
        polys.append(
            quad((bx - ux * k * 0.42, by - uy * k * 0.42), (bx + nx * k * 0.5, by + ny * k * 0.5), tip, 14)
            + quad(tip, (bx + nx * k * 0.18 + ux * k * 0.3, by + ny * k * 0.18 + uy * k * 0.3),
                   (bx + ux * k * 0.42, by + uy * k * 0.42), 14)
        )
    return polys


def hang_hong(x: float, y: float, size: float, flip: bool = False):
    """หางหงส์ — the swan-tail finial at the foot of the barge board."""
    s = -1.0 if flip else 1.0

    def P(u, v):
        return (x + u * size * s, y - v * size)

    main = (
        quad(P(0.0, 0.0), P(0.30, 0.10), P(0.52, 0.40), 22)
        + quad(P(0.52, 0.40), P(0.66, 0.62), P(0.52, 0.74), 18)
        + quad(P(0.52, 0.74), P(0.42, 0.82), P(0.30, 0.70), 14)
        + quad(P(0.30, 0.70), P(0.40, 0.66), P(0.34, 0.50), 12)
        + quad(P(0.34, 0.50), P(0.22, 0.24), P(-0.06, 0.06), 20)
    )
    barb = quad(P(0.18, 0.16), P(0.44, 0.24), P(0.40, 0.44), 16) + quad(P(0.40, 0.44), P(0.26, 0.30), P(0.18, 0.16), 10)
    return [main, barb]


def roof_tier(cx: float, ridge_y: float, half_w: float, height: float, sweep: float = 0.10):
    """One steeply-pitched tier.  Returns (field, left_barge, right_barge, ridge_line).

    The eaves flick upward at the corners the way Thai roofs do.
    """
    eave_y = ridge_y + height
    lift = height * sweep
    left = (
        [(cx, ridge_y)]
        + quad((cx, ridge_y), (cx - half_w * 0.55, ridge_y + height * 0.46), (cx - half_w, eave_y - lift), 40)
        + [(cx - half_w * 1.06, eave_y - lift * 1.5), (cx - half_w * 1.02, eave_y + height * 0.05), (cx, eave_y + height * 0.05)]
    )
    right = mirror_x(left, cx)
    field = left + list(reversed(right))
    barge_l = quad((cx, ridge_y), (cx - half_w * 0.55, ridge_y + height * 0.46), (cx - half_w, eave_y - lift), 40)
    barge_r = mirror_x(barge_l, cx)
    return field, barge_l, barge_r


def gable(cx: float, ridge_y: float, half_w: float, height: float):
    """หน้าบัน — the triangular pediment under the ridge."""
    return [(cx, ridge_y), (cx + half_w, ridge_y + height), (cx - half_w, ridge_y + height)]


# --------------------------------------------------------------------------
# columns, bases, chedi
# --------------------------------------------------------------------------


def lotus_capital(cx: float, y: float, w: float, h: float):
    """บัวหัวเสา — the lotus-bud capital that tops every column."""
    polys = [[(cx - w * 0.62, y), (cx + w * 0.62, y), (cx + w * 0.5, y + h * 0.22), (cx - w * 0.5, y + h * 0.22)]]
    petal = (
        quad((cx - w * 0.5, y), (cx - w * 0.44, y - h * 0.62), (cx, y - h * 0.98), 24)
        + quad((cx, y - h * 0.98), (cx + w * 0.44, y - h * 0.62), (cx + w * 0.5, y), 24)
    )
    polys.append(petal)
    for k in (-0.30, 0.0, 0.30):
        polys.append(
            quad((cx + w * (k - 0.16), y), (cx + w * k, y - h * 0.55), (cx + w * (k + 0.16), y), 20)
        )
    return polys


def column(cx: float, y_top: float, y_bot: float, w: float):
    taper = w * 0.08
    shaft = [
        (cx - w / 2, y_bot),
        (cx - w / 2 + taper, y_top),
        (cx + w / 2 - taper, y_top),
        (cx + w / 2, y_bot),
    ]
    base = [(cx - w * 0.72, y_bot), (cx + w * 0.72, y_bot), (cx + w * 0.60, y_bot - w * 0.55), (cx - w * 0.60, y_bot - w * 0.55)]
    return [shaft, base]


def chedi(cx: float, base_y: float, w: float, h: float):
    """A bell-shaped stupa: plinth, bell, harmika, rings, spire."""
    polys = []
    bw = w
    # stepped square plinths
    for i, (fr, hh) in enumerate(((1.00, 0.055), (0.86, 0.05), (0.74, 0.045))):
        yb = base_y - h * sum(x[1] for x in ((1.00, 0.055), (0.86, 0.05), (0.74, 0.045))[:i])
        polys.append([(cx - bw * fr / 2, yb), (cx + bw * fr / 2, yb), (cx + bw * fr * 0.47 / 1, yb - h * hh), (cx - bw * fr * 0.47, yb - h * hh)])
    y0 = base_y - h * 0.15
    # bell (องค์ระฆัง)
    bell = (
        quad((cx - bw * 0.34, y0), (cx - bw * 0.36, y0 - h * 0.20), (cx - bw * 0.24, y0 - h * 0.34), 26)
        + quad((cx - bw * 0.24, y0 - h * 0.34), (cx - bw * 0.10, y0 - h * 0.44), (cx, y0 - h * 0.45), 20)
    )
    bell = bell + mirror_x(list(reversed(bell)), cx)
    polys.append(bell)
    # harmika + rings + spire
    hy = y0 - h * 0.45
    polys.append([(cx - bw * 0.13, hy), (cx + bw * 0.13, hy), (cx + bw * 0.11, hy - h * 0.06), (cx - bw * 0.11, hy - h * 0.06)])
    ry = hy - h * 0.06
    n = 9
    for i in range(n):
        fr = 0.10 * (1 - i / (n + 1.5))
        yy = ry - h * 0.26 * i / n
        polys.append([(cx - bw * fr, yy), (cx + bw * fr, yy), (cx + bw * fr * 0.86, yy - h * 0.26 / n * 0.8), (cx - bw * fr * 0.86, yy - h * 0.26 / n * 0.8)])
    ty = ry - h * 0.26
    polys.append(quad((cx - bw * 0.022, ty), (cx, ty - h * 0.13), (cx + bw * 0.022, ty), 18))
    return polys


def prang(cx: float, base_y: float, w: float, h: float):
    """ปรางค์ — the corn-cob tower of Khmer-influenced temples."""
    polys = [[(cx - w * 0.5, base_y), (cx + w * 0.5, base_y), (cx + w * 0.44, base_y - h * 0.22), (cx - w * 0.44, base_y - h * 0.22)]]
    n = 7
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        y0 = base_y - h * (0.22 + 0.62 * t0)
        y1 = base_y - h * (0.22 + 0.62 * t1)
        w0 = w * (0.44 - 0.30 * t0)
        w1 = w * (0.44 - 0.30 * t1)
        polys.append([(cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)])
        polys.append([(cx - w0 * 1.14, y0), (cx + w0 * 1.14, y0), (cx + w0 * 1.06, y0 - h * 0.022), (cx - w0 * 1.06, y0 - h * 0.022)])
    ty = base_y - h * 0.84
    polys.append(quad((cx - w * 0.13, ty), (cx, ty - h * 0.16), (cx + w * 0.13, ty), 24))
    return polys


# --------------------------------------------------------------------------
# naga
# --------------------------------------------------------------------------


def naga_rail(x0: float, y0: float, x1: float, y1: float, thickness: float, flip: bool = False):
    """พญานาค — the serpent balustrade flanking temple stairs, head at (x0,y0)."""
    polys = []
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    body_top = [(x0 + ux * ln * t + nx * thickness * 0.5, y0 + uy * ln * t + ny * thickness * 0.5) for t in [i / 40 for i in range(41)]]
    body_bot = [(x0 + ux * ln * t - nx * thickness * 0.5, y0 + uy * ln * t - ny * thickness * 0.5) for t in [i / 40 for i in range(41)]]
    polys.append(body_top + list(reversed(body_bot)))
    # crest scales along the spine
    for i in range(14):
        t = (i + 0.5) / 14
        bx = x0 + ux * ln * t + nx * thickness * 0.5
        by = y0 + uy * ln * t + ny * thickness * 0.5
        k = thickness * 0.62
        polys.append(quad((bx - ux * k * 0.5, by - uy * k * 0.5), (bx + nx * k, by + ny * k), (bx + ux * k * 0.5, by + uy * k * 0.5), 14))
    # the reared head
    s = -1.0 if flip else 1.0
    hs = thickness * 2.5

    def P(u, v):
        return (x0 + u * hs * s, y0 - v * hs)

    head = (
        quad(P(0.0, -0.10), P(-0.42, 0.10), P(-0.44, 0.60), 22)
        + quad(P(-0.44, 0.60), P(-0.46, 1.02), P(-0.16, 1.16), 22)
        + quad(P(-0.16, 1.16), P(0.10, 1.26), P(0.16, 1.02), 18)
        + quad(P(0.16, 1.02), P(0.20, 0.82), P(0.06, 0.70), 16)
        + quad(P(0.06, 0.70), P(-0.06, 0.60), P(0.02, 0.42), 16)
        + quad(P(0.02, 0.42), P(0.14, 0.16), P(0.16, -0.10), 18)
    )
    polys.append(head)
    for i, (u, v, sc) in enumerate(((-0.36, 0.72, 0.30), (-0.30, 0.98, 0.26), (-0.06, 1.16, 0.22))):
        hx, hy = P(u, v)
        polys += kanok(hx, hy, hs * sc, -140 if not flip else -40, depth=0, flip=flip)
    return polys


# --------------------------------------------------------------------------
# lotus
# --------------------------------------------------------------------------


def lotus_flower(cx: float, cy: float, r: float, rows: int = 3):
    polys = []
    for row in range(rows):
        rr = r * (1.0 - row * 0.24)
        n = 8 - row
        for i in range(n):
            a = -math.pi / 2 + (i - (n - 1) / 2) * (math.pi * 1.55 / max(n, 1))
            tipx, tipy = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            wx, wy = -math.sin(a) * rr * 0.28, math.cos(a) * rr * 0.28
            polys.append(
                quad((cx, cy + r * 0.16), (cx + wx * 1.5 + math.cos(a) * rr * 0.5, cy + wy * 1.5 + math.sin(a) * rr * 0.5), (tipx, tipy), 18)
                + quad((tipx, tipy), (cx - wx * 1.5 + math.cos(a) * rr * 0.5, cy - wy * 1.5 + math.sin(a) * rr * 0.5), (cx, cy + r * 0.16), 18)
            )
    return polys


def lotus_base(cx: float, y: float, w: float, h: float):
    """ฐานบัว — the lotus pedestal a Buddha image sits on.

    Returns (group, polygon) pairs.  The drums have to be painted before the
    petal rows and as separate parts, or the scallops vanish into one
    silhouette and the whole base reads as a plain trapezoid.
    """
    out = []

    def slab(top, bot, halfw_top, halfw_bot):
        return [(cx - halfw_bot, bot), (cx + halfw_bot, bot), (cx + halfw_top, top), (cx - halfw_top, top)]

    out.append(("drum", slab(y - h * 1.08, y - h * 0.60, w * 0.36, w * 0.42)))
    out.append(("drum", slab(y - h * 0.64, y - h * 0.18, w * 0.42, w * 0.48)))
    out.append(("plinth", slab(y - h * 0.24, y - h * 0.12, w * 0.50, w * 0.52)))
    out.append(("plinth", slab(y - h * 0.12, y, w * 0.54, w * 0.57)))
    out.append(("plinth", slab(y - h * 1.14, y - h * 1.02, w * 0.38, w * 0.36)))

    n = 11
    for i in range(n):
        t_ = (i + 0.5) / n
        px = cx + (t_ - 0.5) * w * 0.74
        pw = w * 0.40 / n
        out.append(("petal_up", quad((px - pw, y - h * 0.60), (px, y - h * 1.02), (px + pw, y - h * 0.60), 22)))
    for i in range(n + 1):
        t_ = (i + 0.5) / (n + 1)
        px = cx + (t_ - 0.5) * w * 0.88
        pw = w * 0.46 / (n + 1)
        out.append(("petal_dn", quad((px - pw, y - h * 0.18), (px, y - h * 0.58), (px + pw, y - h * 0.18), 22)))
    return out


# --------------------------------------------------------------------------
# พระพุทธรูปปางมารวิชัย — Buddha in the subduing-Mara posture
# --------------------------------------------------------------------------


def buddha(cx: float, base_y: float, height: float):
    """Seated Buddha silhouette, layered back-to-front.

    Returns a list of (name, polygon) so the renderer can shade robe, skin,
    hair and the flame finial differently.  `height` spans lap to flame tip.
    """
    H = height
    out = []

    def P(u, v):
        """u across (fraction of H), v up from the lap line (fraction of H)."""
        return (cx + u * H, base_y - v * H)

    parts = {}

    # ---- torso: narrow waist flaring to broad shoulders --------------------
    torso_l = (
        quad(P(-0.185, 0.17), P(-0.212, 0.34), P(-0.228, 0.46), 26)
        + quad(P(-0.228, 0.46), P(-0.238, 0.552), P(-0.150, 0.586), 22)
    )
    parts["torso"] = ("skin", torso_l + [P(0.0, 0.596)] + mirror_x(list(reversed(torso_l)), cx))

    # ---- chest and belly, so the torso is not a flat slab ------------------
    parts["chest"] = (
        "skin",
        quad(P(-0.150, 0.415), P(-0.150, 0.530), P(-0.052, 0.548), 22)
        + quad(P(-0.052, 0.548), P(0.0, 0.552), P(0.052, 0.548), 12)
        + quad(P(0.052, 0.548), P(0.150, 0.530), P(0.150, 0.415), 22)
        + quad(P(0.150, 0.415), P(0.075, 0.470), P(0.0, 0.472), 20)
        + quad(P(0.0, 0.472), P(-0.075, 0.470), P(-0.150, 0.415), 20),
    )
    parts["belly"] = (
        "skin",
        quad(P(-0.142, 0.330), P(-0.120, 0.200), P(0.0, 0.186), 24)
        + quad(P(0.0, 0.186), P(0.120, 0.200), P(0.142, 0.330), 24)
        + quad(P(0.142, 0.330), P(0.070, 0.372), P(0.0, 0.376), 18)
        + quad(P(0.0, 0.376), P(-0.070, 0.372), P(-0.142, 0.330), 18),
    )

    # ---- neck with the three auspicious rings ------------------------------
    parts["neck"] = ("skin", [P(-0.074, 0.552), P(0.074, 0.552), P(0.064, 0.664), P(-0.064, 0.664)])

    # ---- elongated earlobes (tucked behind the head) -----------------------
    for s_ in (-1, 1):
        parts[f"ear{s_}"] = (
            "skin",
            quad(P(s_ * 0.092, 0.836), P(s_ * 0.148, 0.804), P(s_ * 0.134, 0.706), 20)
            + quad(P(s_ * 0.134, 0.706), P(s_ * 0.122, 0.660), P(s_ * 0.082, 0.690), 18)
            + quad(P(s_ * 0.082, 0.690), P(s_ * 0.096, 0.772), P(s_ * 0.092, 0.836), 16),
        )

    # ---- head: the classic elongated oval with a pointed chin --------------
    head_l = (
        quad(P(-0.006, 0.640), P(-0.090, 0.652), P(-0.107, 0.740), 24)
        + quad(P(-0.107, 0.740), P(-0.120, 0.818), P(-0.062, 0.866), 24)
        + quad(P(-0.062, 0.866), P(-0.026, 0.888), P(0.0, 0.890), 14)
    )
    parts["head"] = ("skin", head_l + mirror_x(list(reversed(head_l)), cx))

    # ---- เกศา: the curled hair cap and its scalloped hairline --------------
    hair_l = (
        quad(P(-0.004, 0.892), P(-0.054, 0.888), P(-0.096, 0.842), 22)
        + quad(P(-0.096, 0.842), P(-0.120, 0.808), P(-0.111, 0.768), 18)
        + quad(P(-0.111, 0.768), P(-0.060, 0.800), P(0.0, 0.795), 20)
    )
    parts["hair"] = ("hair", hair_l + mirror_x(list(reversed(hair_l)), cx))

    # ---- อุษณีษะ + เปลวรัศมี: cranial bump and the flame of wisdom --------
    parts["ushnisha"] = (
        "hair",
        quad(P(-0.054, 0.884), P(0.0, 0.952), P(0.054, 0.884), 24)
        + quad(P(0.054, 0.884), P(0.0, 0.868), P(-0.054, 0.884), 14),
    )
    parts["flame"] = (
        "flame",
        quad(P(-0.032, 0.916), P(-0.054, 0.980), P(-0.021, 1.030), 22)
        + quad(P(-0.021, 1.034), P(-0.004, 1.062), P(0.0, 1.108), 22)
        + quad(P(0.0, 1.108), P(0.021, 1.056), P(0.032, 1.010), 22)
        + quad(P(0.032, 1.010), P(0.047, 0.964), P(0.032, 0.916), 20),
    )

    # ---- สังฆาฏิ: the folded robe sash over the left shoulder --------------
    parts["sash"] = (
        "robe",
        quad(P(-0.150, 0.586), P(-0.206, 0.505), P(-0.192, 0.400), 22)
        + quad(P(-0.192, 0.400), P(-0.180, 0.280), P(-0.154, 0.180), 22)
        + [P(-0.082, 0.180)]
        + quad(P(-0.082, 0.180), P(-0.112, 0.300), P(-0.118, 0.420), 22)
        + quad(P(-0.118, 0.420), P(-0.122, 0.520), P(-0.088, 0.588), 18),
    )
    # the sash tail folded over the point of the left shoulder
    parts["sash_fold"] = (
        "robe",
        quad(P(-0.196, 0.560), P(-0.150, 0.596), P(-0.098, 0.566), 18)
        + quad(P(-0.098, 0.566), P(-0.148, 0.540), P(-0.196, 0.560), 14),
    )

    # ---- legs / lap: a wide, low, softly rounded mound ---------------------
    lap_l = (
        quad(P(-0.425, 0.008), P(-0.462, 0.088), P(-0.352, 0.152), 22)
        + quad(P(-0.352, 0.152), P(-0.190, 0.212), P(0.0, 0.214), 22)
    )
    parts["lap"] = ("robe", lap_l + mirror_x(list(reversed(lap_l)), cx) + [P(0.425, 0.0), P(-0.425, 0.0)])

    # crossed ankles with the right sole turned up
    parts["feet"] = (
        "skin",
        quad(P(-0.145, 0.050), P(0.0, 0.148), P(0.145, 0.050), 26) + quad(P(0.145, 0.050), P(0.0, 0.022), P(-0.145, 0.050), 18),
    )

    # ---- left arm resting in the lap, palm up (สมาธิ) ----------------------
    parts["arm_l"] = (
        "skin",
        quad(P(-0.214, 0.510), P(-0.312, 0.360), P(-0.268, 0.196), 26)
        + quad(P(-0.268, 0.196), P(-0.222, 0.124), P(-0.104, 0.140), 22)
        + quad(P(-0.104, 0.140), P(-0.022, 0.146), P(0.020, 0.174), 14)
        + quad(P(0.020, 0.174), P(-0.062, 0.208), P(-0.152, 0.220), 16)
        + quad(P(-0.152, 0.220), P(-0.206, 0.310), P(-0.172, 0.478), 22),
    )

    # ---- right arm hanging down, fingers touching the earth ----------------
    parts["arm_r"] = (
        "skin",
        quad(P(0.214, 0.510), P(0.314, 0.382), P(0.330, 0.216), 26)
        + quad(P(0.330, 0.216), P(0.340, 0.096), P(0.312, 0.026), 20)
        + quad(P(0.312, 0.026), P(0.272, -0.014), P(0.240, 0.038), 16)
        + quad(P(0.240, 0.038), P(0.262, 0.140), P(0.248, 0.244), 20)
        + quad(P(0.248, 0.244), P(0.222, 0.366), P(0.176, 0.478), 22),
    )
    # four fingers draping over the knee toward the earth
    for i, k in enumerate((0.0, 0.026, 0.052, 0.076)):
        w_ = 0.0105 - i * 0.0009
        drop = 0.052 - abs(i - 1.2) * 0.009
        parts[f"finger{i}"] = (
            "skin",
            quad(P(0.238 + k - w_, 0.062), P(0.238 + k - w_ * 0.7, 0.062 - drop), P(0.238 + k, 0.070 - drop), 16)
            + quad(P(0.238 + k, 0.070 - drop), P(0.238 + k + w_ * 0.7, 0.062 - drop), P(0.238 + k + w_, 0.062), 16),
        )

    order = (
        ["torso", "chest", "belly", "neck", "ear-1", "ear1", "head", "hair", "ushnisha", "flame",
         "sash", "sash_fold", "lap", "feet", "arm_l", "arm_r"]
        + [f"finger{i}" for i in range(4)]
    )
    return [(parts[k][0], parts[k][1], k) for k in order]


def hair_curls(cx: float, base_y: float, height: float):
    """The rows of snail-shell curls on the hair cap."""
    H = height
    pts = []
    rows = ((0.803, 0.098, 11), (0.830, 0.092, 10), (0.855, 0.076, 8), (0.876, 0.050, 6))
    for v, half, n in rows:
        for i in range(n):
            u = -half + 2 * half * (i / max(n - 1, 1))
            r = H * 0.0122 * (1.0 - abs(u) / (half + 1e-6) * 0.22)
            pts.append((cx + u * H, base_y - v * H, r))
    return pts
