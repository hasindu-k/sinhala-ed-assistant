#app/services/evaluation/grading_service.py

import unittest
from decimal import Decimal
import sys
import os

# Mocking parts of the system to test the scoring logic in isolation
# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockGradingService:
    def _apply_discrete_bands(self, ratio: float, max_marks: int) -> float:
        """Convert a continuous similarity ratio into discrete marking bands."""
        # This should match the logic in grading_service._apply_discrete_bands
        full_marks_threshold = 0.40 if max_marks <= 2 else 0.52
        scale_range = full_marks_threshold - 0.05

        if ratio >= full_marks_threshold: return 1.0
        if ratio < 0.05: return 0.0

        scaled_ratio = (ratio - 0.05) / scale_range
        actual_marks = scaled_ratio * max_marks
        
        from decimal import Decimal, ROUND_HALF_UP
        step = Decimal("1.0") if max_marks <= 2 else Decimal("0.5")
        snapped_marks = (Decimal(str(actual_marks)) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step
        
        final_ratio = float(snapped_marks / Decimal(str(max_marks)))
        return min(1.0, final_ratio)

class TestScoringBands(unittest.TestCase):
    def setUp(self):
        self.service = MockGradingService()

    def test_short_answer_bands(self):
        # max_marks = 2, threshold = 0.40, range = 0.35
        self.assertEqual(self.service._apply_discrete_bands(0.45, 2), 1.0)  # 2.0 marks
        self.assertEqual(self.service._apply_discrete_bands(0.40, 2), 1.0) # 2.0 marks
        # (0.25-0.05)/0.35 = 0.57. 0.57*2 = 1.14 -> 1.0 marks
        self.assertEqual(self.service._apply_discrete_bands(0.25, 2), 0.5)  # 1.0 marks
        # (0.15-0.05)/0.35 = 0.28. 0.28*2 = 0.56 -> 1.0 marks
        self.assertEqual(self.service._apply_discrete_bands(0.15, 2), 0.5) # 1.0 marks
        self.assertEqual(self.service._apply_discrete_bands(0.04, 2), 0.0)  # 0.0 marks
        
    def test_essay_bands(self):
        # max_marks = 4, threshold = 0.52, range = 0.47
        self.assertEqual(self.service._apply_discrete_bands(0.55, 4), 1.0)  # 4 marks
        self.assertEqual(self.service._apply_discrete_bands(0.52, 4), 1.0)  # 4 marks
        # (0.40-0.05)/0.47 = 0.74. 0.74*4 = 2.96 -> 3.0 marks
        self.assertEqual(self.service._apply_discrete_bands(0.40, 4), 0.75) # 3 marks
        # (0.30-0.05)/0.47 = 0.53. 0.53*4 = 2.12 -> 2.0 marks
        self.assertEqual(self.service._apply_discrete_bands(0.30, 4), 0.5)  # 2 marks
        # (0.20-0.05)/0.47 = 0.31. 0.31*4 = 1.24 -> 1.0 mark
        self.assertEqual(self.service._apply_discrete_bands(0.20, 4), 0.25) # 1 mark
        self.assertEqual(self.service._apply_discrete_bands(0.04, 4), 0.0)  # 0 marks

if __name__ == '__main__':
    unittest.main()
