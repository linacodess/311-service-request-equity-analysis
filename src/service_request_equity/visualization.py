"""Matplotlib visualizations for the 311 service request analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import pandas as pd


class Visualizer:
    """Create static visual artifacts for portfolio and README use."""

    DELAY_COLORMAP = LinearSegmentedColormap.from_list(
        "delay_green_to_brown",
        ["#1a9850", "#fee08b", "#d73027", "#4d1f0c"],
    )

    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data.copy()

    def plot_case_map(self, save_path: str | Path) -> Path:
        """Save a longitude/latitude scatter plot of cases."""
        self._require_columns(["Longitude", "Latitude", "days_open"])
        output = self._prepare_output_path(save_path)
        coords = self.data.dropna(subset=["Longitude", "Latitude"])
        days_open = pd.to_numeric(coords["days_open"], errors="coerce")
        color_cap = self._percentile_cap(days_open, percentile=0.95)

        if coords.empty:
            raise ValueError("No valid coordinates available for map plot.")

        fig, ax = plt.subplots(figsize=(10, 7))
        scatter = ax.scatter(
            coords["Longitude"],
            coords["Latitude"],
            c=days_open.clip(upper=color_cap),
            cmap=self.DELAY_COLORMAP,
            vmin=0,
            vmax=color_cap,
            s=8,
            alpha=0.28,
            edgecolors="none",
        )
        ax.set_title("311 Service Requests by Location")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        fig.colorbar(scatter, ax=ax, label=f"Days open (capped at {color_cap:g})")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def plot_neighborhood_delays(self, summary: pd.DataFrame, save_path: str | Path, top_n: int = 10) -> Path:
        """Save a bar chart of neighborhoods with the longest average delays."""
        self._require_summary_columns(summary, ["Neighborhood", "avg_days_open"])
        output = self._prepare_output_path(save_path)
        plot_data = summary.head(top_n).sort_values("avg_days_open")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(plot_data["Neighborhood"], plot_data["avg_days_open"], color="#2b6cb0")
        if "citywide_avg_days_open" in plot_data.columns and not plot_data.empty:
            citywide_avg = float(plot_data["citywide_avg_days_open"].iloc[0])
            ax.axvline(citywide_avg, color="#742a2a", linestyle="--", linewidth=1.5, label="Citywide average")
            ax.legend()
        ax.set_title("Neighborhoods With Longest Average Days Open")
        ax.set_xlabel("Average days open")
        ax.set_ylabel("Neighborhood")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def plot_category_durations(self, summary: pd.DataFrame, save_path: str | Path, top_n: int = 10) -> Path:
        """Save a bar chart of categories by average days open."""
        output = self._prepare_output_path(save_path)
        plot_data = summary.head(top_n).sort_values("avg_days_open")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(plot_data["Category"], plot_data["avg_days_open"], color="#b7791f")
        ax.invert_yaxis()
        ax.set_title("311 Categories by Average Days Open")
        ax.set_xlabel("Average days open")
        ax.set_ylabel("Category")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def _require_columns(self, columns: list[str]) -> None:
        missing = [column for column in columns if column not in self.data.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _require_summary_columns(df: pd.DataFrame, columns: list[str]) -> None:
        missing = [column for column in columns if column not in df.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _prepare_output_path(save_path: str | Path) -> Path:
        output = Path(save_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    @staticmethod
    def _percentile_cap(series: pd.Series, percentile: float) -> float:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if numeric.empty:
            return 1.0
        cap = float(numeric.quantile(percentile))
        return max(cap, 1.0)
