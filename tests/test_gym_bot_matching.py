import unittest
import numpy as np
import cv2

from gui.bot_manager import GymBot


class TestGymBotMatching(unittest.TestCase):
    def test_match_score_detects_template(self):
        bot = GymBot()

        frame = np.zeros((80, 120, 3), dtype=np.uint8)
        template = np.zeros((12, 18, 3), dtype=np.uint8)

        cv2.circle(template, (9, 6), 5, (255, 255, 255), thickness=-1)
        frame[30:42, 50:68] = template

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        score = bot._match_score(frame, frame_gray, template, tpl_gray)
        self.assertGreaterEqual(score, 0.9)


if __name__ == "__main__":
    unittest.main()

