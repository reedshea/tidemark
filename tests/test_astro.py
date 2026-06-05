"""Tests for the offline sun and moon astronomy."""

import datetime
import unittest
from zoneinfo import ZoneInfo

import _bootstrap  # noqa: F401
from data import moon, sun

UTC = ZoneInfo("UTC")
TZ = ZoneInfo("America/New_York")
# Great Hill, for a concrete location.
LAT, LON = 41.7138, -70.7506


class TestMoon(unittest.TestCase):
    def test_full_moon_illuminated(self):
        frac, illum = moon.phase(datetime.datetime(2026, 5, 31, 12, tzinfo=UTC))
        self.assertGreater(illum, 0.98)
        self.assertEqual(moon.phase_name(frac), "Full Moon")

    def test_new_moon_dark(self):
        frac, illum = moon.phase(datetime.datetime(2026, 6, 15, 12, tzinfo=UTC))
        self.assertLess(illum, 0.05)
        self.assertEqual(moon.phase_name(frac), "New Moon")

    def test_rise_set_and_track(self):
        start = datetime.datetime(2026, 5, 30, tzinfo=TZ)
        end = start + datetime.timedelta(days=2)
        events = moon.rise_set(start, end, LAT, LON, TZ)
        self.assertTrue(events)
        kinds = {k for k, _ in events}
        self.assertTrue(kinds <= {"moonrise", "moonset"})
        track = moon.altitude_track(start, end, LAT, LON, step_minutes=30)
        self.assertGreater(len(track), 1)


class TestSun(unittest.TestCase):
    def test_solstice_day_length(self):
        ev = sun.sun_events(datetime.date(2026, 6, 21), LAT, LON, TZ)
        day_h = (ev["sunset"] - ev["sunrise"]).total_seconds() / 3600
        self.assertAlmostEqual(day_h, 15.2, delta=0.4)

    def test_summer_longer_than_winter(self):
        s = sun.sun_events(datetime.date(2026, 6, 21), LAT, LON, TZ)
        w = sun.sun_events(datetime.date(2026, 12, 21), LAT, LON, TZ)
        summer = (s["sunset"] - s["sunrise"]).total_seconds()
        winter = (w["sunset"] - w["sunrise"]).total_seconds()
        self.assertGreater(summer, winter + 3 * 3600)

    def test_daylight_intervals_cover_window(self):
        start = datetime.datetime(2026, 5, 30, tzinfo=TZ)
        end = start + datetime.timedelta(hours=36)
        intervals = sun.daylight_intervals(start, end, LAT, LON, TZ)
        self.assertTrue(intervals)
        for rise, set_ in intervals:
            self.assertLess(rise, set_)


if __name__ == "__main__":
    unittest.main()
