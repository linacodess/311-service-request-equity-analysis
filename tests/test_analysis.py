"""Tests for equity analysis summaries."""

from __future__ import annotations

import unittest
from pathlib import Path

from service_request_equity.analysis import NeighborhoodAnalyzer
from service_request_equity.data_loader import DataLoader
from service_request_equity.sorting import CaseSorter

SAMPLE_PATH = Path("data/sample_311_cases.csv")


class TestNeighborhoodAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        df = DataLoader(SAMPLE_PATH).load()
        ranked = CaseSorter().sort_by_urgency(df)
        self.analyzer = NeighborhoodAnalyzer(ranked)

    def test_average_days_open(self) -> None:
        self.assertAlmostEqual(self.analyzer.average_days_open(), 6.78, places=2)

    def test_above_average_counts(self) -> None:
        counts = self.analyzer.above_average_neighborhood_counts()

        self.assertEqual(counts.loc["Dorchester"], 4)
        self.assertEqual(counts.loc["Roxbury"], 3)

    def test_category_duration_summary_orders_slowest_first(self) -> None:
        summary = self.analyzer.category_duration_summary()

        self.assertEqual(summary.iloc[0]["Category"], "Poor Conditions of Property")
        self.assertEqual(summary.iloc[0]["avg_days_open"], 15.5)

    def test_equity_snapshot_is_json_ready(self) -> None:
        snapshot = self.analyzer.equity_snapshot(top_n=3)

        self.assertEqual(snapshot["total_cases_analyzed"], 18)
        self.assertEqual(len(snapshot["slowest_categories_by_avg_days_open"]), 3)
        self.assertEqual(len(snapshot["top_equity_priority_neighborhoods"]), 3)
        self.assertIsInstance(snapshot["avg_days_open"], float)

    def test_equity_priority_scores_rank_neighborhoods(self) -> None:
        scores = self.analyzer.equity_priority_scores()

        self.assertIn("equity_priority_score", scores.columns)
        self.assertGreaterEqual(scores["equity_priority_score"].iloc[0], scores["equity_priority_score"].iloc[-1])
        self.assertTrue(scores["equity_priority_score"].between(0, 100).all())


if __name__ == "__main__":
    unittest.main()
