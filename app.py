"""Streamlit dashboard for simulating the fair service queue."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from service_request_equity.data_loader import DataLoader
from service_request_equity.simulation import FairQueueSimulation

DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "311_service_requests_2026.csv"
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_311_cases.csv"
COMPLETION_COUNT = 10000
DEFAULT_ACTIVE_CASE_MAX_DAYS_OPEN = 90


def main() -> None:
    st.set_page_config(page_title="Fair Service Queue Simulation", layout="wide")
    st.title("Fair Service Queue Simulation")
    st.caption(
        "Simulate how completing cases from the fair queue can change neighborhood delay boosts over time."
    )

    data_path = _data_path_input()
    max_days_open = _active_case_limit_input()
    active_df, total_open_cases = _load_initial_cases(data_path, max_days_open)
    simulation = _get_simulation(data_path, max_days_open, active_df)

    excluded_count = total_open_cases - len(active_df)
    st.caption(
        f"Open cases beyond {max_days_open} days are treated as stale and excluded from the queue "
        f"because long-open 311 records are often resolved-but-unmarked, especially Parking Enforcement. "
        f"{excluded_count:,} of {total_open_cases:,} open cases excluded."
    )
    _render_controls(simulation)
    _render_summary(simulation)
    _render_delay_dashboard(simulation)
    _render_queue(simulation)


def _data_path_input() -> Path:
    default_path = DEFAULT_DATA_PATH if DEFAULT_DATA_PATH.exists() else SAMPLE_DATA_PATH
    path_text = st.sidebar.text_input("CSV path", value=str(default_path))
    return Path(path_text).expanduser()


def _active_case_limit_input() -> int:
    return st.sidebar.slider(
        "Open case day limit",
        min_value=30,
        max_value=365,
        value=DEFAULT_ACTIVE_CASE_MAX_DAYS_OPEN,
        step=5,
        help="Open records beyond this many days are treated as stale so they do not dominate the queue.",
    )


@st.cache_data(show_spinner="Loading 311 data...")
def _load_initial_cases(data_path: Path, max_days_open: int) -> tuple[pd.DataFrame, int]:
    loader = DataLoader(data_path)
    df = loader.load()
    total_open_cases = len(loader.cases_with_status(df, "Open"))
    return (
        loader.get_active_cases(max_days_open=max_days_open),
        total_open_cases,
    )


def _get_simulation(
    data_path: Path,
    max_days_open: int,
    active_df: pd.DataFrame,
) -> FairQueueSimulation:
    state_key = f"{data_path}:{max_days_open}"
    if st.session_state.get("simulation_data_path") != state_key:
        st.session_state.simulation_data_path = state_key
        st.session_state.simulation = FairQueueSimulation(active_df)
        st.session_state.last_completed = pd.DataFrame()

    return st.session_state.simulation


def _render_controls(simulation: FairQueueSimulation) -> None:
    left, right = st.columns([1, 1])

    with left:
        if st.button(f"Complete next {COMPLETION_COUNT} cases", type="primary"):
            st.session_state.last_completed = simulation.complete_next_cases(COMPLETION_COUNT)

    with right:
        if st.button("Reset simulation"):
            simulation.reset()
            st.session_state.last_completed = pd.DataFrame()


def _render_summary(simulation: FairQueueSimulation) -> None:
    summary = simulation.summary()
    current_tracker = simulation.delay_tracker()
    queue_df = simulation.queue_dataframe()

    active_col, completed_col, citywide_col = st.columns(3)
    active_col.metric("Active queue cases", f"{len(queue_df):,}")
    completed_col.metric("Completed in simulation", f"{summary['completed_cases']:,}")
    citywide_col.metric(
        "Active avg days open",
        _format_metric(current_tracker.citywide_avg_days_open),
    )

    if not st.session_state.last_completed.empty:
        st.success(f"Completed {len(st.session_state.last_completed):,} cases in this simulation step.")


def _render_delay_dashboard(simulation: FairQueueSimulation) -> None:
    st.subheader("Neighborhood Delay Boosts")

    initial_tracker = FairQueueSimulation(simulation.initial_active_df).delay_tracker()
    current_summary = simulation.delay_tracker().boost_summary()
    initial_summary = initial_tracker.boost_summary()
    comparison = _delay_comparison(initial_summary, current_summary)
    queue_df = simulation.queue_dataframe()

    left, right = st.columns([1.2, 1])

    with left:
        st.write("Neighborhood delay table")
        st.dataframe(
            comparison,
            hide_index=True,
            use_container_width=True,
        )

    with right:
        category_summary = _category_summary(queue_df)
        st.write("Top 3 categories overall")
        if category_summary.empty:
            st.info("No active ranked cases remain.")
        else:
            st.dataframe(category_summary, hide_index=True, use_container_width=True)


def _render_queue(simulation: FairQueueSimulation) -> None:
    st.subheader("Strict Fair Queue")
    queue_df = simulation.queue_dataframe()

    if queue_df.empty:
        st.info("No active ranked cases remain in the queue.")
        return

    preview = queue_df.head(25).copy().reset_index(drop=True)
    preview.insert(0, "Queue rank", range(1, len(preview) + 1))
    preview["urgency_score"] = preview["urgency_score"].astype(int)
    preview["neighborhood_delay_boost"] = preview["neighborhood_delay_boost"].map(_round_number)
    preview["days_open"] = preview["days_open"].map(_round_number)
    columns = [
        "Queue rank",
        "CaseID",
        "Category",
        "Neighborhood",
        "urgency_score",
        "neighborhood_delay_boost",
        "days_open",
    ]
    st.dataframe(preview[columns], hide_index=True, use_container_width=True)


def _delay_comparison(initial_summary: pd.DataFrame, current_summary: pd.DataFrame) -> pd.DataFrame:
    comparison = initial_summary.merge(
        current_summary[
            [
                "Neighborhood",
                "avg_days_open",
                "neighborhood_delay_boost",
                "total_cases",
            ]
        ],
        on="Neighborhood",
        how="left",
        suffixes=("_initial", "_current"),
    )
    comparison["avg_days_open_current"] = comparison["avg_days_open_current"].fillna(0)
    comparison["neighborhood_delay_boost_current"] = comparison[
        "neighborhood_delay_boost_current"
    ].fillna(0)
    comparison["total_cases_current"] = comparison["total_cases_current"].fillna(0)
    comparison["avg_days_change"] = (
        comparison["avg_days_open_current"] - comparison["avg_days_open_initial"]
    )
    display = comparison[
        [
            "Neighborhood",
            "avg_days_open_initial",
            "avg_days_open_current",
            "neighborhood_delay_boost_current",
            "total_cases_current",
        ]
    ].copy()
    display["avg_days_open_initial"] = display["avg_days_open_initial"].map(_round_number)
    display["avg_days_open_current"] = display["avg_days_open_current"].map(_round_number)
    display["avg_days_change"] = (
        display["avg_days_open_current"] - display["avg_days_open_initial"]
    ).map(_format_signed_change)
    display["neighborhood_delay_boost_current"] = display["neighborhood_delay_boost_current"].map(
        _round_number
    )
    display["total_cases_current"] = display["total_cases_current"].astype(int)
    display = display.sort_values(
        ["neighborhood_delay_boost_current", "avg_days_open_current", "total_cases_current"],
        ascending=[False, False, False],
    )
    display = display.rename(
        columns={
            "avg_days_open_initial": "Initial avg days open",
            "avg_days_open_current": "Current avg days open",
            "avg_days_change": "Avg days change",
            "neighborhood_delay_boost_current": "Current delay boost",
            "total_cases_current": "Active cases",
        }
    )
    return display[
        [
            "Neighborhood",
            "Initial avg days open",
            "Current avg days open",
            "Avg days change",
            "Current delay boost",
            "Active cases",
        ]
    ]


def _category_summary(queue_df: pd.DataFrame) -> pd.DataFrame:
    if queue_df.empty:
        return pd.DataFrame()

    summary = (
        queue_df.groupby("Category")
        .agg(
            total_cases=("CaseID", "count"),
            avg_days_open=("days_open", "mean"),
        )
        .reset_index()
        .sort_values(["total_cases", "avg_days_open"], ascending=[False, False])
        .head(3)
    )
    summary["avg_days_open"] = summary["avg_days_open"].map(_round_number)
    return summary


def _format_metric(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{_round_number(value):,}"


def _round_number(value: float | int) -> int | None:
    if pd.isna(value):
        return None
    return int(round(float(value)))


def _format_signed_change(value: float | int) -> str:
    if pd.isna(value):
        return "0"

    numeric_value = float(value)
    rounded_value = _round_number(abs(numeric_value))
    if numeric_value > 0:
        return f"+{rounded_value}"
    if numeric_value < 0:
        return f"-{rounded_value}"
    return "0"


if __name__ == "__main__":
    main()
