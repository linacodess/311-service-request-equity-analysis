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

SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_311_cases.csv"
APP_DATA_PATH = PROJECT_ROOT / "data" / "app_queue_cases_110_days.csv"
COMPLETION_COUNT = 5000
APP_DATA_MAX_DAYS_OPEN = 110
BLUE_DUNE = "#003198"
AZURE_HORIZON = "#95cde8"
PUMPKIN_VIBE = "#e05502"
MISTY_CANVAS = "#dad1ca"
LIGHT_CANVAS = "#f7f3ef"
SOFT_CANVAS = "#efe8e1"
DELAY_COLORMAP = LinearSegmentedColormap.from_list(
    "delay_vivid_blue_to_orange",
    [AZURE_HORIZON, "#2772c7", PUMPKIN_VIBE, "#b83200"],
)


def main() -> None:
    st.set_page_config(page_title="Fair Service Queue Simulation", layout="wide")
    _apply_theme_css()
    _render_title()

    data_path = APP_DATA_PATH if APP_DATA_PATH.exists() else SAMPLE_DATA_PATH
    active_df = _load_initial_cases(data_path)
    simulation = _get_simulation(data_path, active_df)

    overview_tab, queue_tab, impact_tab, map_tab = st.tabs(
        ["Overview", "Queue", "Impact", "Map"]
    )

    with overview_tab:
        _render_overview()
        _render_overview_metrics(active_df)

    with queue_tab:
        _render_summary(simulation)
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
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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

        div.stButton > button:not([kind="primary"]),
        div.stButton > button:not([kind="primary"]) p {
            color: #d10000 !important;
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


def _render_title() -> None:
    title_col, reset_col = st.columns([0.78, 0.22], vertical_alignment="center")

    with title_col:
        st.title("Fair Service Queue Simulation")

    with reset_col:
        st.button(
            "Reset simulation",
            on_click=_reset_simulation,
            width="stretch",
        )


def _render_overview() -> None:
    st.markdown(
        (
            '<div class="project-description">'
            "This project simulates a fair queue for Boston 311 service requests. "
            "It ranks urgent requests first, then gives priority to neighborhoods "
            "that currently wait longer than others. As cases are completed, the goal "
            "is to reduce average delays over time for neighborhoods that used to wait "
            "longer. The app uses a prepared 2026 sample with open, queue-eligible "
            f"cases capped at {APP_DATA_MAX_DAYS_OPEN} days open, so stale records do "
            "not dominate the simulation."
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_overview_metrics(
    active_df: pd.DataFrame,
) -> None:
    neighborhood_count = active_df["Neighborhood"].nunique()
    category_count = active_df["Category"].nunique()
    metrics = [
        ("Neighborhoods represented", f"{neighborhood_count:,}"),
        ("Queue cases loaded", f"{len(active_df):,}"),
        ("Categories represented", f"{category_count:,}"),
        ("Prepared day cap", f"{APP_DATA_MAX_DAYS_OPEN} days"),
    ]
    _render_metric_cards(metrics)


@st.cache_data(show_spinner="Loading 311 data...")
def _load_initial_cases(data_path: Path) -> pd.DataFrame:
    loader = DataLoader(data_path)
    loader.load()
    return loader.get_active_cases()


def _get_simulation(
    data_path: Path,
    active_df: pd.DataFrame,
) -> FairQueueSimulation:
    state_key = str(data_path)
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
    _render_metric_cards(metrics)

    if not st.session_state.last_completed.empty:
        st.success(f"Completed {len(st.session_state.last_completed):,} cases in this simulation step.")


def _render_metric_cards(metrics: list[tuple[str, str]]) -> None:
    cards = "\n".join(
        f'<div class="metric-card">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f"</div>"
        for label, value in metrics
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def _render_neighborhood_impact(simulation: FairQueueSimulation) -> None:
    st.subheader("Neighborhood Delay Boosts")

    initial_tracker = FairQueueSimulation(simulation.initial_active_df).delay_tracker()
    current_summary = simulation.delay_tracker().boost_summary()
    initial_summary = initial_tracker.boost_summary()
    comparison = _delay_comparison(initial_summary, current_summary)

    st.write("Average days open before and after the simulation")
    _render_neighborhood_bar_chart(comparison)


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


def _reset_simulation() -> None:
    simulation = st.session_state.get("simulation")
    if simulation is not None:
        simulation.reset()
    st.session_state.last_completed = pd.DataFrame()


def _render_neighborhood_bar_chart(comparison: pd.DataFrame) -> None:
    if comparison.empty:
        st.info("No neighborhood data available.")
        return

    chart_df = comparison.sort_values(
        ["Current delay boost", "Current avg days open"],
        ascending=[False, False],
    ).head(12)
    chart_df = chart_df.sort_values("Initial avg days open", ascending=True)
    neighborhoods = chart_df["Neighborhood"].tolist()
    y_positions = range(len(chart_df))

    fig_height = max(4.2, len(chart_df) * 0.34)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.barh(
        [position - 0.18 for position in y_positions],
        chart_df["Initial avg days open"],
        height=0.3,
        color=AZURE_HORIZON,
        label="Initial",
    )
    current_bars = ax.barh(
        [position + 0.18 for position in y_positions],
        chart_df["Current avg days open"],
        height=0.3,
        color=PUMPKIN_VIBE,
        label="Current",
    )
    max_value = max(
        chart_df["Initial avg days open"].max(),
        chart_df["Current avg days open"].max(),
        1,
    )
    for bar, change in zip(current_bars, chart_df["Avg days change"]):
        x_position = bar.get_width() + max_value * 0.015
        y_position = bar.get_y() + bar.get_height() / 2
        ax.text(
            x_position,
            y_position,
            change,
            va="center",
            color=BLUE_DUNE,
            fontsize=9,
            fontweight="bold",
        )

    ax.set_yticks(list(y_positions), neighborhoods)
    ax.set_xlabel("Average days open")
    ax.set_ylabel("")
    ax.set_xlim(right=max_value * 1.18)
    ax.legend(loc="lower right")
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
        alpha=0.42,
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
