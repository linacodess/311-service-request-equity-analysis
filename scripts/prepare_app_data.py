"""Prepare a current, queue-eligible CSV for the Streamlit dashboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from service_request_equity.data_loader import DataLoader
from service_request_equity.sorting import CaseSorter

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "app_queue_cases_110_days.csv"
DEFAULT_MAX_DAYS_OPEN = 110
OUTPUT_COLUMNS = [
    "CaseID",
    "Status",
    "Category",
    "Neighborhood",
    "Latitude",
    "Longitude",
    "OpenedDate",
    "ClosedDate",
    "days_open",
]


def prepare_app_data(
    input_path: str | Path,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    max_days_open: int = DEFAULT_MAX_DAYS_OPEN,
    today: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Prepare and save open cases used by the dashboard queue."""
    loader = DataLoader(input_path)
    loader.load()
    active = loader.get_active_cases(today=today, max_days_open=max_days_open)
    ranked = CaseSorter().filter_ranked_categories(active)

    for column in OUTPUT_COLUMNS:
        if column not in ranked.columns:
            ranked[column] = pd.NA

    prepared = ranked[OUTPUT_COLUMNS].copy().reset_index(drop=True)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_csv(destination, index=False)
    return prepared


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare current Boston 311 cases for the Streamlit dashboard."
    )
    parser.add_argument("input_path", help="Path to the downloaded Boston 311 CSV file.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Where to save the prepared dashboard CSV.",
    )
    parser.add_argument(
        "--max-days-open",
        type=int,
        default=DEFAULT_MAX_DAYS_OPEN,
        help="Oldest open case to keep. Defaults to 110 days.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prepared = prepare_app_data(
        input_path=args.input_path,
        output_path=args.output,
        max_days_open=args.max_days_open,
    )
    print(f"Saved {len(prepared):,} queue-eligible cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
