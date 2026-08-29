"""Streamlit dashboard for simulating the fair service queue."""

from __future__ import annotations

import html
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
BLUE_DUNE = "#003198"
AZURE_HORIZON = "#95cde8"
PUMPKIN_VIBE = "#e05502"
MISTY_CANVAS = "#dad1ca"
LIGHT_CANVAS = "#f7f3ef"
SOFT_CANVAS = "#efe8e1"
DELAY_COLORMAP = LinearSegmentedColormap.from_list(
    "delay_blue_to_orange",
    [AZURE_HORIZON, PUMPKIN_VIBE],
)


def main() -> None:
    st.set_page_config(page_title="Fair Service Queue Simulation", layout="wide")
    _apply_theme_css()

    data_path = _data_path_input()
    max_days_open = _active_case_limit_input()
    active_df, total_open_cases = _load_initial_cases(data_path, max_days_open)
    simulation = _get_simulation(data_path, max_days_open, active_df)

    excluded_count = total_open_cases - len(active_df)
    _render_header(simulation, max_days_open, excluded_count, total_open_cases)
    _render_summary(simulation)

    queue_tab, impact_tab, map_tab = st.tabs(["Queue", "Impact", "Map"])

    with queue_tab:
        _render_queue(simulation)

    with impact_tab:
        _render_neighborhood_impact(simulation)

    with map_tab:
        _render_map(simulation)


def _apply_theme_css() -> None:
    st.markdown(
        """
        <style>
        .project-description {
            background: #efe8e1;
            border: 1px solid rgba(0, 49, 152, 0.16);
            border-left: 5px solid #e05502;
            border-radius: 10px;
            color: #16345f;
            font-size: 1rem;
            line-height: 1.55;
            margin: 0.25rem 0 1.2rem;
            padding: 1rem 1.15rem;
        }

        .metric-grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin: 0.8rem 0 1.6rem;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.48);
            border: 1px solid rgba(0, 49, 152, 0.12);
            border-radius: 14px;
            box-shadow: 0 14px 34px rgba(0, 49, 152, 0.06);
            padding: 1rem 1.1rem;
        }

        .metric-label {
            color: rgba(0, 49, 152, 0.72);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.3rem;
            text-transform: uppercase;
        }

        .metric-value {
            color: #003198;
            font-size: 2.05rem;
            font-weight: 800;
            line-height: 1.05;
        }

        div[data-testid="stTabs"] button {
            padding: 0.8rem 1.15rem;
        }

        div[data-testid="stTabs"] button p {
            color: #003198;
            font-size: 1.3rem;
            font-weight: 750;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] p {
            color: #e05502;
        }

        div.stButton > button {
            min-height: 2.75rem;
            font-weight: 650;
            font-size: 0.95rem;
        }

        div.stButton > button p {
            font-size: 0.95rem;
            font-weight: 650;
        }

        div.stButton > button[kind="primary"],
        div.stButton > button[kind="primary"] p {
            color: #f7f3ef !important;
        }

        div[data-testid="stButtonGroup"] [data-variant="pills"] {
            min-height: 1.85rem !important;
            padding: 0.16rem 0.55rem !important;
            border-radius: 999px !important;
        }

        div[data-testid="stButtonGroup"] [data-variant="pills"] p {
            font-size: 0.78rem;
            font-weight: 600;
            line-height: 1.1;
        }

        div[data-testid="stButtonGroup"] [data-variant="pills"][aria-selected="true"],
        div[data-testid="stButtonGroup"] [data-variant="pills"][aria-pressed="true"],
        div[data-testid="stButtonGroup"] [data-variant="pills"][data-selected="true"] {
            background-color: rgba(224, 85, 2, 0.14);
            border-color: rgba(224, 85, 2, 0.45);
        }

        div[data-testid="stButtonGroup"] [data-variant="pills"][aria-selected="true"] p,
        div[data-testid="stButtonGroup"] [data-variant="pills"][aria-pressed="true"] p,
        div[data-testid="stButtonGroup"] [data-variant="pills"][data-selected="true"] p {
            color: #003198 !important;
        }

        .queue-list {
            display: grid;
            gap: 0.7rem;
            margin-top: 1rem;
        }

        .queue-card {
            align-items: center;
            background: rgba(255, 255, 255, 0.56);
            border: 1px solid rgba(0, 49, 152, 0.12);
            border-left: 5px solid #95cde8;
            border-radius: 14px;
            box-shadow: 0 12px 28px rgba(0, 49, 152, 0.05);
            display: grid;
            gap: 1rem;
            grid-template-columns: 3rem 1.2fr 1.45fr 1.15fr 0.8fr 1fr 0.8fr;
            padding: 0.85rem 1rem;
        }

        .queue-rank {
            align-items: center;
            background: #003198;
            border-radius: 999px;
            color: #f7f3ef;
            display: flex;
            font-size: 0.9rem;
            font-weight: 800;
            height: 2.25rem;
            justify-content: center;
            width: 2.25rem;
        }

        .queue-label {
            color: rgba(0, 49, 152, 0.62);
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
        }

        .queue-value {
            color: #12315c;
            font-size: 0.92rem;
            font-weight: 700;
            line-height: 1.25;
            margin-top: 0.15rem;
        }

        .urgency-pill {
            align-items: center;
            background: rgba(149, 205, 232, 0.38);
            border-radius: 999px;
            color: #003198;
            display: inline-flex;
            font-weight: 800;
            height: 2rem;
            justify-content: center;
            width: 2rem;
        }

        .mini-bar {
            background: rgba(0, 49, 152, 0.1);
            border-radius: 999px;
            height: 0.38rem;
            margin-top: 0.3rem;
            overflow: hidden;
            width: 100%;
        }

        .mini-bar-fill {
            background: #e05502;
            border-radius: 999px;
            height: 100%;
        }

        @media (max-width: 900px) {
            .metric-grid,
            .queue-card {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(
    simulation: FairQueueSimulation,
    max_days_open: int,
    excluded_count: int,
    total_open_cases: int,
) -> None:
    title_col, reset_col = st.columns([0.78, 0.22], vertical_alignment="center")

    with title_col:
        st.title("Fair Service Queue Simulation")

    with reset_col:
        st.button(
            "Reset simulation",
            on_click=_reset_simulation,
            args=(simulation,),
            width="stretch",
        )

    st.markdown(
        f"""
        <div class="project-description">
        This project simulates a fair queue for Boston 311 service requests. It ranks urgent
        requests first, then gives priority to neighborhoods that currently wait longer than
        others. As cases are completed, the goal is to reduce average delays over time for
        neighborhoods that used to wait longer. Open cases beyond {max_days_open} days are
        treated as stale and excluded because very long-open records are often resolved but
        not marked closed, especially Parking Enforcement. {excluded_count:,} of
        {total_open_cases:,} open cases are excluded by the current day limit.
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def _render_summary(simulation: FairQueueSimulation) -> None:
    summary = simulation.summary()
    current_tracker = simulation.delay_tracker()
    queue_df = simulation.queue_dataframe()

    metrics = [
        ("Active queue cases", f"{len(queue_df):,}"),
        ("Completed in simulation", f"{summary['completed_cases']:,}"),
        ("Active avg days open", _format_metric(current_tracker.citywide_avg_days_open)),
    ]
    cards = "\n".join(
        f'<div class="metric-card">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f"</div>"
        for label, value in metrics
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)

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
    title_col, action_col = st.columns([0.78, 0.22], vertical_alignment="center")
    with title_col:
        st.subheader("Queue")
    with action_col:
        st.button(
            "Complete cases",
            type="primary",
            on_click=_complete_next_cases,
            args=(simulation,),
            width="stretch",
        )

    queue_df = simulation.queue_dataframe()

    if queue_df.empty:
        st.info("No active ranked cases remain in the queue.")
        return

    ranked_queue = queue_df.copy().reset_index(drop=True)
    ranked_queue.insert(0, "Queue rank", range(1, len(ranked_queue) + 1))
    categories = sorted(ranked_queue["Category"].dropna().unique())
    selected_categories = st.pills(
        "Category",
        options=categories,
        default=categories,
        selection_mode="multi",
        help="This only filters the table display. The simulation still completes cases from the full fair queue.",
        width="stretch",
    )
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
    _render_queue_cards(preview[columns])


def _render_queue_cards(preview: pd.DataFrame) -> None:
    max_boost = max(preview["neighborhood_delay_boost"].max(), 1)
    max_days_open = max(preview["days_open"].max(), 1)
    cards = "\n".join(
        _queue_card_html(row, max_boost=max_boost, max_days_open=max_days_open)
        for _, row in preview.iterrows()
    )
    st.markdown(f'<div class="queue-list">{cards}</div>', unsafe_allow_html=True)


def _queue_card_html(row: pd.Series, max_boost: int, max_days_open: int) -> str:
    rank = _round_number(row["Queue rank"])
    case_id = html.escape(str(row["CaseID"]))
    category = html.escape(str(row["Category"]))
    neighborhood = html.escape(str(row["Neighborhood"]))
    urgency = _round_number(row["urgency_score"])
    delay_boost = _round_number(row["neighborhood_delay_boost"]) or 0
    days_open = _round_number(row["days_open"]) or 0
    delay_width = min((delay_boost / max_boost) * 100, 100)
    days_width = min((days_open / max_days_open) * 100, 100)

    return (
        f'<div class="queue-card">'
        f'<div class="queue-rank">{rank}</div>'
        f"<div>"
        f'<div class="queue-label">Case ID</div>'
        f'<div class="queue-value">{case_id}</div>'
        f"</div>"
        f"<div>"
        f'<div class="queue-label">Category</div>'
        f'<div class="queue-value">{category}</div>'
        f"</div>"
        f"<div>"
        f'<div class="queue-label">Neighborhood</div>'
        f'<div class="queue-value">{neighborhood}</div>'
        f"</div>"
        f"<div>"
        f'<div class="queue-label">Urgency</div>'
        f'<div class="queue-value"><span class="urgency-pill">{urgency}</span></div>'
        f"</div>"
        f"<div>"
        f'<div class="queue-label">Delay boost</div>'
        f'<div class="queue-value">{delay_boost}</div>'
        f'<div class="mini-bar"><div class="mini-bar-fill" style="width: {delay_width:.1f}%"></div></div>'
        f"</div>"
        f"<div>"
        f'<div class="queue-label">Days open</div>'
        f'<div class="queue-value">{days_open}</div>'
        f'<div class="mini-bar"><div class="mini-bar-fill" style="width: {days_width:.1f}%"></div></div>'
        f"</div>"
        f"</div>"
    )


def _complete_next_cases(simulation: FairQueueSimulation) -> None:
    st.session_state.last_completed = simulation.complete_next_cases(COMPLETION_COUNT)


def _reset_simulation(simulation: FairQueueSimulation) -> None:
    simulation.reset()
    st.session_state.last_completed = pd.DataFrame()


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
        color=AZURE_HORIZON,
        label="Initial",
    )
    ax.barh(
        [position + 0.18 for position in y_positions],
        chart_df["Current avg days open"],
        height=0.34,
        color=PUMPKIN_VIBE,
        label="Current",
    )
    ax.set_yticks(list(y_positions), neighborhoods)
    ax.set_xlabel("Average days open")
    ax.set_ylabel("Neighborhood")
    ax.legend()
    ax.grid(axis="x", color=MISTY_CANVAS, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_facecolor(LIGHT_CANVAS)
    fig.patch.set_facecolor(LIGHT_CANVAS)
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
    ax.set_title("Current Active Queue Cases", color=BLUE_DUNE)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="box")
    ax.set_facecolor(LIGHT_CANVAS)
    fig.patch.set_facecolor(LIGHT_CANVAS)
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
