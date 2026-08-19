"""Tests for the command-line analysis workflow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from service_request_equity.cli import run_analysis

SAMPLE_PATH = Path("data/sample_311_cases.csv")


class TestCliWorkflow(unittest.TestCase):
    def test_run_analysis_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = run_analysis(SAMPLE_PATH, tmp_dir, top_n=3)
            output = Path(tmp_dir)

            expected_files = [
                output / "summary.json",
                output / "neighborhood_delay_summary.csv",
                output / "category_summary.csv",
                output / "case_map.png",
                output / "neighborhood_delays.png",
                output / "category_durations.png",
                output / "fair_queue_preview.html",
            ]

            for path in expected_files:
                self.assertTrue(path.exists(), f"Missing expected output: {path}")
                self.assertGreater(path.stat().st_size, 0)

            self.assertIn("neighborhood_csv_path", result)
            self.assertIn("fair_queue_preview_path", result)
            self.assertFalse((output / "equity_priority_scores.csv").exists())

            queue_html = (output / "fair_queue_preview.html").read_text(encoding="utf-8")
            self.assertIn('"Status": "Open"', queue_html)
            self.assertNotIn('"Status": "Closed"', queue_html)


if __name__ == "__main__":
    unittest.main()
