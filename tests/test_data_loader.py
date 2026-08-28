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

        self.assertEqual(len(df), 60)
        self.assertTrue(loader.is_processed)
        self.assertIn("days_open", df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["days_open"]))
        self.assertEqual(set(df["Status"]), {"Open", "Closed"})

    def test_basic_stats_after_loading(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        stats = loader.get_basic_stats()

        self.assertEqual(stats["total_cases"], 60)
        self.assertGreaterEqual(stats["unique_neighborhoods"], 6)
        self.assertGreater(stats["unique_categories"], 10)

    def test_filter_by_neighborhood_is_case_insensitive(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        filtered = loader.filter_by_neighborhood(["dorchester"])

        self.assertEqual(set(filtered["Neighborhood"]), {"Dorchester"})
        self.assertGreater(len(filtered), 5)

    def test_prepares_initial_historical_and_active_cases(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        historical = loader.get_historical_cases()
        active = loader.get_active_cases()

        self.assertEqual(len(historical), 42)
        self.assertEqual(len(active), 18)
        self.assertEqual(set(historical["Status"]), {"Closed"})
        self.assertEqual(set(active["Status"]), {"Open"})
        self.assertTrue(pd.api.types.is_numeric_dtype(active["days_open"]))

    def test_active_cases_fill_missing_days_open_from_opened_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "active.csv"
            path.write_text(
                "\n".join(
                    [
                        "CaseID,OpenedDate,ClosedDate,Status,Category,Neighborhood,Latitude,Longitude",
                        "1,2026-01-01,,Open,Needle Pickup,Dorchester,42.3,-71.0",
                    ]
                ),
                encoding="utf-8",
            )

            loader = DataLoader(path)
            loader.load()
            active = loader.get_active_cases(today=pd.Timestamp("2026-01-05"))

        self.assertEqual(active.loc[0, "days_open"], 4)

    def test_active_cases_can_exclude_stale_records(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        active = loader.get_active_cases(max_days_open=5)

        self.assertLess(len(active), 18)
        self.assertTrue((active["days_open"] <= 5).all())

    def test_active_cases_requires_positive_stale_record_limit(self) -> None:
        loader = DataLoader(SAMPLE_PATH)
        loader.load()

        with self.assertRaises(ValueError):
            loader.get_active_cases(max_days_open=0)

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

    def test_loads_new_boston_export_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "new_boston.csv"
            path.write_text(
                "\n".join(
                    [
                        "case_enquiry_id,open_dt,closed_dt,case_status,type,neighborhood,latitude,longitude",
                        "101,2026-01-01,2026-01-04,Closed,Parking Enforcement,Dorchester,42.3,-71.0",
                    ]
                ),
                encoding="utf-8",
            )

            df = DataLoader(path).load()

        self.assertEqual(df.loc[0, "CaseID"], 101)
        self.assertEqual(df.loc[0, "Status"], "Closed")
        self.assertEqual(df.loc[0, "Category"], "Parking Enforcement")
        self.assertEqual(df.loc[0, "Neighborhood"], "Dorchester")
        self.assertEqual(df.loc[0, "days_open"], 3)


if __name__ == "__main__":
    unittest.main()
