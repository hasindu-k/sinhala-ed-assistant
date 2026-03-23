
import unittest
from decimal import Decimal
from unittest.mock import MagicMock
from app.services.evaluation.grading_service import GradingService

class TestMCQGrading(unittest.TestCase):
    def setUp(self):
        # Mock DB session
        self.db = MagicMock()
        self.service = GradingService(self.db)

    def test_exact_match_boost_numeric(self):
        """Verify that exact numeric matches (ignoring dots/spaces) get 1.0 similarity."""
        # 2 marks = short answer
        score = self.service._calculate_system_score(
            student_text="3",
            reference_text="3",
            weights={"semantic": 0.8, "relevance": 0.2},
            max_marks=2
        )
        self.assertEqual(score, 1.0)

        score_with_dot = self.service._calculate_system_score(
            student_text="3.",
            reference_text="3",
            weights={"semantic": 0.8, "relevance": 0.2},
            max_marks=2
        )
        self.assertEqual(score_with_dot, 1.0)

    def test_exact_match_boost_sinhala(self):
        """Verify that exact Sinhala word matches get 1.0 similarity."""
        score = self.service._calculate_system_score(
            student_text="වැව",
            reference_text="වැව",
            weights={"semantic": 0.8, "relevance": 0.2},
            max_marks=2
        )
        self.assertEqual(score, 1.0)

    def test_sigmoid_threshold_lenience(self):
        """Verify that low similarity (due to OCR noise) is treated more leniently now."""
        # Previous threshold for 0.5 marks was 0.22. Now it's 0.18.
        # Let's test 0.20 similarity.
        
        # We need to mock _semantic_similarity to return exactly 0.20
        self.service._semantic_similarity = MagicMock(return_value=0.20)
        self.service._calculate_relevance_score = MagicMock(return_value=0.20)
        
        score = self.service._calculate_system_score(
            student_text="noisy text",
            reference_text="reference",
            weights={"semantic": 1.0, "relevance": 0.0},
            max_marks=2
        )
        
        # sim 0.20 is between 0.18 and 0.30.
        # Should be > 0.50.
        self.assertGreater(score, 0.50)
        self.assertLess(score, 1.0)

if __name__ == "__main__":
    unittest.main()
