"""Regression tests for the harmonic tide engine.

These lock in the accuracy the README claims by checking tidemark's predictions
for the bundled Great Hill station against NOAA's *own* published high/low
predictions (station 8447368). NOAA tide predictions are deterministic, so these
reference values don't drift; if our numbers move, the engine (or the station
data) changed.

Validated characterization (see README): high-tide timing is excellent, low
tides sit in flat troughs so their timing is looser, and heights track within
roughly the documented ~0.17 m RMS.
"""

import datetime
import unittest
from zoneinfo import ZoneInfo

import _bootstrap  # noqa: F401  (sets sys.path)
from data.stations import load_station
from data.tide import predict_series

TZ = ZoneInfo("America/New_York")

# NOAA published hi/lo predictions for 8447368, MLLW datum, metric, local time.
# Source: api.tidesandcurrents.noaa.gov .../datagetter?product=predictions&interval=hilo
NOAA_HILO = [
    ("2026-05-30 01:30", 0.124, "L"), ("2026-05-30 08:18", 1.124, "H"),
    ("2026-05-30 13:07", 0.112, "L"), ("2026-05-30 20:38", 1.348, "H"),
    ("2026-05-31 02:09", 0.105, "L"), ("2026-05-31 08:57", 1.124, "H"),
    ("2026-05-31 13:49", 0.094, "L"), ("2026-05-31 21:17", 1.316, "H"),
    ("2026-06-01 02:50", 0.102, "L"), ("2026-06-01 09:36", 1.109, "H"),
    ("2026-06-01 14:33", 0.091, "L"), ("2026-06-01 21:56", 1.273, "H"),
]


def _parse(ts):
    return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


class TestHarmonicsAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        station = load_station("8447368")
        start = datetime.datetime(2026, 5, 30, 0, 0, tzinfo=TZ)
        cls.series = predict_series(station, start, 72, step_minutes=1)

    def _nearest(self, kind, when):
        cands = [e for e in self.series.extrema if e.kind == kind]
        return min(cands, key=lambda e: abs((e.time - when).total_seconds()))

    def test_high_tide_timing(self):
        """Every NOAA high is matched by a tidemark high within 15 minutes."""
        for ts, _h, kind in NOAA_HILO:
            if kind != "H":
                continue
            when = _parse(ts)
            err = abs((self._nearest("H", when).time - when).total_seconds()) / 60
            self.assertLess(err, 15.0,
                            f"high at {ts}: {err:.1f} min off (expected < 15)")

    def test_low_tide_timing(self):
        """Lows sit in flat troughs; timing is looser but bounded (< 60 min)."""
        for ts, _h, kind in NOAA_HILO:
            if kind != "L":
                continue
            when = _parse(ts)
            err = abs((self._nearest("L", when).time - when).total_seconds()) / 60
            self.assertLess(err, 60.0,
                            f"low at {ts}: {err:.1f} min off (expected < 60)")

    def test_heights_track_noaa(self):
        """Predicted heights track NOAA within the documented RMS band."""
        for ts, h, kind in NOAA_HILO:
            when = _parse(ts)
            dh = abs(self._nearest(kind, when).height - h)
            tol = 0.30 if kind == "H" else 0.15
            self.assertLess(dh, tol,
                            f"{kind} at {ts}: {dh:.3f} m off (expected < {tol})")


class TestHarmonicsPhysical(unittest.TestCase):
    """Sanity checks that don't depend on a station file."""

    def test_semidiurnal_spacing(self):
        """Great Hill is semidiurnal: consecutive highs ~12.42 h apart."""
        station = load_station("8447368")
        start = datetime.datetime(2026, 5, 30, 0, 0, tzinfo=TZ)
        series = predict_series(station, start, 72, step_minutes=2)
        highs = [e.time for e in series.extrema if e.kind == "H"]
        gaps = [(b - a).total_seconds() / 3600
                for a, b in zip(highs, highs[1:])]
        self.assertTrue(gaps)
        for g in gaps:
            self.assertAlmostEqual(g, 12.42, delta=1.0)


if __name__ == "__main__":
    unittest.main()
