import unittest
import numpy as np
import cv2

from gui.bot_manager import ConstructionBot


class TestConstructionBotMatching(unittest.TestCase):
    def test_match_score_prefers_correct_template(self):
        bot = ConstructionBot()

        frame = np.zeros((60, 60, 3), dtype=np.uint8)
        template_good = np.zeros((10, 10, 3), dtype=np.uint8)
        template_bad = np.zeros((10, 10, 3), dtype=np.uint8)

        cv2.rectangle(template_good, (2, 2), (7, 7), (255, 255, 255), thickness=-1)
        cv2.rectangle(template_bad, (0, 0), (3, 9), (255, 255, 255), thickness=-1)

        frame[25:35, 30:40] = template_good

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tpl_good_gray = cv2.cvtColor(template_good, cv2.COLOR_BGR2GRAY)
        tpl_bad_gray = cv2.cvtColor(template_bad, cv2.COLOR_BGR2GRAY)

        score_good = bot._match_score(frame, frame_gray, template_good, tpl_good_gray)
        score_bad = bot._match_score(frame, frame_gray, template_bad, tpl_bad_gray)

        self.assertGreater(score_good, score_bad)
        self.assertGreaterEqual(score_good, 0.9)


if __name__ == "__main__":
    unittest.main()

