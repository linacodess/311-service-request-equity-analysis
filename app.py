"""Streamlit dashboard for simulating the fair service queue."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from service_request_equity.data_loader import DataLoader
from service_request_equity.map_visualization import plot_neighborhood_boundaries
from service_request_equity.simulation import FairQueueSimulation

DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "311_service_requests_2026.csv"
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_311_cases.csv"
COMPLETION_COUNT = 10000
DEFAULT_ACTIVE_CASE_MAX_DAYS_OPEN = 90
DELAY_COLORMAP = LinearSegmentedColormap.from_list(
    "delay_green_to_brown",
    ["#1a9850", "#fee08b", "#d73027", "#4d1f0c"],
)


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

    simulation_tab, impact_tab, map_tab = st.tabs(
        ["Simulation", "Neighborhood Impact", "Map"]
    )

    with simulation_tab:
        _render_controls(simulation)
        _render_summary(simulation)
        _render_queue(simulation)

    with impact_tab:
        _render_neighborhood_impact(simulation)

    with map_tab:
        _render_map(simulation)


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


def _render_neighborhood_impact(simulation: FairQueueSimulation) -> None:
    st.subheader("Neighborhood Delay Boosts")

    initial_tracker = FairQueueSimulation(simulation.initial_active_df).delay_tracker()
    current_summary = simulation.delay_tracker().boost_summary()
    initial_summary = initial_tracker.boost_summary()
    comparison = _delay_comparison(initial_summary, current_summary)

    st.write("Average days open before and after the simulation")
    _render_neighborhood_bar_chart(comparison)

    st.write("Neighborhood delay table")
    st.dataframe(
        comparison,
        hide_index=True,
        width="stretch",
    )


def _render_map(simulation: FairQueueSimulation) -> None:
    st.subheader("Current Queue Map")
    queue_df = simulation.queue_dataframe()

    if queue_df.empty:
        st.info("No active ranked cases remain to map.")
        return

    coords = queue_df.dropna(subset=["Longitude", "Latitude", "days_open"]).copy()
    if coords.empty:
        st.info("No valid coordinates available for the current queue.")
        return

    st.caption("Dots show current ranked queue cases. Color is based on days open.")
    fig = _case_map_figure(coords)
    st.pyplot(fig)
    plt.close(fig)


def _render_queue(simulation: FairQueueSimulation) -> None:
    st.subheader("Strict Fair Queue")
    queue_df = simulation.queue_dataframe()

    if queue_df.empty:
        st.info("No active ranked cases remain in the queue.")
        return

    ranked_queue = queue_df.copy().reset_index(drop=True)
    ranked_queue.insert(0, "Queue rank", range(1, len(ranked_queue) + 1))
    categories = sorted(ranked_queue["Category"].dropna().unique())
    selected_categories = st.multiselect(
        "Display categories",
        options=categories,
        default=categories,
        help="This only filters the table display. The simulation still completes cases from the full fair queue.",
    )
    if selected_categories:
        ranked_queue = ranked_queue[ranked_queue["Category"].isin(selected_categories)]

    preview = ranked_queue.head(25).copy().reset_index(drop=True)
    if preview.empty:
        st.info("No queue cases match the selected category filter.")
        return

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
    st.dataframe(preview[columns], hide_index=True, width="stretch")


def _render_neighborhood_bar_chart(comparison: pd.DataFrame) -> None:
    if comparison.empty:
        st.info("No neighborhood data available.")
        return

    chart_df = comparison.sort_values("Initial avg days open", ascending=True)
    neighborhoods = chart_df["Neighborhood"].tolist()
    y_positions = range(len(chart_df))

    fig_height = max(5, len(chart_df) * 0.42)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    ax.barh(
        [position - 0.18 for position in y_positions],
        chart_df["Initial avg days open"],
        height=0.34,
        color="#96add6",
        label="Initial",
    )
    ax.barh(
        [position + 0.18 for position in y_positions],
        chart_df["Current avg days open"],
        height=0.34,
        color="#e85234",
        label="Current",
    )
    ax.set_yticks(list(y_positions), neighborhoods)
    ax.set_xlabel("Average days open")
    ax.set_ylabel("Neighborhood")
    ax.legend()
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _case_map_figure(queue_df: pd.DataFrame) -> plt.Figure:
    days_open = pd.to_numeric(queue_df["days_open"], errors="coerce")
    color_cap = _percentile_cap(days_open, percentile=0.95)

    fig, ax = plt.subplots(figsize=(10, 7))
    plot_neighborhood_boundaries(ax)
    scatter = ax.scatter(
        queue_df["Longitude"],
        queue_df["Latitude"],
        c=days_open.clip(upper=color_cap),
        cmap=DELAY_COLORMAP,
        vmin=0,
        vmax=color_cap,
        s=7,
        alpha=0.28,
        edgecolors="none",
        zorder=2,
    )
    ax.set_title("Current Active Queue Cases")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="box")
    fig.colorbar(scatter, ax=ax, label=f"Days open (capped at {_round_number(color_cap)})")
    fig.tight_layout()
    return fig


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


def _format_metric(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{_round_number(value):,}"


def _round_number(value: float | int) -> int | None:
    if pd.isna(value):
        return None
    return int(round(float(value)))


def _percentile_cap(series: pd.Series, percentile: float) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return 1.0
    cap = float(numeric.quantile(percentile))
    return max(cap, 1.0)


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
