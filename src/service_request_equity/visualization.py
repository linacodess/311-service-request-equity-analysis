"""Matplotlib visualizations for the 311 service request analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


class Visualizer:
    """Create static visual artifacts for portfolio and README use."""

    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data.copy()

    def plot_case_map(self, save_path: str | Path) -> Path:
        """Save a longitude/latitude scatter plot of cases."""
        self._require_columns(["Longitude", "Latitude"])
        output = self._prepare_output_path(save_path)
        coords = self.data.dropna(subset=["Longitude", "Latitude"])

        if coords.empty:
            raise ValueError("No valid coordinates available for map plot.")

        fig, ax = plt.subplots(figsize=(10, 7))
        scatter = ax.scatter(
            coords["Longitude"],
            coords["Latitude"],
            c=coords["days_open"],
            cmap="viridis",
            s=36,
            alpha=0.72,
            edgecolors="none",
        )
        ax.set_title("311 Service Requests by Location")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        fig.colorbar(scatter, ax=ax, label="Days open")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def plot_neighborhood_delays(self, summary: pd.DataFrame, save_path: str | Path, top_n: int = 10) -> Path:
        """Save a bar chart of neighborhoods with the most above-average cases."""
        output = self._prepare_output_path(save_path)
        plot_data = summary.head(top_n).sort_values("above_average_cases")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(plot_data["Neighborhood"], plot_data["above_average_cases"], color="#2b6cb0")
        ax.set_title("Neighborhoods With Most Above-Average Resolution Times")
        ax.set_xlabel("Cases above citywide average")
        ax.set_ylabel("Neighborhood")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def plot_category_durations(self, summary: pd.DataFrame, save_path: str | Path, top_n: int = 10) -> Path:
        """Save a bar chart of the slowest categories by average days open."""
        output = self._prepare_output_path(save_path)
        plot_data = summary.head(top_n).sort_values("avg_days_open")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(plot_data["Category"], plot_data["avg_days_open"], color="#b7791f")
        ax.set_title("Slowest 311 Categories by Average Days Open")
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
    def _prepare_output_path(save_path: str | Path) -> Path:
        output = Path(save_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        return output
