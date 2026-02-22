import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from utils.knowledge.gardener import KnowledgeGardeningService


class TestKnowledgeGardeningService(unittest.TestCase):
    def setUp(self):
        self.service = KnowledgeGardeningService()
        # Mock settings for predictable testing
        self.service.settings.kg_importance_weight_recency = 0.3
        self.service.settings.kg_importance_weight_impact = 0.5
        self.service.settings.kg_importance_weight_pattern = 0.2
        self.service.settings.kg_retention_days = 100

    def test_calculate_importance_score_fresh_critical(self):
        """Test scoring for a fresh, critical item."""
        item = {
            "created_at": datetime.now().isoformat(),
            "category": "security",
            "codified_improvements": [{"type": "fix"}],
            "description": "Critical security vulnerability fixed",
        }
        score = self.service._calculate_importance_score(item)
        # Recency (1.0 * 0.3) + Impact (0.9 * 0.5) + Pattern (0.5 * 0.2)
        # 0.3 + 0.5 + 0.1 = 0.9
        # Impact breakdown: 0.5 base + 0.2 (improvements) + 0.2 (security) + 0.1 (critical) = 1.0
        self.assertAlmostEqual(score, 0.90, places=2)
        self.assertEqual(self.service._determine_tier(score), "detailed")

    def test_calculate_importance_score_old_trivial(self):
        """Test scoring for an old, trivial item."""
        old_date = (datetime.now() - timedelta(days=50)).isoformat()
        item = {
            "created_at": old_date,
            "category": "chore",
            "description": "Fixed a typo",
        }
        score = self.service._calculate_importance_score(item)
        # Recency (0.5 * 0.3) + Impact (0.5 * 0.5) + Pattern (0.5 * 0.2)
        # 0.15 + 0.25 + 0.1 = 0.5
        self.assertAlmostEqual(score, 0.50, places=2)
        self.assertEqual(self.service._determine_tier(score), "compressed")

    def test_determine_tier(self):
        self.assertEqual(self.service._determine_tier(0.9), "detailed")
        self.assertEqual(self.service._determine_tier(0.6), "compressed")
        self.assertEqual(self.service._determine_tier(0.2), "principle")

    @patch("utils.knowledge.gardener.KnowledgeBase")
    def test_garden_flow_enrichment(self, MockKB):
        """Test that garden flow calculates scores for items without them."""
        mock_kb_instance = MockKB.return_value

        # Setup mock items
        item1 = {"id": "1", "description": "Test item 1", "created_at": datetime.now().isoformat()}
        mock_kb_instance.get_all_learnings.return_value = [item1]
        mock_kb_instance.search_similar_patterns.return_value = []

        # Inject mock KB into service
        self.service.kb = mock_kb_instance

        # Run garden
        self.service.garden(dry_run=True)

        # Verify item was modified with new fields
        self.assertIn("importance_score", item1)
        self.assertIn("compression_tier", item1)
        self.assertIn("fact_statement", item1)

