"""Tests for generated visual artifacts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from service_request_equity.analysis import NeighborhoodAnalyzer
from service_request_equity.data_loader import DataLoader
from service_request_equity.sorting import CaseSorter
from service_request_equity.visualization import Visualizer

SAMPLE_PATH = Path("data/sample_311_cases.csv")


class TestVisualizer(unittest.TestCase):
    def test_visualizations_are_written(self) -> None:
        df = DataLoader(SAMPLE_PATH).load()
        sorted_df = CaseSorter().sort_by_urgency(df)
        analyzer = NeighborhoodAnalyzer(sorted_df)
        visualizer = Visualizer(sorted_df)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir)
            map_path = visualizer.plot_case_map(output / "map.png")
            delay_path = visualizer.plot_neighborhood_delays(
                analyzer.neighborhood_delay_summary(),
                output / "delays.png",
            )
            category_path = visualizer.plot_category_durations(
                analyzer.category_duration_summary(),
                output / "categories.png",
            )

            self.assertGreater(map_path.stat().st_size, 0)
            self.assertGreater(delay_path.stat().st_size, 0)
            self.assertGreater(category_path.stat().st_size, 0)

    def test_percentile_cap_uses_high_but_not_max_value(self) -> None:
        cap = Visualizer._percentile_cap(pd.Series([0, 1, 2, 3, 100]), percentile=0.8)

        self.assertGreater(cap, 3.0)
        self.assertLess(cap, 100.0)


if __name__ == "__main__":
    unittest.main()
