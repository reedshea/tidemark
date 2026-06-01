#!/usr/bin/env python3
"""
Experimental visual styles for the Tidemark ribbon — three art-historical
treatments of the same tide data, to learn what reads well on the IT8951 e-ink
panel (16-level grayscale, bistable, prone to banding/ghosting in soft fills).

  - render_sumi      : Japanese ink wash (sumi-e). Soft gray washes + a single
                       confident brushstroke for the tide. Deliberately leans on
                       tonal washes — the case e-ink handles *worst* (banding),
                       so it's the honest stress test of the panel.
  - render_durer     : Dürer copperplate engraving. Tone built entirely from
                       fine, disciplined cross-hatching; the moon is an engraved
                       sphere. Pure black-on-white — what e-ink loves.
  - render_rembrandt : Rembrandt etching. Looser, sketchier hatching, lots of
                       open paper, broken irregular lines. Also pure line, but
                       gestural rather than mechanical.

Each takes the same ctx dict that ribbon.render() consumes and returns an
8-bit ("L") PIL image sized for the panel. All output is quantized to 16 gray
levels at the end so the preview reflects what the GC16 panel can actually show.
"""

import math
import random

from PIL import Image, ImageDraw, ImageChops, ImageFilter

from render import theme as T

SS = 2  # supersample factor for crisp edges
M2FT = 3.28084

# --- shared art-board geometry (independent of the production ribbon layout) --
W, H = T.WIDTH, T.HEIGHT
PLOT_L, PLOT_R = 150, W - 150
SEA_Y = H - 210                 # the horizon / still-water baseline
CURVE_TOP = 500                 # highest a high tide reaches on the board
MOON_CX, MOON_CY, MOON_R = W - 360, 380, 165


def _q16(img):
    """Quantize to 16 evenly spaced gray levels — the GC16 panel's real gamut."""
    return img.point(lambda v: round(v / 255 * 15) * 17)


class Board:
    """A supersampled drawing board; all public coords are logical (1x)."""

    def __init__(self, bg=255):
        self.img = Image.new("L", (W * SS, H * SS), bg)
        self.d = ImageDraw.Draw(self.img)

    def _p(self, pts):
        return [(int(round(x * SS)), int(round(y * SS))) for x, y in pts]

    def line(self, pts, fill, width=1):
        self.d.line(self._p(pts), fill=fill, width=max(1, int(width * SS)),
                    joint="curve")

    def dot(self, x, y, r, fill, outline=None, width=1):
        b = self._p([(x - r, y - r), (x + r, y + r)])
        self.d.ellipse([b[0][0], b[0][1], b[1][0], b[1][1]], fill=fill,
                       outline=outline, width=max(1, int(width * SS)))

    def text(self, xy, s, fill, style, size, anchor="la"):
        self.d.text((int(xy[0] * SS), int(xy[1] * SS)), s, fill=fill,
                    font=T.font(style, int(size * SS)), anchor=anchor)

    def region_mask(self, poly):
        m = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(m).polygon(self._p(poly), fill=255)
        return m

    def paint_through(self, mask, color):
        """Paint a flat color everywhere `mask` is set."""
        self.img.paste(color, (0, 0), mask)
        self.d = ImageDraw.Draw(self.img)

    def hatch(self, mask, angle_deg, spacing, fill=0, width=1,
              jitter=0.0, prob=1.0, rng=None, dash=None):
        """Draw straight hatch lines at `angle_deg`, clipped to `mask`.

        spacing/width/jitter are logical px. prob<1 randomly drops lines (sketch
        feel); dash=(on,off) breaks lines into strokes."""
        layer = Image.new("L", self.img.size, 255)
        ld = ImageDraw.Draw(layer)
        a = math.radians(angle_deg)
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx                       # normal, to step line-to-line
        diag = math.hypot(W, H)
        n = int(2 * diag / spacing)
        cx, cy = W / 2, H / 2
        for i in range(-n, n):
            if rng and prob < 1.0 and rng.random() > prob:
                continue
            off = i * spacing + (rng.uniform(-jitter, jitter) if rng else 0)
            ox, oy = cx + nx * off, cy + ny * off
            x0, y0 = ox - dx * diag, oy - dy * diag
            x1, y1 = ox + dx * diag, oy + dy * diag
            if dash and rng:
                self._dashed(ld, x0, y0, x1, y1, dash, rng)
            else:
                ld.line(self._p([(x0, y0), (x1, y1)]),
                        fill=fill, width=max(1, int(width * SS)))
        line_mask = layer.point(lambda v: 255 if v < 128 else 0)
        combined = ImageChops.darker(line_mask, mask)
        self.img.paste(fill, (0, 0), combined)
        self.d = ImageDraw.Draw(self.img)

    def _dashed(self, ld, x0, y0, x1, y1, dash, rng):
        on, off = dash
        total = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / total, (y1 - y0) / total
        s = 0.0
        while s < total:
            seg = on * rng.uniform(0.5, 1.5)
            e = min(s + seg, total)
            ld.line(self._p([(x0 + ux * s, y0 + uy * s),
                             (x0 + ux * e, y0 + uy * e)]),
                    fill=0, width=max(1, int(1 * SS)))
            s = e + off * rng.uniform(0.5, 1.5)

    def finish(self):
        return _q16(self.img.resize((W, H), Image.LANCZOS))


# --------------------------------------------------------------------------- #
#  shared tide / moon helpers
# --------------------------------------------------------------------------- #
def _mappers(ctx):
    start, end = ctx["start"], ctx["end"]
    span = (end - start).total_seconds()
    sc = ctx["scale"]
    lo, hi = sc["lo"], sc["hi"]
    rng = (hi - lo) or 1.0

    def X(dt):
        return PLOT_L + (dt - start).total_seconds() / span * (PLOT_R - PLOT_L)

    def Y(h):
        return SEA_Y - (h - lo) / rng * (SEA_Y - CURVE_TOP)

    return X, Y


def _curve(ctx, X, Y):
    s = ctx["series"]
    return [(X(t), Y(h)) for t, h in zip(s.times, s.heights)]


def _sea_poly(curve):
    return [(PLOT_L, SEA_Y)] + curve + [(PLOT_R, SEA_Y)]


def _lune(cx, cy, r, frac, illum, steps=72):
    """Polygon of the *illuminated* lune (left as paper); returns (poly,waxing)."""
    waxing = frac < 0.5
    rx = r * (1 - 2 * illum)
    poly = []
    for i in range(steps + 1):
        a = -math.pi / 2 + math.pi * i / steps
        poly.append((cx + (r if waxing else -r) * math.cos(a),
                     cy + r * math.sin(a)))
    for i in range(steps + 1):
        a = math.pi / 2 - math.pi * i / steps
        poly.append((cx + (rx if waxing else -rx) * math.cos(a),
                     cy + r * math.sin(a)))
    return poly, waxing


def _title(b, ctx, fill, style):
    loc = ctx["location"]
    nh = ctx["series"].next_high(ctx["now"])
    b.text((PLOT_L, 250), loc.get("name", "Tide"), fill, style, 70, anchor="ls")
    if nh:
        ft = nh.height * (M2FT if ctx["units"] == "ft" else 1)
        b.text((PLOT_L, 312), f"next high {nh.time.strftime('%-I:%M %p')} · "
               f"{ft:.1f}{ctx['units']}", fill, style, 34, anchor="ls")


# --------------------------------------------------------------------------- #
#  1. Japanese ink wash (sumi-e)
# --------------------------------------------------------------------------- #
def render_sumi(ctx):
    b = Board()
    X, Y = _mappers(ctx)
    curve = _curve(ctx, X, Y)
    sea = _sea_poly(curve)
    rng = random.Random(7)

    # --- sea: soft graded wash, darker with depth (the e-ink banding test) ---
    grad = Image.new("L", b.img.size, 255)
    gd = ImageDraw.Draw(grad)
    top_y = min(p[1] for p in curve)
    for yy in range(int(top_y), SEA_Y + 1):
        t = max(0.0, (yy - top_y) / max(1, (SEA_Y - top_y)))
        tone = int(232 - 150 * (t ** 1.3))          # ~232 (surface) -> ~82 deep
        gd.line([(0, int(yy * SS)), (W * SS, int(yy * SS))], fill=tone,
                width=SS)
    grad = grad.filter(ImageFilter.GaussianBlur(SS))
    # Dither the wash with fine noise: on a 16-level panel a smooth gradient
    # hard-bands, but carrying tone as noise/dot-density survives far better.
    noise = Image.effect_noise(grad.size, 26)
    grad = ImageChops.add(grad, noise, 1.0, -128)
    b.img.paste(grad, (0, 0), b.region_mask(sea))
    b.d = ImageDraw.Draw(b.img)

    # --- tide curve as one tapering, dry-edged brushstroke ---------------------
    n = len(curve)
    for i in range(n - 1):
        t = i / (n - 1)
        wln = 22 * (0.35 + 0.65 * math.sin(math.pi * t)) + rng.uniform(-2, 2)
        if t > 0.82 and rng.random() < 0.30:        # dry-brush skips at the tail
            continue
        b.line([curve[i], curve[i + 1]], fill=12, width=wln)
        b.dot(curve[i][0], curve[i][1], wln / 2, fill=12)
    # a few stray flecks trailing the stroke (splatter)
    for _ in range(40):
        px, py = rng.choice(curve)
        b.dot(px + rng.uniform(-6, 6), py + rng.uniform(8, 26),
              rng.uniform(0.5, 2.2), fill=40)

    # --- moon: soft ink-wash orb — shadow side a pale wash, lit lune reserved -
    disk_mask, dark = _moon_masks(b, ctx)
    orb = Image.new("L", b.img.size, 255)
    orb.paste(120, (0, 0), dark)
    orb = orb.filter(ImageFilter.GaussianBlur(5 * SS))   # wet, soft terminator
    b.img.paste(orb, (0, 0), disk_mask)
    b.d = ImageDraw.Draw(b.img)
    b.dot(MOON_CX, MOON_CY, MOON_R, fill=None, outline=90, width=2)

    _title(b, ctx, 20, "serif")
    _now_brush(b, ctx, X, Y, rng)
    return b.finish()


def _now_brush(b, ctx, X, Y, rng):
    nx = X(ctx["now"])
    b.dot(nx, Y(ctx["series"].height_at(ctx["now"])), 16, fill=0)


# --------------------------------------------------------------------------- #
#  2. Dürer copperplate engraving
# --------------------------------------------------------------------------- #
def render_durer(ctx):
    b = Board()
    X, Y = _mappers(ctx)
    curve = _curve(ctx, X, Y)
    sea = _sea_poly(curve)
    sea_mask = b.region_mask(sea)

    # plate frame (a fine double rule, like an old print)
    b.line([(70, 70), (W - 70, 70), (W - 70, H - 70), (70, H - 70), (70, 70)],
           fill=0, width=2)
    b.line([(84, 84), (W - 84, 84), (W - 84, H - 84), (84, H - 84), (84, 84)],
           fill=0, width=1)

    # sea tone from layered cross-hatching: every layer adds darkness with depth
    top_y = min(p[1] for p in curve)
    mid = top_y + 0.45 * (SEA_Y - top_y)
    deep = top_y + 0.72 * (SEA_Y - top_y)
    b.hatch(sea_mask, 18, 9, fill=0, width=1)                    # base tone
    b.hatch(ImageChops.darker(sea_mask, b.region_mask(
        [(PLOT_L, mid), (PLOT_R, mid), (PLOT_R, SEA_Y), (PLOT_L, SEA_Y)])),
        -18, 9, fill=0, width=1)                                 # cross => darker
    b.hatch(ImageChops.darker(sea_mask, b.region_mask(
        [(PLOT_L, deep), (PLOT_R, deep), (PLOT_R, SEA_Y), (PLOT_L, SEA_Y)])),
        90, 8, fill=0, width=1)                                  # deepest => darkest

    # the tide surface: one firm engraved contour
    b.line(curve, fill=0, width=4)
    b.line([(PLOT_L, SEA_Y), (PLOT_R, SEA_Y)], fill=0, width=2)

    _engrave_moon(b, ctx, durer=True)
    _title(b, ctx, 0, "serif")
    b.dot(X(ctx["now"]), Y(ctx["series"].height_at(ctx["now"])), 12,
          fill=255, outline=0, width=3)
    return b.finish()


# --------------------------------------------------------------------------- #
#  3. Rembrandt etching
# --------------------------------------------------------------------------- #
def render_rembrandt(ctx):
    b = Board()
    X, Y = _mappers(ctx)
    curve = _curve(ctx, X, Y)
    sea = _sea_poly(curve)
    sea_mask = b.region_mask(sea)
    rng = random.Random(11)

    top_y = min(p[1] for p in curve)
    mid = top_y + 0.5 * (SEA_Y - top_y)
    # loose diagonal hatch, denser & more layered toward the depths; lots of
    # open paper near the surface (low draw probability up high)
    b.hatch(sea_mask, 32, 12, fill=0, width=1, jitter=4, prob=0.55,
            rng=rng, dash=(60, 14))
    lower = ImageChops.darker(sea_mask, b.region_mask(
        [(PLOT_L, mid), (PLOT_R, mid), (PLOT_R, SEA_Y), (PLOT_L, SEA_Y)]))
    b.hatch(lower, -28, 13, fill=0, width=1, jitter=5, prob=0.8, rng=rng,
            dash=(80, 12))
    # a pocket of dark scribble in the deepest trough
    lowest = max(curve, key=lambda p: p[1])
    deep_poly = [(lowest[0] - 140, lowest[1]), (lowest[0] + 140, lowest[1]),
                 (lowest[0] + 140, SEA_Y), (lowest[0] - 140, SEA_Y)]
    b.hatch(ImageChops.darker(sea_mask, b.region_mask(deep_poly)), 70, 7,
            fill=0, width=1, jitter=3, prob=0.9, rng=rng)

    # the tide surface: a few overlapping sketchy strokes
    for k in range(3):
        jit = [(x + rng.uniform(-3, 3), y + rng.uniform(-3, 3)) for x, y in curve]
        b.line(jit, fill=0, width=2)
    # foreground "ground" hatching in the lower-left corner (cf. the etching)
    b.hatch(b.region_mask([(70, SEA_Y + 30), (520, SEA_Y + 30),
                           (70, H - 90)]), 35, 10, fill=0, width=1,
            jitter=6, prob=0.85, rng=rng, dash=(120, 18))

    _engrave_moon(b, ctx, durer=False, rng=rng)
    _title(b, ctx, 0, "serif")
    nx = X(ctx["now"])
    ny = Y(ctx["series"].height_at(ctx["now"]))
    for _ in range(6):                              # scratchy now-mark
        b.line([(nx + rng.uniform(-3, 3), ny - 16), (nx + rng.uniform(-3, 3),
                ny + 16)], fill=0, width=1)
    return b.finish()


def render_contour(ctx):
    """Engraving whose hatching *follows the form*: each sea line is the tide
    curve relaxed a little further toward the flat seabed, so the lines flow
    with the wave (à la the contour hatching in Dürer's hands) instead of
    ignoring it. Tone comes from spacing — lines crowd toward the depths — so
    it grades smoothly with no abrupt layer seams."""
    b = Board()
    X, Y = _mappers(ctx)
    curve = _curve(ctx, X, Y)
    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]

    # plate frame (fine double rule)
    b.line([(70, 70), (W - 70, 70), (W - 70, H - 70), (70, H - 70), (70, 70)],
           fill=0, width=2)
    b.line([(84, 84), (W - 84, 84), (W - 84, H - 84), (84, H - 84), (84, 84)],
           fill=0, width=1)

    # flow lines: interpolate every sample from the surface curve (s=0) toward
    # the flat baseline; gamma>1 bunches them gently toward the depths for tone.
    # smax<1 stops them short of the seabed so they don't pile into a muddy line.
    N, gamma, smax = 34, 1.25, 0.88
    for i in range(1, N + 1):
        s = smax * (i / N) ** gamma
        pts = [(xs[j], ys[j] * (1 - s) + SEA_Y * s) for j in range(len(xs))]
        b.line(pts, fill=0, width=1)

    b.line(curve, fill=0, width=4)                       # bold water surface
    b.line([(PLOT_L, SEA_Y), (PLOT_R, SEA_Y)], fill=0, width=2)

    _engrave_moon(b, ctx, durer=True)
    _title(b, ctx, 0, "serif")
    b.dot(X(ctx["now"]), Y(ctx["series"].height_at(ctx["now"])), 12,
          fill=255, outline=0, width=3)
    return b.finish()


# Sea-swell as a superposition of components: (amplitude px, wavelength px,
# base phase, phase-drift per line). A long lazy roller + the main swell + a
# little chop — summed, they read as rolling sets of larger and smaller waves
# rather than one mechanical sine.
_SWELL = [
    (3.6, 430.0, 0.0, 0.18),
    (4.4, 165.0, 1.7, 0.55),
    (1.6, 73.0, 3.9, 1.05),
]


def render_tufte_waves(ctx, swell=_SWELL):
    """The real production ribbon, untouched — except the engraved sea's flat
    horizontal hairlines undulate as a sum of sine swells (see _SWELL). Mostly
    Tufte, a little fun; stays well below the bold tide curve."""
    from render import ribbon as R

    def _wavy_sea(c, curve):
        full = Image.new("L", (R._s(T.WIDTH), R._s(T.HEIGHT)), T.PAPER)
        fd = ImageDraw.Draw(full)
        y = T.PLOT_TOP
        i = 0
        while y <= T.HORIZON_Y:
            pts = []
            x = T.PLOT_LEFT
            while x <= T.PLOT_RIGHT:
                yy = y + sum(a * math.sin(2 * math.pi * x / w + p + i * d)
                             for a, w, p, d in swell)
                pts.append((R._s(x), R._s(yy)))
                x += 4
            fd.line(pts, fill=T.SEA_LINE, width=max(1, R._s(1)))
            y += T.SEA_LINE_GAP
            i += 1

        mask = Image.new("L", full.size, 0)
        md = ImageDraw.Draw(mask)
        poly = [(R._s(T.PLOT_LEFT), R._s(T.HORIZON_Y))]
        poly += [(R._s(px), R._s(py)) for px, py in curve]
        poly += [(R._s(T.PLOT_RIGHT), R._s(T.HORIZON_Y))]
        md.polygon(poly, fill=255)
        c.img.paste(full, (0, 0), mask)
        c.d = ImageDraw.Draw(c.img)
        c.line([(T.PLOT_LEFT, T.HORIZON_Y), (T.PLOT_RIGHT, T.HORIZON_Y)],
               T.INK, 1)

    orig = R._draw_engraved_sea
    R._draw_engraved_sea = _wavy_sea
    try:
        img, _rect = R.render(ctx)
    finally:
        R._draw_engraved_sea = orig
    return img


def _stroke(b, x, y, ang, length, turn=0.0, steps=10, shrink=1.0, width=1):
    """A stroke that curves as it goes: start at (x,y) heading `ang`, turning
    `turn` radians each step (turn>0 curls clockwise on screen). shrink<1 shortens
    each successive step so the path spirals inward — a rolling wave lip."""
    pts = [(x, y)]
    st = length / steps
    a = ang
    for _ in range(steps):
        x += math.cos(a) * st
        y += math.sin(a) * st
        a += turn
        st *= shrink
        pts.append((x, y))
    b.line(pts, fill=0, width=width)


def _arc(b, cx, cy, r, a0, a1, width=1, n=44):
    pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / n),
            cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    b.line(pts, fill=0, width=width)


def _interp_y(xs, ys, xq):
    if xq <= xs[0]:
        return ys[0]
    if xq >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= xq:
            t = (xq - xs[i - 1]) / ((xs[i] - xs[i - 1]) or 1)
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


def render_breakers(ctx):
    """Each tidal rise drawn as a breaking wave seen from the side, rolling
    left-to-right: the rising (left) face is dark with combed strokes following
    the slope, the crest curls over into a lighter lip, and a swooping hollow
    opens beneath it. Mostly open water with deliberate dark accents."""
    b = Board()
    X, Y = _mappers(ctx)
    curve = _curve(ctx, X, Y)
    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]
    rng = random.Random(9)

    b.line([(70, 70), (W - 70, 70), (W - 70, H - 70), (70, H - 70), (70, 70)],
           fill=0, width=2)
    b.line([(84, 84), (W - 84, 84), (W - 84, H - 84), (84, H - 84), (84, 84)],
           fill=0, width=1)

    exs = sorted((X(e.time), Y(e.height), e.kind) for e in ctx["series"].extrema
                 if PLOT_L - 60 <= X(e.time) <= PLOT_R + 60)
    for xc, yc, kind in exs:
        if kind != "H":
            continue
        left = [e for e in exs if e[0] < xc - 5]
        right = [e for e in exs if e[0] > xc + 5]
        xL = max(left[-1][0] if left else PLOT_L, PLOT_L)
        xR = min(right[0][0] if right else PLOT_R, PLOT_R)
        back = [j for j in range(len(xs)) if xL <= xs[j] <= xc]
        front = [j for j in range(len(xs)) if xc <= xs[j] <= xR]
        sp = 11

        # --- rising back face (left): DARK, form-following contour lines ------
        for k in range(1, 13):
            run = [(xs[j], ys[j] + k * sp) for j in back
                   if ys[j] + k * sp <= SEA_Y - 4]
            if len(run) >= 2:
                b.line(run, fill=0, width=1)

        # --- front face: light, just a few near-surface lines, mostly open ----
        for k in range(1, 4):
            run = [(xs[j], ys[j] + k * sp) for j in front
                   if ys[j] + k * sp <= SEA_Y - 4]
            if len(run) >= 2:
                b.line(run, fill=0, width=1)

        # --- the curl: one continuous lip rolling inward off the crest tip ----
        _stroke(b, xc, yc, -0.7, 470, turn=0.42, steps=16, shrink=0.88, width=3)
        _stroke(b, xc + 6, yc + 8, -0.5, 360, turn=0.44, steps=15, shrink=0.88,
                width=1)                          # a thinner foam shell inside

    b.line(curve, fill=0, width=4)
    b.line([(PLOT_L, SEA_Y), (PLOT_R, SEA_Y)], fill=0, width=2)
    _engrave_moon(b, ctx, durer=True)
    _title(b, ctx, 0, "serif")
    return b.finish()


def _flow_strokes(b, pts, tones, rng, width=1):
    """Walk a contour polyline drawing dashes whose length follows `tones`
    (0=light → tiny ticks/blank, 1=dark → near-continuous). This builds tone
    from stroke length, not line spacing — the engraver's way."""
    on, rem = False, 0.0
    prev = pts[0]
    for i in range(1, len(pts)):
        p = pts[i]
        seg = math.hypot(p[0] - prev[0], p[1] - prev[1])
        t = tones[i]
        on_len = 3 + 40 * (t ** 1.3)
        off_len = 30 * (1 - t) + 4
        if on:
            b.line([prev, p], fill=0, width=width)
        rem -= seg
        if rem <= 0:
            on = not on
            base = on_len if on else off_len
            rem = base * rng.uniform(0.7, 1.3)
        prev = p


def render_seascape(ctx):
    """Even-spaced contour lines that follow the wave form, each broken into
    strokes whose length is driven by a shading field — short ticks where the
    water catches light, long dense strokes in the wave hollows and depths.
    Tone lives in the strokes themselves, à la the modelling in Dürer's hands."""
    b = Board()
    X, Y = _mappers(ctx)
    curve = _curve(ctx, X, Y)
    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]
    rng = random.Random(5)

    # surface shading: light from upper-left; the wave face turned away is dark
    Lx, Ly = -0.5, -0.86
    shade = []
    for j in range(len(xs)):
        a, c = max(0, j - 2), min(len(xs) - 1, j + 2)
        dx, dy = xs[c] - xs[a], ys[c] - ys[a]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = dy / L, -dx / L                  # surface normal
        if ny > 0:
            nx, ny = -nx, -ny                     # point it skyward
        shade.append(1.0 - max(0.0, nx * Lx + ny * Ly))

    # plate frame
    b.line([(70, 70), (W - 70, 70), (W - 70, H - 70), (70, H - 70), (70, 70)],
           fill=0, width=2)
    b.line([(84, 84), (W - 84, 84), (W - 84, H - 84), (84, H - 84), (84, 84)],
           fill=0, width=1)

    spacing = 15
    k = 1
    while True:
        runs, run = [], []
        valid = False
        for j in range(len(xs)):
            yy = ys[j] + k * spacing
            if yy <= SEA_Y - 4:
                valid = True
                run.append(j)
            elif len(run) >= 2:
                runs.append(run)
                run = []
            else:
                run = []
        if len(run) >= 2:
            runs.append(run)
        if not valid:
            break
        depth = k * spacing
        for run in runs:
            pts = [(xs[j], ys[j] + depth) for j in run]
            tones = []
            for j in run:
                df = min(1.0, depth / max(1.0, (SEA_Y - ys[j])))   # 0 surf→1 bed
                t = 0.08 + 0.62 * shade[j] + 0.55 * df
                tones.append(max(0.0, min(1.0, t)))
            _flow_strokes(b, pts, tones, rng)
        k += 1

    b.line(curve, fill=0, width=4)                       # the water surface
    b.line([(PLOT_L, SEA_Y), (PLOT_R, SEA_Y)], fill=0, width=2)
    _engrave_moon(b, ctx, durer=True)
    _title(b, ctx, 0, "serif")
    b.dot(X(ctx["now"]), Y(ctx["series"].height_at(ctx["now"])), 12,
          fill=255, outline=0, width=3)
    return b.finish()


def _moon_masks(b, ctx):
    """(disk_mask, dark_side_mask) for the moon at the current phase."""
    cx, cy, r = MOON_CX, MOON_CY, MOON_R
    lune, _ = _lune(cx, cy, r, ctx["moon"]["frac"], ctx["moon"]["illum"])
    disk_mask = b.region_mask(
        [(cx + r * math.cos(t), cy + r * math.sin(t))
         for t in [i * math.pi / 60 for i in range(121)]])
    dark = ImageChops.subtract(disk_mask, b.region_mask(lune))
    return disk_mask, dark


def _engrave_moon(b, ctx, durer, rng=None):
    """A hatched sphere: the shadowed side is inked with hatching, the lit lune
    left as paper. Dürer = tidy cross-hatch; Rembrandt = loose, broken strokes."""
    cx, cy, r = MOON_CX, MOON_CY, MOON_R
    _, dark = _moon_masks(b, ctx)
    if durer:
        b.hatch(dark, 22, 8, fill=0, width=1)
        b.hatch(dark, -22, 8, fill=0, width=1)       # cross => a solid dark orb
        b.hatch(dark, 90, 13, fill=0, width=1)        # third pass tightens tone
    else:
        rr = rng or random.Random(3)
        b.hatch(dark, 20, 9, fill=0, width=1, jitter=4, prob=0.85, rng=rr,
                dash=(70, 12))
        b.hatch(dark, -30, 11, fill=0, width=1, jitter=5, prob=0.7, rng=rr,
                dash=(60, 16))
    b.dot(cx, cy, r, fill=None, outline=0, width=2)
