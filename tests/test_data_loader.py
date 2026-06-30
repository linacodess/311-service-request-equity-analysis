"""Tests for CSV loading and cleaning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from service_request_equity.data_loader import DataLoader

SAMPLE_PATH = Path("data/sample_311_cases.csv")


class TestDataLoader(unittest.TestCase):
    def test_load_sample_data(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        df = loader.load()

        self.assertEqual(len(df), 18)
        self.assertTrue(loader.is_processed)
        self.assertIn("days_open", df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["days_open"]))

    def test_basic_stats_after_loading(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        stats = loader.get_basic_stats()

        self.assertEqual(stats["total_cases"], 18)
        self.assertGreaterEqual(stats["unique_neighborhoods"], 5)
        self.assertEqual(stats["unique_categories"], 10)

    def test_filter_by_neighborhood_is_case_insensitive(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        filtered = loader.filter_by_neighborhood(["dorchester"])

        self.assertEqual(set(filtered["Neighborhood"]), {"Dorchester"})
        self.assertEqual(len(filtered), 5)

    def test_missing_file_raises(self) -> None:
        loader = DataLoader("data/not-here.csv")

        with self.assertRaises(FileNotFoundError):
            loader.load()

    def test_calculates_days_open_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "mini.csv"
            path.write_text(
                "\n".join(
                    [
                        "CaseID,OpenedDate,ClosedDate,Status,Category,Neighborhood,Latitude,Longitude",
                        "1,2024-01-01,2024-01-04,Closed,Graffiti Removal,Dorchester,42.3,-71.0",
                    ]
                ),
                encoding="utf-8",
            )

            df = DataLoader(path).load()

        self.assertEqual(df.loc[0, "days_open"], 3)


if __name__ == "__main__":
    unittest.main()
