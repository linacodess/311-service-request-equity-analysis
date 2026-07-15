"""Neighborhood delay boost tracking for fair service prioritization."""

from __future__ import annotations

import pandas as pd


class DelayTracker:
    """Calculate neighborhood delay boosts from service request history."""

    def __init__(self) -> None:
        self.citywide_avg_days_open: float | None = None
        self._summary = pd.DataFrame(
            columns=[
                "Neighborhood",
                "total_cases",
                "avg_days_open",
                "neighborhood_delay_boost",
            ]
        )

    def refresh(self, df: pd.DataFrame) -> None:
        """Recalculate citywide and neighborhood delay metrics."""
        self._require_columns(df, ["Neighborhood", "days_open"])
        working = df.copy()
        working["days_open"] = pd.to_numeric(working["days_open"], errors="coerce")
        valid = working.dropna(subset=["Neighborhood", "days_open"])
        if valid.empty:
            raise ValueError("DelayTracker requires at least one valid neighborhood and days_open row.")

        self.citywide_avg_days_open = float(valid["days_open"].mean())
        summary = (
            valid.groupby("Neighborhood")
            .agg(
                total_cases=("days_open", "count"),
                avg_days_open=("days_open", "mean"),
            )
            .reset_index()
        )
        delay_gap = (summary["avg_days_open"] - self.citywide_avg_days_open).clip(lower=0)
        summary["neighborhood_delay_boost"] = delay_gap
        self._summary = self._round_float_columns(
            summary.sort_values(
                ["neighborhood_delay_boost", "avg_days_open", "total_cases"],
                ascending=[False, False, False],
            ).reset_index(drop=True)
        )

    def get_neighborhood_boost(self, neighborhood: str) -> float:
        """Return the current delay boost for a neighborhood, or 0 if unknown."""
        if self._summary.empty:
            return 0.0

        matches = self._summary[self._summary["Neighborhood"] == neighborhood]
        if matches.empty:
            return 0.0
        return float(matches.iloc[0]["neighborhood_delay_boost"])

    def boost_summary(self) -> pd.DataFrame:
        """Return the latest neighborhood delay boost summary."""
        return self._summary.copy()

    @staticmethod
    def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
        missing = [column for column in columns if column not in df.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _round_float_columns(df: pd.DataFrame) -> pd.DataFrame:
        rounded = df.copy()
        for column in rounded.select_dtypes(include=["float"]).columns:
            rounded[column] = rounded[column].round(2)
        return rounded
