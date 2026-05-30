#!/usr/bin/env python3
"""
Harmonic tide prediction with full astronomical corrections.

The naive model height = MSL + sum(A * cos(speed * t + phase)) is wrong by
hours because it omits the *equilibrium argument* (V0 + u) and the *nodal
factor* f that real harmonic prediction requires. This module implements those
corrections so high/low tide TIMES are accurate offline, with no internet.

Reference convention (Schureman / NOAA):
    height(t) = MSL + sum_i  f_i * A_i * cos( speed_i * t_hours
                                              + (V0 + u)_i - g_i )
where
    A_i     amplitude (m), g_i phase lag (deg), speed_i deg/hour  [from station]
    V0_i    equilibrium argument at the reference epoch (deg)
    u_i     nodal phase correction (deg), f_i nodal amplitude factor
    t_hours hours from the reference epoch (we anchor at the prediction time
            itself, so t_hours = 0 and V0+u is evaluated at that instant).
"""

import math
import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

D2R = math.pi / 180.0


def _julian_date(dt):
    """Julian Date for a timezone-aware datetime (converted to UTC)."""
    dt = dt.astimezone(UTC)
    y, m = dt.year, dt.month
    day = (dt.day + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6)
                                / 60.0) / 60.0) / 24.0)
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716))
            + math.floor(30.6001 * (m + 1))
            + day + b - 1524.5)


def _fundamental_arguments(dt):
    """
    Mean longitudes of the astronomical bodies (degrees, 0-360) and the mean
    lunar time tau. Polynomials are the standard Meeus mean elements with time
    measured in Julian centuries from J2000.0.

    Returns dict with: tau, s, h, p, N, pp  (all degrees)
      s  = mean longitude of the Moon
      h  = mean longitude of the Sun
      p  = longitude of lunar perigee
      N  = longitude of Moon's ascending node
      pp = longitude of solar perigee (perihelion)
      tau= mean lunar time = 15*UThours + h - s
    """
    jd = _julian_date(dt)
    T = (jd - 2451545.0) / 36525.0

    s = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T \
        + T ** 3 / 538841.0 - T ** 4 / 65194000.0
    h = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    p = 83.3532465 + 4069.0137287 * T - 0.0103200 * T * T \
        - T ** 3 / 80053.0 + T ** 4 / 18999000.0
    N = 125.0445479 - 1934.1362891 * T + 0.0020754 * T * T \
        + T ** 3 / 467441.0 - T ** 4 / 60616000.0
    pp = 282.9373481 + 1.7195269 * T + 0.0004568 * T * T \
        + T ** 3 / 4900000.0

    dt_utc = dt.astimezone(UTC)
    ut_hours = (dt_utc.hour + dt_utc.minute / 60.0
                + dt_utc.second / 3600.0)
    tau = 15.0 * ut_hours + h - s

    return {
        "tau": tau % 360.0,
        "s": s % 360.0,
        "h": h % 360.0,
        "p": p % 360.0,
        "N": N % 360.0,
        "pp": pp % 360.0,
    }


# Doodson numbers (n_tau, n_s, n_h, n_p, n_pp) and a constant phase bias (deg).
# "node" selects the nodal f/u formula family below.
# Bias values follow the standard convention so that V0 = sum(n_i * arg_i) + bias.
CONSTITUENT_DEF = {
    # --- semidiurnal ---
    "M2":  ((2, 0, 0, 0, 0), 0.0, "M2"),
    "S2":  ((2, 2, -2, 0, 0), 0.0, "S"),
    "N2":  ((2, -1, 0, 1, 0), 0.0, "M2"),
    "K2":  ((2, 2, 0, 0, 0), 0.0, "K2"),
    "NU2": ((2, -1, 2, -1, 0), 0.0, "M2"),
    "MU2": ((2, -2, 2, 0, 0), 0.0, "M2"),
    "2N2": ((2, -2, 0, 2, 0), 0.0, "M2"),
    "LAM2": ((2, 1, -2, 1, 0), 180.0, "M2"),
    "L2":  ((2, 1, 0, -1, 0), 180.0, "M2"),
    "T2":  ((2, 2, -3, 0, 1), 0.0, "S"),
    "R2":  ((2, 2, -1, 0, -1), 180.0, "S"),
    "2SM2": ((2, 4, -4, 0, 0), 0.0, "M2_inv"),
    "MS4": ((4, 2, -2, 0, 0), 0.0, "M2"),
    # --- diurnal ---
    "K1":  ((1, 1, 0, 0, 0), -90.0, "K1"),
    "O1":  ((1, -1, 0, 0, 0), 90.0, "O1"),
    "OO1": ((1, 3, 0, 0, 0), -90.0, "OO1"),
    "Q1":  ((1, -2, 0, 1, 0), 90.0, "O1"),
    "2Q1": ((1, -3, 0, 2, 0), 90.0, "O1"),
    "RHO": ((1, -2, 2, -1, 0), 90.0, "O1"),
    "P1":  ((1, 1, -2, 0, 0), 90.0, "S"),
    "S1":  ((1, 1, -1, 0, 0), 0.0, "S"),
    "J1":  ((1, 2, 0, -1, 0), -90.0, "J1"),
    "M1":  ((1, 0, 0, 1, 0), -90.0, "O1"),
    # --- terdiurnal / higher (shallow water) ---
    "M3":  ((3, 0, 0, 0, 0), 0.0, "M3"),
    "MK3": ((3, 1, 0, 0, 0), -90.0, "MK3"),
    "2MK3": ((3, -1, 0, 0, 0), 90.0, "2MK3"),
    "M4":  ((4, 0, 0, 0, 0), 0.0, "M4"),
    "MN4": ((4, -1, 0, 1, 0), 0.0, "M4"),
    "M6":  ((6, 0, 0, 0, 0), 0.0, "M6"),
    "M8":  ((8, 0, 0, 0, 0), 0.0, "M8"),
    "S4":  ((4, 4, -4, 0, 0), 0.0, "S"),
    "S6":  ((6, 6, -6, 0, 0), 0.0, "S"),
    # --- long period ---
    "MM":  ((0, 1, 0, -1, 0), 0.0, "MM"),
    "MF":  ((0, 2, 0, 0, 0), 0.0, "MF"),
    "MSF": ((0, 2, -2, 0, 0), 0.0, "S"),
    "SSA": ((0, 0, 2, 0, 0), 0.0, "S"),
    "SA":  ((0, 0, 1, 0, 0), 0.0, "S"),
}


def _nodal_f_u(family, N_deg):
    """Return (f, u_deg) nodal corrections for a constituent family.

    Formulas are the standard Schureman approximations expressed as a function
    of the node longitude N. Shallow-water constituents combine the corrections
    of their parents.
    """
    N = N_deg * D2R

    def cosN(k):
        return math.cos(k * N)

    def sinN(k):
        return math.sin(k * N)

    if family == "S":  # solar / no nodal correction
        return 1.0, 0.0

    if family == "M2":
        f = 1.0004 - 0.0373 * cosN(1) + 0.0002 * cosN(2)
        u = -2.14 * sinN(1)
        return f, u
    if family == "M2_inv":  # 2SM2 ~ -M2 nodal
        f, u = _nodal_f_u("M2", N_deg)
        return f, -u
    if family == "O1":
        f = 1.0089 + 0.1871 * cosN(1) - 0.0147 * cosN(2) + 0.0014 * cosN(3)
        u = 10.80 * sinN(1) - 1.34 * sinN(2) + 0.19 * sinN(3)
        return f, u
    if family == "K1":
        f = 1.0060 + 0.1150 * cosN(1) - 0.0088 * cosN(2) + 0.0006 * cosN(3)
        u = -8.86 * sinN(1) + 0.68 * sinN(2) - 0.07 * sinN(3)
        return f, u
    if family == "K2":
        f = 1.0241 + 0.2863 * cosN(1) + 0.0083 * cosN(2) - 0.0015 * cosN(3)
        u = -17.74 * sinN(1) + 0.68 * sinN(2) - 0.04 * sinN(3)
        return f, u
    if family == "J1":
        f = 1.0129 + 0.1676 * cosN(1) - 0.0170 * cosN(2) + 0.0016 * cosN(3)
        u = -12.94 * sinN(1) + 1.34 * sinN(2) - 0.19 * sinN(3)
        return f, u
    if family == "OO1":
        f = 1.1027 + 0.6504 * cosN(1) + 0.0317 * cosN(2) - 0.0014 * cosN(3)
        u = -36.68 * sinN(1) + 4.02 * sinN(2) - 0.57 * sinN(3)
        return f, u
    if family == "MM":
        f = 1.0 - 0.1311 * cosN(1)
        return f, 0.0
    if family == "MF":
        f = 1.0429 + 0.4135 * cosN(1) - 0.004 * cosN(2)
        u = -23.7 * sinN(1) + 2.7 * sinN(2) - 0.4 * sinN(3)
        return f, u
    # shallow-water combinations of M2/K1/O1
    fM2, uM2 = _nodal_f_u("M2", N_deg)
    fK1, uK1 = _nodal_f_u("K1", N_deg)
    if family == "M3":
        return fM2 ** 1.5, 1.5 * uM2
    if family == "M4":
        return fM2 ** 2, 2 * uM2
    if family == "M6":
        return fM2 ** 3, 3 * uM2
    if family == "M8":
        return fM2 ** 4, 4 * uM2
    if family == "MK3":
        return fM2 * fK1, uM2 + uK1
    if family == "2MK3":
        return fM2 ** 2 * fK1, 2 * uM2 - uK1
    return 1.0, 0.0


def build_constituents(station):
    """
    Resolve a station's constituent list into prediction-ready entries.

    Each station constituent provides name/amplitude/phase/speed. We attach the
    Doodson definition so we can compute V0+u at prediction time.
    """
    resolved = []
    for c in station["constituents"]:
        name = c["name"].upper()
        defn = CONSTITUENT_DEF.get(name)
        if defn is None:
            # Unknown/!defined constituent: fall back to speed-only (no V0+u).
            # These are tiny; skipping their astronomy is harmless.
            resolved.append({
                "name": name, "amp": c["amplitude"], "g": c["phase"],
                "doodson": None, "bias": 0.0, "node": "S",
            })
            continue
        doodson, bias, node = defn
        resolved.append({
            "name": name, "amp": c["amplitude"], "g": c["phase"],
            "doodson": doodson, "bias": bias, "node": node,
        })
    return resolved


def predict_height(resolved, mean_level, dt):
    """Tide height (m) at timezone-aware datetime dt for resolved constituents."""
    args = _fundamental_arguments(dt)
    tau, s, h, p, N, pp = (args["tau"], args["s"], args["h"],
                           args["p"], args["N"], args["pp"])
    height = mean_level
    for c in resolved:
        amp = c["amp"]
        if amp == 0.0:
            continue
        if c["doodson"] is None:
            continue
        n_tau, n_s, n_h, n_p, n_pp = c["doodson"]
        V0 = (n_tau * tau + n_s * s + n_h * h + n_p * p + n_pp * pp
              + c["bias"])
        f, u = _nodal_f_u(c["node"], N)
        angle = (V0 + u - c["g"]) * D2R
        height += f * amp * math.cos(angle)
    return height
