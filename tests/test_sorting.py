"""Tests for urgency ranking and sorting."""

from __future__ import annotations

import unittest

import pandas as pd

from service_request_equity.sorting import CaseSorter, DEFAULT_URGENCY_RANKING


class TestCaseSorter(unittest.TestCase):
    def test_filter_ranked_categories_removes_unranked_rows(self) -> None:
        df = pd.DataFrame(
            {
                "Category": ["Needle Pickup", "Noise Complaint"],
                "days_open": [1, 4],
            }
        )
        sorter = CaseSorter()

        result = sorter.filter_ranked_categories(df)

        self.assertEqual(result["Category"].tolist(), ["Needle Pickup"])

    def test_sort_by_urgency_uses_rank_then_days_open(self) -> None:
        df = pd.DataFrame(
            {
                "Category": ["Parking Enforcement", "Needle Pickup", "Parking Enforcement"],
                "days_open": [2, 1, 8],
            }
        )
        sorter = CaseSorter()

        result = sorter.sort_by_urgency(df)

        self.assertEqual(result["Category"].tolist(), ["Needle Pickup", "Parking Enforcement", "Parking Enforcement"])
        self.assertEqual(result["days_open"].tolist(), [1, 8, 2])
        self.assertEqual(result["urgency_score"].tolist(), [1, 3, 3])

    def test_add_urgency_scores_does_not_mutate_input(self) -> None:
        df = pd.DataFrame({"Category": ["Needle Pickup"], "days_open": [1]})
        sorter = CaseSorter()

        result = sorter.add_urgency_scores(df)

        self.assertIn("urgency_score", result.columns)
        self.assertNotIn("urgency_score", df.columns)

    def test_missing_rank_raises(self) -> None:
        df = pd.DataFrame({"Category": ["Noise Complaint"], "days_open": [5]})
        sorter = CaseSorter(DEFAULT_URGENCY_RANKING)

        with self.assertRaises(ValueError):
            sorter.add_urgency_scores(df)

    def test_non_numeric_days_open_raises(self) -> None:
        df = pd.DataFrame({"Category": ["Needle Pickup"], "days_open": ["slow"]})

        with self.assertRaises(ValueError):
            CaseSorter().sort_by_urgency(df)

    def test_fair_service_queue_uses_provided_delay_boost(self) -> None:
        df = pd.DataFrame(
            {
                "Category": ["Needle Pickup", "Needle Pickup"],
                "Neighborhood": ["Roxbury", "Dorchester"],
                "days_open": [1, 10],
                "neighborhood_delay_boost": [5, 0],
            }
        )

        result = CaseSorter().sort_by_fair_service_queue(df)

        self.assertEqual(result["Neighborhood"].tolist(), ["Roxbury", "Dorchester"])
        self.assertEqual(result["neighborhood_delay_boost"].tolist(), [5, 0])

    def test_fair_service_queue_requires_delay_boost(self) -> None:
        df = pd.DataFrame(
            {
                "Category": ["Needle Pickup"],
                "Neighborhood": ["Dorchester"],
                "days_open": [1],
            }
        )

        with self.assertRaises(KeyError):
            CaseSorter().sort_by_fair_service_queue(df)


if __name__ == "__main__":
    unittest.main()
