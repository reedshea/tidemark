"""Smoke test for the ribbon renderer.

Doesn't assert pixels (that's brittle); it confirms the full pipeline runs and
produces a panel-sized image plus a sane now-marker rectangle for the C host's
partial-refresh logic.
"""

import datetime
import random
import unittest
from zoneinfo import ZoneInfo

import _bootstrap  # noqa: F401
import main
from render import theme as T
from render import ribbon


class TestRender(unittest.TestCase):
    def test_render_produces_panel_image_and_rect(self):
        random.seed(0)  # ribbon uses random for sea swell / moon stipple
        now = datetime.datetime(2026, 5, 30, 14, 23,
                                tzinfo=ZoneInfo("America/New_York"))
        ctx = main.build_context(now)
        img, rect = ribbon.render(ctx)

        self.assertEqual(img.size, (T.WIDTH, T.HEIGHT))
        self.assertEqual(img.mode, "L")

        x, y, w, h = rect
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        # The marker strip must fall inside the panel.
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(x + w, T.WIDTH)
        self.assertLessEqual(y + h, T.HEIGHT)


if __name__ == "__main__":
    unittest.main()
