"""Tests for the dashboard data preparation script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.prepare_app_data import OUTPUT_COLUMNS, prepare_app_data


class TestPrepareAppData(unittest.TestCase):
    def test_prepares_current_ranked_open_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "raw.csv"
            output_path = root / "prepared.csv"
            pd.DataFrame(
                {
                    "CaseID": [1, 2, 3, 4],
                    "Status": ["Open", "Open", "Closed", "Open"],
                    "Category": [
                        "Needle Pickup",
                        "Street Light Outages",
                        "Needle Pickup",
                        "Noise Complaint",
                    ],
                    "Neighborhood": ["Roxbury"] * 4,
                    "Latitude": [42.3] * 4,
                    "Longitude": [-71.1] * 4,
                    "OpenedDate": ["2026-08-21", "2026-04-01", "2026-08-01", "2026-08-26"],
                    "ClosedDate": [None, None, "2026-08-05", None],
                }
            ).to_csv(input_path, index=False)

            prepared = prepare_app_data(
                input_path,
                output_path,
                max_days_open=110,
                today=pd.Timestamp("2026-08-31"),
            )

            self.assertEqual(prepared["CaseID"].tolist(), [1])
            self.assertEqual(prepared["days_open"].tolist(), [10.0])
            self.assertEqual(prepared.columns.tolist(), OUTPUT_COLUMNS)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
