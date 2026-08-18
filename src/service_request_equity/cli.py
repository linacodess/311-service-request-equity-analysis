"""Command-line workflow for the 311 service request equity analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from service_request_equity.analysis import NeighborhoodAnalyzer
from service_request_equity.data_loader import DataLoader
from service_request_equity.sorting import CaseSorter
from service_request_equity.visualization import Visualizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze 311 service request equity patterns.")
    parser.add_argument(
        "--data-path",
        default="data/sample_311_cases.csv",
        help="Path to a 311 CSV file. Defaults to the included sample dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where summary JSON and plots will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit for faster local experiments with large CSV files.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of top neighborhoods/categories to include in outputs. Defaults to 25.",
    )
    return parser


def run_analysis(data_path: str | Path, output_dir: str | Path, limit: int | None = None, top_n: int = 25) -> dict[str, Any]:
    """Run the complete analysis workflow and return generated artifact paths."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    loader = DataLoader(data_path)
    df = loader.load(nrows=limit)

    sorter = CaseSorter()
    ranked_df = sorter.filter_ranked_categories(df)
    sorted_df = sorter.sort_by_urgency(ranked_df)

    analyzer = NeighborhoodAnalyzer(sorted_df)
    neighborhood_delay_summary = analyzer.neighborhood_delay_summary()
    category_summary = analyzer.category_duration_summary()
    snapshot = analyzer.equity_snapshot(top_n=top_n)

    summary_payload = {
        "dataset": loader.get_basic_stats(),
        "urgency_ranking": sorter.urgency_ranking,
        "snapshot": snapshot,
        "neighborhood_delay_summary": neighborhood_delay_summary.head(top_n).to_dict(orient="records"),
        "category_summary": category_summary.head(top_n).to_dict(orient="records"),
    }

    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    neighborhood_csv_path = output / "neighborhood_delay_summary.csv"
    category_csv_path = output / "category_summary.csv"
    neighborhood_delay_summary.to_csv(neighborhood_csv_path, index=False)
    category_summary.to_csv(category_csv_path, index=False)

    visualizer = Visualizer(sorted_df)
    map_path = visualizer.plot_case_map(output / "case_map.png")
    neighborhood_path = visualizer.plot_neighborhood_delays(
        neighborhood_delay_summary,
        output / "neighborhood_delays.png",
        top_n=top_n,
    )
    category_path = visualizer.plot_category_durations(
        category_summary,
        output / "category_durations.png",
        top_n=top_n,
    )

    return {
        "summary_path": str(summary_path),
        "map_path": str(map_path),
        "neighborhood_delays_path": str(neighborhood_path),
        "category_durations_path": str(category_path),
        "neighborhood_csv_path": str(neighborhood_csv_path),
        "category_csv_path": str(category_csv_path),
        "snapshot": snapshot,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    result = run_analysis(
        data_path=args.data_path,
        output_dir=args.output_dir,
        limit=args.limit,
        top_n=args.top_n,
    )

    snapshot = result["snapshot"]
    print("311 Service Request Equity Analysis")
    print(f"Analyzed {snapshot['total_cases_analyzed']} ranked cases")
    print(f"Average days open: {snapshot['avg_days_open']}")
    print(f"Summary: {result['summary_path']}")
    print(f"Map: {result['map_path']}")
    print(f"Neighborhood delay CSV: {result['neighborhood_csv_path']}")
    print(f"Neighborhood chart: {result['neighborhood_delays_path']}")
    print(f"Category chart: {result['category_durations_path']}")
    return 0
