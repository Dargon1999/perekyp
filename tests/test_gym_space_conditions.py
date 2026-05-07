import unittest
import numpy as np
import cv2

from gui.bot_manager import GymBot


class TestGymSpaceConditions(unittest.TestCase):
    def test_space_triggers_only_with_valid_circle_in_entry_area(self):
        bot = GymBot()
        bot.space_cfg = {
            "min_radius": 10,
            "max_radius": 40,
            "min_y_ratio": 0.5,
            "edge_margin": 6,
            "min_contrast": 5,
            "cooldown_s": 0.06,
        }

        frame = np.zeros((200, 200), dtype=np.uint8)

        cv2.circle(frame, (100, 40), 20, 255, thickness=-1)
        cv2.circle(frame, (100, 40), 14, 0, thickness=-1)
        circles = bot._filter_circles(frame, [(100, 40, 20)], min_y=100, edge_margin=6, min_contrast=5)
        self.assertEqual(len(circles), 0)

        frame2 = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(frame2, (100, 140), 20, 255, thickness=-1)
        cv2.circle(frame2, (100, 140), 14, 0, thickness=-1)
        circles2 = bot._filter_circles(frame2, [(100, 140, 20)], min_y=100, edge_margin=6, min_contrast=5)
        self.assertGreaterEqual(len(circles2), 1)


if __name__ == "__main__":
    unittest.main()
