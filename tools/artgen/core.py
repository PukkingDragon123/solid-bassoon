"""Core imaging helpers: gradients, noise, light, glass, grade.

Everything works on float32 RGB arrays in 0..1 with shape (h, w, 3),
and float32 alpha arrays in 0..1 with shape (h, w).  Pillow is used only
for rasterising polygons/curves and for the final encode.
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# --------------------------------------------------------------------------
# conversions
# --------------------------------------------------------------------------


def rgb(hexstr: str) -> np.ndarray:
    """'#e8b24a' or 'e8b24a' -> float32 array of 3 in 0..1 (sRGB)."""
    h = hexstr.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def canvas(w: int, h: int, color="#000000") -> np.ndarray:
    return np.ones((h, w, 3), dtype=np.float32) * rgb(color)


def to_pil(arr: np.ndarray, alpha: np.ndarray | None = None) -> Image.Image:
    """float RGB (+alpha) -> 8-bit PIL image, with a touch of ordered dither
    so wide smooth gradients do not band on 8-bit displays."""
    a = np.clip(arr, 0.0, 1.0)
    h, w = a.shape[:2]
    # 8x8 Bayer dither at +-0.5/255 — invisible, but kills banding.
    bayer = _bayer8()
    d = (np.tile(bayer, (h // 8 + 1, w // 8 + 1))[:h, :w] - 0.5) / 255.0
    a = np.clip(a + d[..., None], 0.0, 1.0)
    out = (a * 255.0 + 0.5).astype(np.uint8)
    if alpha is None:
        return Image.fromarray(out, "RGB")
    al = (np.clip(alpha, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(np.dstack([out, al]), "RGBA")


_BAYER_CACHE: dict[int, np.ndarray] = {}


def _bayer8() -> np.ndarray:
    if 8 not in _BAYER_CACHE:
        m = np.array([[0, 2], [3, 1]], dtype=np.float32)
        for _ in range(2):
            m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
        _BAYER_CACHE[8] = m / 64.0
    return _BAYER_CACHE[8]


def from_pil_gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float32) / 255.0


# --------------------------------------------------------------------------
# gradients
# --------------------------------------------------------------------------


def _ramp(t: np.ndarray, stops: list[tuple[float, str]]) -> np.ndarray:
    """Interpolate colour stops [(pos, hex), ...] over t in 0..1.

    Interpolation happens in linear light so gold->red ramps stay saturated
    instead of dipping through mud.
    """
    t = np.clip(t, 0.0, 1.0)
    pos = np.array([s[0] for s in stops], dtype=np.float32)
    cols = np.stack([srgb_to_linear(rgb(s[1])) for s in stops])  # (n,3)
    out = np.empty(t.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return linear_to_srgb(out)


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1 / 2.4)) - 0.055)


def linear_gradient(w: int, h: int, stops, angle_deg: float = 90.0) -> np.ndarray:
    """angle 90 = top to bottom, 0 = left to right."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(angle_deg)
    vx, vy = math.cos(a), math.sin(a)
    t = (xx / max(w - 1, 1)) * vx + (yy / max(h - 1, 1)) * vy
    lo, hi = t.min(), t.max()
    t = (t - lo) / max(hi - lo, 1e-6)
    return _ramp(t, stops)


def radial_gradient(
    w: int, h: int, stops, cx: float = 0.5, cy: float = 0.5, rx: float = 0.5, ry: float | None = None
) -> np.ndarray:
    ry = rx if ry is None else ry
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (xx / max(w - 1, 1) - cx) / max(rx, 1e-6)
    dy = (yy / max(h - 1, 1) - cy) / max(ry, 1e-6)
    return _ramp(np.sqrt(dx * dx + dy * dy), stops)


def radial_falloff(
    w: int, h: int, cx: float, cy: float, rx: float, ry: float | None = None, power: float = 2.0
) -> np.ndarray:
    """Scalar 1 at the centre easing to 0 at the ellipse edge."""
    ry = rx if ry is None else ry
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (xx / max(w - 1, 1) - cx) / max(rx, 1e-6)
    dy = (yy / max(h - 1, 1) - cy) / max(ry, 1e-6)
    d = np.sqrt(dx * dx + dy * dy)
    return np.clip(1.0 - d, 0.0, 1.0) ** power


# --------------------------------------------------------------------------
# noise
# --------------------------------------------------------------------------


def value_noise(w: int, h: int, cells: int, seed: int = 0) -> np.ndarray:
    """Smooth value noise in 0..1 built from a bicubic-ish upsample."""
    rs = np.random.RandomState(seed)
    gh = max(2, int(round(cells * h / max(w, 1))) + 1)
    gw = max(2, cells + 1)
    grid = rs.rand(gh, gw).astype(np.float32)
    small = Image.fromarray((grid * 255).astype(np.uint8), "L")
    big = small.resize((w, h), Image.BICUBIC)
    return np.asarray(big, dtype=np.float32) / 255.0


def fbm(w: int, h: int, cells: int = 4, octaves: int = 5, seed: int = 0, gain: float = 0.5) -> np.ndarray:
    """Fractal noise in 0..1."""
    total = np.zeros((h, w), dtype=np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += amp * value_noise(w, h, cells * (2**o), seed + o * 977)
        norm += amp
        amp *= gain
    n = total / max(norm, 1e-6)
    return (n - n.min()) / max(n.max() - n.min(), 1e-6)


def ridged(w: int, h: int, cells: int = 4, octaves: int = 5, seed: int = 0) -> np.ndarray:
    """Ridged fractal noise — good for wood grain, marble, cloud edges."""
    n = fbm(w, h, cells, octaves, seed)
    r = 1.0 - np.abs(n * 2.0 - 1.0)
    return (r - r.min()) / max(r.max() - r.min(), 1e-6)


def warp_field(arr: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Displace an array (2-D or 3-D) by per-pixel offsets, in pixels."""
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = np.clip(xx + dx, 0, w - 1)
    sy = np.clip(yy + dy, 0, h - 1)
    x0, y0 = np.floor(sx).astype(np.int32), np.floor(sy).astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    if arr.ndim == 2:
        fx, fy = fx[..., 0], fy[..., 0]
    a = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    b = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    return (a * (1 - fy) + b * fy).astype(np.float32)


# --------------------------------------------------------------------------
# blur / composite
# --------------------------------------------------------------------------


def _box_pass(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    """Box blur of radius r along one axis, via a summed-area table."""
    if r < 1:
        return a
    a = np.moveaxis(a, axis, 0)
    n = a.shape[0]
    pad = np.concatenate([np.repeat(a[:1], r + 1, axis=0), a, np.repeat(a[-1:], r, axis=0)], axis=0)
    cs = np.cumsum(pad, axis=0, dtype=np.float32)
    out = (cs[2 * r + 1 : 2 * r + 1 + n] - cs[:n]) / np.float32(2 * r + 1)
    return np.moveaxis(out, 0, axis)


def blur_a(a: np.ndarray, radius: float) -> np.ndarray:
    """Float-precision gaussian for masks.

    Three box passes approximate a gaussian closely, and staying in float32
    throughout is what keeps shading gradients free of the contour rings an
    8-bit intermediate would bake in.
    """
    if radius <= 0.4:
        return a.astype(np.float32)
    sigma = float(radius) * 0.55
    r = max(1, int(round(sigma * 1.4)))
    out = np.ascontiguousarray(a, dtype=np.float32)
    for _ in range(3):
        out = _box_pass(out, r, 0)
        out = _box_pass(out, r, 1)
    return out


def blur(arr: np.ndarray, radius: float) -> np.ndarray:
    """Gaussian blur that works on (h,w) or (h,w,3) float arrays."""
    if radius <= 0:
        return arr
    if arr.ndim == 2:
        return blur_a(arr, radius)
    out = np.empty_like(arr)
    for c in range(arr.shape[2]):
        out[..., c] = blur_a(arr[..., c], radius)
    return out


def over(base: np.ndarray, top: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Alpha-composite `top` onto `base` using a (h,w) mask."""
    m = np.clip(mask, 0.0, 1.0)[..., None]
    return base * (1 - m) + top * m


def screen(base: np.ndarray, top: np.ndarray, amount: np.ndarray | float = 1.0) -> np.ndarray:
    t = top * (amount[..., None] if isinstance(amount, np.ndarray) else amount)
    return 1.0 - (1.0 - np.clip(base, 0, 1)) * (1.0 - np.clip(t, 0, 1))


def add_light(base: np.ndarray, color: np.ndarray, amount: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Physically-ish light accumulation: add in linear space, back to sRGB."""
    lin = srgb_to_linear(base) + srgb_to_linear(color)[None, None, :] * (amount[..., None] * strength)
    return linear_to_srgb(np.clip(lin, 0.0, 1.0))


def multiply(base: np.ndarray, color: np.ndarray, amount: np.ndarray) -> np.ndarray:
    m = np.clip(amount, 0, 1)[..., None]
    return base * (1 - m) + base * color[None, None, :] * m


def overlay(base: np.ndarray, top: np.ndarray, amount: float = 1.0) -> np.ndarray:
    b, t = np.clip(base, 0, 1), np.clip(top, 0, 1)
    res = np.where(b <= 0.5, 2 * b * t, 1 - 2 * (1 - b) * (1 - t))
    return base * (1 - amount) + res * amount


# --------------------------------------------------------------------------
# shape rasterising (supersampled for clean edges)
# --------------------------------------------------------------------------

SS = 3  # supersample factor for masks


class Shape:
    """Draws into a supersampled L-mask, then downsamples to a float mask."""

    def __init__(self, w: int, h: int, ss: int = SS):
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new("L", (w * ss, h * ss), 0)
        self.d = ImageDraw.Draw(self.img)

    def _s(self, pts):
        return [(x * self.ss, y * self.ss) for (x, y) in pts]

    def polygon(self, pts, fill=255):
        self.d.polygon(self._s(pts), fill=fill)
        return self

    def ellipse(self, box, fill=255):
        x0, y0, x1, y1 = box
        self.d.ellipse([x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss], fill=fill)
        return self

    def rect(self, box, fill=255, radius=0):
        x0, y0, x1, y1 = box
        b = [x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss]
        if radius:
            self.d.rounded_rectangle(b, radius=radius * self.ss, fill=fill)
        else:
            self.d.rectangle(b, fill=fill)
        return self

    def line(self, pts, width=1, fill=255, joint="curve"):
        self.d.line(self._s(pts), width=max(1, int(width * self.ss)), fill=fill, joint=joint)
        return self

    def mask(self) -> np.ndarray:
        small = self.img.resize((self.w, self.h), Image.LANCZOS)
        return np.asarray(small, dtype=np.float32) / 255.0


def bezier(p0, p1, p2, p3, n=64):
    """Cubic bezier sampled into a point list."""
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.array(p, dtype=np.float32) for p in (p0, p1, p2, p3))
    pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * (t**2) * p2 + (t**3) * p3
    return [tuple(p) for p in pts]


def quad(p0, p1, p2, n=48):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.array(p, dtype=np.float32) for p in (p0, p1, p2))
    pts = ((1 - t) ** 2) * p0 + 2 * (1 - t) * t * p1 + (t**2) * p2
    return [tuple(p) for p in pts]


def mirror_x(pts, axis: float):
    return [(2 * axis - x, y) for (x, y) in pts]


# --------------------------------------------------------------------------
# lighting helpers
# --------------------------------------------------------------------------


def shade(mask: np.ndarray, light_dir=(-0.6, -0.8), depth: float = 18.0, ambient: float = 0.45) -> np.ndarray:
    """Fake normals from a mask's blurred gradient -> lambert term in 0..1.

    Gives painted props a believable rounded read without any 3-D.
    """
    soft = blur_a(mask, depth)
    gy, gx = np.gradient(soft)
    nz = 1.0 / max(depth, 1.0) * 6.0
    nx, ny = -gx * depth, -gy * depth
    ln = math.sqrt(light_dir[0] ** 2 + light_dir[1] ** 2 + 0.75**2)
    lx, ly, lz = light_dir[0] / ln, light_dir[1] / ln, 0.75 / ln
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    lam = (nx * lx + ny * ly + nz * lz) / norm
    return np.clip(ambient + (1.0 - ambient) * np.clip(lam, 0, 1) * 1.35, 0.0, 1.35)


def specular(mask: np.ndarray, light_dir=(-0.6, -0.8), depth: float = 14.0, power: float = 28.0) -> np.ndarray:
    soft = blur_a(mask, depth)
    gy, gx = np.gradient(soft)
    nz = 6.0 / max(depth, 1.0)
    nx, ny = -gx * depth, -gy * depth
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    nx, ny, nz = nx / norm, ny / norm, nz / norm
    ln = math.sqrt(light_dir[0] ** 2 + light_dir[1] ** 2 + 0.75**2)
    lx, ly, lz = light_dir[0] / ln, light_dir[1] / ln, 0.75 / ln
    hx, hy, hz = lx, ly, lz + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    spec = np.clip(nx * hx / hn + ny * hy / hn + nz * hz / hn, 0, 1) ** power
    return spec * mask


def edge_light(mask: np.ndarray, radius: float = 6.0) -> np.ndarray:
    """Thin rim just inside a shape's silhouette."""
    inner = blur_a(mask, radius)
    return np.clip((mask - inner) * 2.4, 0, 1)


def ao(mask: np.ndarray, radius: float = 30.0, strength: float = 0.75) -> np.ndarray:
    """Contact shadow field around/below a shape (1 = fully lit)."""
    s = blur_a(mask, radius)
    return np.clip(1.0 - s * strength, 0.0, 1.0)


# --------------------------------------------------------------------------
# post
# --------------------------------------------------------------------------


def bloom(arr: np.ndarray, threshold: float = 0.72, radius: float = 34.0, intensity: float = 0.55) -> np.ndarray:
    lum = arr.max(axis=2)
    hi = np.clip((lum - threshold) / max(1 - threshold, 1e-6), 0, 1)
    src = arr * hi[..., None]
    glow = blur(src, radius) * 0.6 + blur(src, radius * 2.6) * 0.4
    return screen(arr, glow, intensity)


def vignette(arr: np.ndarray, amount: float = 0.35, softness: float = 1.25) -> np.ndarray:
    h, w = arr.shape[:2]
    v = radial_falloff(w, h, 0.5, 0.5, 0.78, 0.82, power=softness)
    return arr * (1.0 - amount + amount * v[..., None])


def grade(arr: np.ndarray, lift=(0.0, 0.0, 0.0), gamma=(1.0, 1.0, 1.0), gain=(1.0, 1.0, 1.0), sat: float = 1.0):
    a = np.clip(arr, 0, 1)
    a = a * np.array(gain, dtype=np.float32) + np.array(lift, dtype=np.float32)
    a = np.clip(a, 1e-5, 1.0) ** (1.0 / np.array(gamma, dtype=np.float32))
    if sat != 1.0:
        lum = (a * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).sum(axis=2, keepdims=True)
        a = lum + (a - lum) * sat
    return np.clip(a, 0, 1)


def filmic(arr: np.ndarray, exposure: float = 0.82) -> np.ndarray:
    """Gentle highlight rolloff so candle flames read hot instead of clipped.

    The ACES fit expects *linear* light; feeding it sRGB values washes every
    midtone toward white, so convert in and back out.
    """
    x = srgb_to_linear(np.clip(arr, 0, 1)) * exposure
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return linear_to_srgb(np.clip(y, 0, 1))


def chroma_shift(arr: np.ndarray, px: float = 1.2) -> np.ndarray:
    """Very slight lens fringing toward the frame edges."""
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    dx, dy = (xx - cx) / cx, (yy - cy) / cy
    out = arr.copy()
    out[..., 0] = warp_field(arr[..., 0], dx * px, dy * px)
    out[..., 2] = warp_field(arr[..., 2], -dx * px, -dy * px)
    return out


def finish(arr: np.ndarray, *, bloom_amt=0.5, vig=0.34, ca=1.0, exposure=0.95, sat=1.06, tone=0.78) -> np.ndarray:
    # Blend the tonemap back with the source: full ACES crushes shadow detail
    # that a candle-lit interior needs.
    a = arr * (1.0 - tone) + filmic(arr, exposure) * tone
    a = bloom(a, 0.7, 40, bloom_amt)
    if ca:
        a = chroma_shift(a, ca)
    a = vignette(a, vig)
    return grade(a, sat=sat)
