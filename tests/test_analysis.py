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

    def test_category_duration_summary_orders_shortest_average_duration_first(self) -> None:
        summary = self.analyzer.category_duration_summary()

        self.assertEqual(summary.iloc[0]["Category"], "Needle Pickup")
        self.assertEqual(summary.iloc[0]["avg_days_open"], 1.0)

    def test_equity_snapshot_is_json_ready(self) -> None:
        snapshot = self.analyzer.equity_snapshot(top_n=3)

        self.assertEqual(snapshot["total_cases_analyzed"], 18)
        self.assertEqual(len(snapshot["categories_by_avg_days_open"]), 3)
        self.assertEqual(len(snapshot["neighborhoods_with_highest_avg_delay"]), 3)
        self.assertIsInstance(snapshot["avg_days_open"], float)

    def test_neighborhood_delay_summary_orders_longest_average_delay_first(self) -> None:
        summary = self.analyzer.neighborhood_delay_summary()

        self.assertEqual(summary.iloc[0]["Neighborhood"], "Roxbury")
        self.assertEqual(summary.iloc[0]["avg_days_open"], 13.0)
        self.assertEqual(summary.iloc[0]["citywide_avg_days_open"], 6.78)
        self.assertEqual(summary.iloc[0]["neighborhood_delay_boost"], 6.22)


if __name__ == "__main__":
    unittest.main()
