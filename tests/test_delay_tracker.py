"""Tests for neighborhood delay boost tracking."""

from __future__ import annotations

import unittest

import pandas as pd

from service_request_equity.delay_tracker import DelayTracker


class TestDelayTracker(unittest.TestCase):
    def test_refresh_calculates_delay_boosts(self) -> None:
        tracker = DelayTracker()
        df = pd.DataFrame(
            {
                "Neighborhood": ["Dorchester", "Dorchester", "Roxbury", "Hyde Park"],
                "days_open": [10, 14, 4, 8],
            }
        )

        tracker.refresh(df)
        summary = tracker.boost_summary()

        self.assertAlmostEqual(tracker.citywide_avg_days_open, 9.0)
        self.assertEqual(summary.iloc[0]["Neighborhood"], "Dorchester")
        self.assertEqual(summary.iloc[0]["avg_days_open"], 12.0)
        self.assertEqual(summary.iloc[0]["neighborhood_delay_boost"], 3.0)
        self.assertEqual(tracker.get_neighborhood_boost("Roxbury"), 0.0)

    def test_get_unknown_neighborhood_boost_returns_zero(self) -> None:
        tracker = DelayTracker()

        self.assertEqual(tracker.get_neighborhood_boost("Unknown"), 0.0)

    def test_refresh_requires_columns(self) -> None:
        tracker = DelayTracker()
        df = pd.DataFrame({"Neighborhood": ["Dorchester"]})

        with self.assertRaises(KeyError):
            tracker.refresh(df)

    def test_refresh_requires_valid_rows(self) -> None:
        tracker = DelayTracker()
        df = pd.DataFrame({"Neighborhood": [None], "days_open": [None]})

        with self.assertRaises(ValueError):
            tracker.refresh(df)


if __name__ == "__main__":
    unittest.main()
