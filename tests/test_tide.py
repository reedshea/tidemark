"""Tests for the tide series machinery: extrema finding, interpolation, scale."""

import datetime
import math
import os
import tempfile
import unittest
from zoneinfo import ZoneInfo

import _bootstrap  # noqa: F401
from data.stations import load_station
from data.tide import (TideSeries, _find_extrema, predict_series,
                       extreme_range)

TZ = ZoneInfo("America/New_York")


def _synthetic_cosine(n=241, period_steps=120):
    """A clean cosine so extrema have known locations."""
    base = datetime.datetime(2026, 1, 1, tzinfo=TZ)
    times, heights = [], []
    for i in range(n):
        times.append(base + datetime.timedelta(minutes=i))
        heights.append(math.cos(2 * math.pi * i / period_steps))
    return times, heights


class TestExtrema(unittest.TestCase):
    def test_finds_max_and_min(self):
        times, heights = _synthetic_cosine()
        ext = _find_extrema(times, heights)
        kinds = [e.kind for e in ext]
        self.assertIn("H", kinds)
        self.assertIn("L", kinds)

    def test_parabolic_refines_peak_height(self):
        """The interpolated peak should be very close to the true amplitude 1.0."""
        times, heights = _synthetic_cosine()
        ext = _find_extrema(times, heights)
        first_high = next(e for e in ext if e.kind == "H")
        self.assertAlmostEqual(first_high.height, 1.0, places=3)


class TestTideSeries(unittest.TestCase):
    def setUp(self):
        self.times, self.heights = _synthetic_cosine()
        self.series = TideSeries(self.times, self.heights,
                                 _find_extrema(self.times, self.heights),
                                 station={"name": "synthetic"})

    def test_height_at_endpoints(self):
        self.assertEqual(self.series.height_at(self.times[0]), self.heights[0])
        self.assertEqual(self.series.height_at(self.times[-1]), self.heights[-1])

    def test_height_at_interpolates(self):
        midpoint = self.times[0] + (self.times[1] - self.times[0]) / 2
        expected = (self.heights[0] + self.heights[1]) / 2
        self.assertAlmostEqual(self.series.height_at(midpoint), expected, places=6)

    def test_next_high_returns_future_high(self):
        nh = self.series.next_high(self.times[0])
        self.assertIsNotNone(nh)
        self.assertEqual(nh.kind, "H")
        self.assertGreaterEqual(nh.time, self.times[0])


class TestExtremeRange(unittest.TestCase):
    def test_range_and_cache(self):
        station = load_station("8447368")
        ref = datetime.datetime(2026, 5, 30, tzinfo=TZ)
        with tempfile.TemporaryDirectory() as d:
            lo, hi = extreme_range(station, ref, cache_dir=d, days=30)
            self.assertLess(lo, hi)
            # A cache file should now exist and a second call should reuse it.
            files = os.listdir(d)
            self.assertTrue(any(f.startswith("range_") for f in files))
            lo2, hi2 = extreme_range(station, ref, cache_dir=d, days=30)
            self.assertEqual((lo, hi), (lo2, hi2))


if __name__ == "__main__":
    unittest.main()
