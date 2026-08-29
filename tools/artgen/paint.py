"""Material + lighting compositor.

Parts are painted back-to-front.  Each part casts a contact shadow onto
whatever is already behind it, then gets its own diffuse shading, specular,
rim light and a dark seam at the silhouette — which is what stops a pile of
polygons from reading as one flat blob.
"""
from __future__ import annotations

import numpy as np
from . import core
from .core import blur_a, over, rgb, shade, specular, edge_light, ao


class Material:
    def __init__(
        self,
        ramp,                    # colour stops for the body of the material
        *,
        spec: float = 0.0,       # specular strength
        spec_color: str = "#ffffff",
        spec_power: float = 30.0,
        rim: float = 0.0,        # rim-light strength
        rim_color: str = "#ffd98a",
        ambient: float = 0.34,
        depth: float = 16.0,     # how rounded the fake normals are
        grain: float = 0.0,      # surface mottle amount
        grain_cells: int = 26,
        seam: float = 0.55,      # dark line at the silhouette
        vertical: bool = True,   # ramp runs down the part, else across
        shade_mix: float = 0.72, # how much the ramp follows light vs position
        value: float = 0.5,      # how much value (vs hue) the light carries
    ):
        self.ramp, self.spec, self.spec_color, self.spec_power = ramp, spec, spec_color, spec_power
        self.rim, self.rim_color, self.ambient, self.depth = rim, rim_color, ambient, depth
        self.grain, self.grain_cells, self.seam, self.vertical = grain, grain_cells, seam, vertical
        self.shade_mix, self.value = shade_mix, value


# ---------------------------------------------------------------- materials
GOLD = Material(
    [(0.0, "#fff6d8"), (0.16, "#ffdf92"), (0.40, "#e0a938"), (0.66, "#a86e15"), (0.86, "#6b3f08"), (1.0, "#2e1a03")],
    spec=0.72, spec_color="#fffbe8", spec_power=24, rim=0.5, rim_color="#ffd98a",
    ambient=0.16, depth=14, grain=0.09, seam=0.6, shade_mix=0.80, value=0.42,
)
GOLD_DEEP = Material(
    [(0.0, "#ffeab2"), (0.20, "#f0c264"), (0.46, "#bd8420"), (0.72, "#7d4d0c"), (1.0, "#241304")],
    spec=0.55, spec_color="#ffeec2", spec_power=20, rim=0.42, rim_color="#ffcd7d",
    ambient=0.14, depth=16, grain=0.11, seam=0.64, shade_mix=0.82, value=0.40,
)
# Soft, seamless variant for forms that must swell out of a surface rather
# than sit on it — a chest inside a torso, a cheek inside a face.
GOLD_SOFT = Material(
    [(0.0, "#fff6d8"), (0.16, "#ffdf92"), (0.40, "#e0a938"), (0.66, "#a86e15"), (0.86, "#6b3f08"), (1.0, "#2e1a03")],
    spec=0.30, spec_color="#fffbe8", spec_power=18, rim=0.0,
    ambient=0.16, depth=30, grain=0.06, seam=0.0, shade_mix=0.80, value=0.42,
)

BRONZE_DARK = Material(
    [(0.0, "#c99a4e"), (0.24, "#8d6a34"), (0.55, "#4d3618"), (1.0, "#0f0903")],
    spec=0.42, spec_color="#ffe4ab", spec_power=34, rim=0.34, rim_color="#e8b563",
    ambient=0.12, depth=10, grain=0.15, seam=0.5, shade_mix=0.84, value=0.38,
)
BRASS = Material(
    [(0.0, "#f0d79a"), (0.34, "#b58c3e"), (0.7, "#77551d"), (1.0, "#2e1f08")],
    spec=0.85, spec_color="#fff4d2", spec_power=20, rim=0.42, rim_color="#ffdf9e",
    ambient=0.28, depth=12, grain=0.2, seam=0.55,
)
TEAK = Material(
    [(0.0, "#8a5a30"), (0.42, "#5c3a1d"), (1.0, "#22140a")],
    spec=0.22, spec_color="#ffd9a0", spec_power=42, rim=0.22, rim_color="#c98f4c",
    ambient=0.32, depth=18, grain=0.3, grain_cells=8, seam=0.45,
)
TEAK_LIGHT = Material(
    [(0.0, "#c9925a"), (0.45, "#96633a"), (1.0, "#4a2c16")],
    spec=0.26, spec_color="#ffe0b0", spec_power=40, rim=0.24, rim_color="#dda76a",
    ambient=0.36, depth=18, grain=0.32, grain_cells=7, seam=0.4,
)
BAMBOO = Material(
    [(0.0, "#e0c489"), (0.4, "#b8975c"), (0.78, "#7d6234"), (1.0, "#3a2b12")],
    spec=0.3, spec_color="#fff0cc", spec_power=36, rim=0.3, rim_color="#e6cd93",
    ambient=0.38, depth=14, grain=0.26, grain_cells=6, seam=0.42,
)
LACQUER_RED = Material(
    [(0.0, "#b5392c"), (0.4, "#7d1f18"), (1.0, "#2a0806")],
    spec=0.5, spec_color="#ffd0b0", spec_power=30, rim=0.35, rim_color="#e8804f",
    ambient=0.28, depth=16, grain=0.1, seam=0.5,
)
ROOF_TILE = Material(
    [(0.0, "#c46a35"), (0.45, "#8f4420"), (1.0, "#3b1a0d")],
    spec=0.18, spec_color="#ffd2a0", spec_power=44, rim=0.2, rim_color="#d98a4e",
    ambient=0.34, depth=22, grain=0.22, grain_cells=14, seam=0.4,
)
ROOF_GREEN = Material(
    [(0.0, "#3f7a52"), (0.5, "#245039"), (1.0, "#0d1f16")],
    spec=0.2, spec_color="#c8f0d6", spec_power=40, rim=0.22, rim_color="#5fae7c",
    ambient=0.32, depth=20, grain=0.2, seam=0.4,
)
STONE = Material(
    [(0.0, "#a09484"), (0.45, "#6d6355"), (1.0, "#2a251e")],
    spec=0.1, spec_color="#fff0d8", spec_power=50, rim=0.18, rim_color="#b8a68c",
    ambient=0.38, depth=24, grain=0.34, grain_cells=18, seam=0.35,
)
STONE_WARM = Material(
    [(0.0, "#c8b193"), (0.45, "#8d7658"), (1.0, "#3a2f21")],
    spec=0.12, spec_color="#fff2d8", spec_power=48, rim=0.2, rim_color="#d3ba95",
    ambient=0.4, depth=26, grain=0.32, grain_cells=16, seam=0.34,
)
WAX = Material(
    [(0.0, "#fff6e2"), (0.45, "#f0dcb4"), (1.0, "#a98d5f")],
    spec=0.35, spec_color="#fffaf0", spec_power=24, rim=0.6, rim_color="#ffd9a0",
    ambient=0.55, depth=10, grain=0.05, seam=0.3,
)
PAPER = Material(
    [(0.0, "#fbf1dc"), (0.5, "#f0e0c0"), (1.0, "#cbb289")],
    spec=0.05, spec_color="#ffffff", spec_power=60, rim=0.25, rim_color="#fff2d2",
    ambient=0.62, depth=14, grain=0.16, grain_cells=30, seam=0.22,
)
INCENSE = Material(
    [(0.0, "#8e5a4a"), (0.5, "#5d3327"), (1.0, "#25120c")],
    spec=0.16, spec_color="#ffcaa0", spec_power=46, rim=0.4, rim_color="#d98f63",
    ambient=0.42, depth=6, grain=0.12, seam=0.3,
)
ASH = Material(
    [(0.0, "#cfc4b4"), (0.5, "#9a8e7c"), (1.0, "#4b4238")],
    spec=0.04, spec_color="#ffffff", spec_power=60, rim=0.14, rim_color="#d8ccb8",
    ambient=0.5, depth=20, grain=0.4, grain_cells=40, seam=0.2,
)


class Painter:
    """Accumulates painted parts over a background image."""

    def __init__(self, img: np.ndarray, light=(-0.55, -0.85), depth_scale: float = 1.0):
        self.img = img
        self.h, self.w = img.shape[:2]
        self.light = light
        # Material depths are authored against a ~900px reference; scaling them
        # with the render keeps forms equally round at any output size.
        self.depth_scale = depth_scale
        self._grain_cache: dict[int, np.ndarray] = {}

    # -- helpers ----------------------------------------------------------
    def _grain(self, cells: int, seed: int) -> np.ndarray:
        key = cells * 1000 + (seed % 1000)
        if key not in self._grain_cache:
            self._grain_cache[key] = core.fbm(self.w, self.h, cells, 4, seed)
        return self._grain_cache[key]

    def _body(self, mask: np.ndarray, mat: Material, seed: int, lam: np.ndarray | None = None) -> np.ndarray:
        """Colour field for a material, ramped along the part's own extent
        and along the light — a gold shadow must go amber, never grey."""
        ys, xs = np.nonzero(mask > 0.02)
        if len(ys) == 0:
            return np.zeros((self.h, self.w, 3), dtype=np.float32)
        if mat.vertical:
            lo, hi = ys.min(), ys.max()
            yy = np.mgrid[0 : self.h, 0 : self.w][0].astype(np.float32)
            t = (yy - lo) / max(hi - lo, 1)
        else:
            lo, hi = xs.min(), xs.max()
            xx = np.mgrid[0 : self.h, 0 : self.w][1].astype(np.float32)
            t = (xx - lo) / max(hi - lo, 1)
        if lam is not None and mat.shade_mix > 0:
            lam_n = np.clip(lam / 1.35, 0.0, 1.0)
            t = t * (1.0 - mat.shade_mix) + (1.0 - lam_n) * mat.shade_mix
        if mat.grain:
            t = t + (self._grain(mat.grain_cells, seed) - 0.5) * mat.grain
        return core._ramp(np.clip(t, 0, 1), mat.ramp)

    # -- the one call that matters ---------------------------------------
    def part(
        self,
        mask: np.ndarray,
        mat: Material,
        *,
        seed: int = 0,
        light=None,
        contact: float = 0.7,
        contact_radius: float = None,
        depth: float = None,
        tint: np.ndarray | None = None,
        opacity: float = 1.0,
    ) -> np.ndarray:
        """Paint one part over everything drawn so far, and return the mask."""
        if mask.max() <= 0.01:
            return mask
        L = light or self.light
        d = (mat.depth if depth is None else depth) * self.depth_scale
        cr = contact_radius if contact_radius is not None else max(d * 1.8, 12.0)

        # 1. contact shadow onto what is behind
        if contact > 0:
            self.img = self.img * ao(mask, cr, contact)[..., None]

        # 2. diffuse — the ramp carries the hue shift, lam a touch of value
        lam = shade(mask, L, d, mat.ambient)
        body = self._body(mask, mat, seed, lam)
        col = body * (1.0 - mat.value + mat.value * np.clip(lam / 1.15, 0.15, 1.35))[..., None]

        # 3. specular + rim
        if mat.spec:
            sp = specular(mask, L, max(d * 0.7, 4.0), mat.spec_power)
            col = col + rgb(mat.spec_color)[None, None, :] * (sp * mat.spec)[..., None]
        if mat.rim:
            rl = edge_light(mask, max(d * 0.45, 3.0))
            col = col + rgb(mat.rim_color)[None, None, :] * (rl * mat.rim)[..., None]

        # 4. dark seam just inside the silhouette so forms separate
        if mat.seam:
            seam = edge_light(blur_a(mask, 1.0), max(d * 0.30, 2.0))
            col = col * (1.0 - seam * mat.seam * 0.55)[..., None]

        if tint is not None:
            col = col * tint[None, None, :]
        self.img = over(self.img, np.clip(col, 0, 1), mask * opacity)
        return mask

    def glow(self, mask_or_center, color: str, radius: float, strength: float = 1.0):
        """Add an emissive pool of light."""
        if isinstance(mask_or_center, tuple):
            cx, cy = mask_or_center
            g = core.radial_falloff(self.w, self.h, cx / self.w, cy / self.h, radius / self.w, radius / self.h, 2.2)
        else:
            g = blur_a(mask_or_center, radius) 
            g = g / max(g.max(), 1e-6)
        self.img = core.add_light(self.img, rgb(color), g, strength)
        return g

    def shadow(self, mask: np.ndarray, radius: float, strength: float, dx: int = 0, dy: int = 0):
        s = blur_a(np.roll(np.roll(mask, dy, 0), dx, 1), radius)
        self.img = self.img * (1.0 - s * strength)[..., None]

    def darken(self, mask: np.ndarray, strength: float):
        self.img = self.img * (1.0 - np.clip(mask, 0, 1) * strength)[..., None]
