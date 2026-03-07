import unittest
import numpy as np
import cv2

from gui.bot_manager import GymBot


class TestGymSpaceGreenCircle(unittest.TestCase):
    def test_detects_green_circle_within_radius_and_entry_area(self):
        bot = GymBot()
        bot.space_cfg = {
            "min_radius": 10,
            "max_radius": 50,
            "min_y_ratio": 0.4,
            "edge_margin": 2,
            "min_contrast": 0,
            "cooldown_s": 0.01,
            "hue_min": 35,
            "hue_max": 95,
            "sat_min": 50,
            "val_min": 50,
            "min_area": 50,
            "min_circularity": 0.3,
        }

        frame = np.zeros((200, 300, 3), dtype=np.uint8)
        center = (150, 160)
        radius = 28

        cv2.circle(frame, center, radius, (0, 255, 0), thickness=6)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        circles = bot._find_valid_circles(frame, gray)

        self.assertGreaterEqual(len(circles), 1)
        x, y, r = circles[0]
        self.assertTrue(abs(r - radius) <= 4)


if __name__ == "__main__":
    unittest.main()

