#!/usr/bin/env python3
"""
E-ink post-processing for the supersampled canvas.

Two pure-Pillow techniques (Pillow is the only dependency that ships to the Pi):

  * linear-light downsampling — antialiasing/coverage averaging is correct only
    in linear light; Pillow's resize otherwise averages gamma-encoded values,
    which makes black-on-white edge ramps too dark and visibly harsher.
  * GC16 quantization — snap to the 16 levels the panel actually renders, used
    to preview real-device banding from the simulator (TIDE_POSTERIZE16).
"""

from PIL import Image

GC16_LEVELS = 16

# sRGB-ish gamma. A plain 2.2 power (not the piecewise sRGB curve) is enough
# here and is exactly invertible, which keeps the round-trip clean.
_GAMMA = 2.2
_SRGB_TO_LIN = [round(((i / 255.0) ** _GAMMA) * 255.0) for i in range(256)]
_LIN_TO_SRGB = [round(((i / 255.0) ** (1.0 / _GAMMA)) * 255.0) for i in range(256)]

# Nearest-of-16 quantization LUT, landing exactly on GC16 levels.
_QUANTIZE = [round(i / 255.0 * (GC16_LEVELS - 1)) * 255 // (GC16_LEVELS - 1)
             for i in range(256)]

_FILTERS = {
    "lanczos": Image.LANCZOS,
    "bicubic": Image.BICUBIC,
    "bilinear": Image.BILINEAR,
    "box": Image.BOX,
    "hamming": Image.HAMMING,
}


def resolve_filter(name):
    return _FILTERS.get((name or "lanczos").lower(), Image.LANCZOS)


def downsample_linear(img, size, resample):
    """Downsample `img` ("L") to `size`, averaging in linear light."""
    lin = img.point(_SRGB_TO_LIN)            # sRGB -> linear (8-bit LUT)
    lin = lin.resize(size, resample)         # average in linear light
    return lin.point(_LIN_TO_SRGB)           # linear -> sRGB


def quantize_gc16(img):
    """Snap an "L" image to the panel's 16 GC16 levels (nearest, no dither)."""
    return img.point(_QUANTIZE)
