"""Equity-oriented summaries for 311 service request data."""

from __future__ import annotations

from typing import Any

import pandas as pd


class NeighborhoodAnalyzer:
    """Analyze duration, category, and neighborhood patterns in 311 data."""

    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data.copy()
        self._require_columns(["Category", "Neighborhood", "days_open"])

    def average_days_open(self) -> float:
        """Return the average number of days a request stayed open."""
        return float(self.data["days_open"].dropna().mean())

    def above_average_neighborhood_counts(self) -> pd.Series:
        """Count above-average-duration cases by neighborhood."""
        avg_days_open = self.average_days_open()
        above_average = self.data[self.data["days_open"] > avg_days_open]
        return above_average["Neighborhood"].value_counts()

    def category_duration_summary(self) -> pd.DataFrame:
        """Summarize resolution duration by service category."""
        summary = (
            self.data.dropna(subset=["days_open"])
            .groupby("Category")
            .agg(
                total_cases=("CaseID", "count") if "CaseID" in self.data.columns else ("days_open", "count"),
                avg_days_open=("days_open", "mean"),
                median_days_open=("days_open", "median"),
                max_days_open=("days_open", "max"),
            )
            .sort_values(["avg_days_open", "total_cases"], ascending=[False, False])
            .reset_index()
        )
        return self._round_float_columns(summary)

    def neighborhood_volume_summary(self) -> pd.DataFrame:
        """Summarize case volume and delay rate by neighborhood."""
        avg_days_open = self.average_days_open()
        working = self.data.copy()
        working["above_average_duration"] = working["days_open"] > avg_days_open

        summary = (
            working.groupby("Neighborhood")
            .agg(
                total_cases=("CaseID", "count") if "CaseID" in working.columns else ("days_open", "count"),
                avg_days_open=("days_open", "mean"),
                above_average_cases=("above_average_duration", "sum"),
            )
            .sort_values(["above_average_cases", "total_cases"], ascending=[False, False])
            .reset_index()
        )
        summary["pct_above_average"] = summary["above_average_cases"] / summary["total_cases"]
        return self._round_float_columns(summary)

    def equity_priority_scores(self) -> pd.DataFrame:
        """
        Rank neighborhoods by a transparent equity priority score.

        The score combines delay rate, average duration, and request volume.
        It is meant to flag neighborhoods worth a closer human review, not to
        prove the cause of any disparity on its own.
        """
        summary = self.neighborhood_volume_summary()
        scored = summary.copy()

        delay_component = self._scale_by_max(scored["pct_above_average"])
        duration_component = self._scale_by_max(scored["avg_days_open"])
        volume_component = self._scale_by_max(scored["total_cases"])

        scored["equity_priority_score"] = (
            (0.45 * delay_component)
            + (0.35 * duration_component)
            + (0.20 * volume_component)
        ) * 100

        return self._round_float_columns(
            scored.sort_values("equity_priority_score", ascending=False).reset_index(drop=True)
        )

    def equity_snapshot(self, top_n: int = 5) -> dict[str, Any]:
        """Return JSON-serializable headline metrics and top findings."""
        category_summary = self.category_duration_summary().head(top_n)
        neighborhood_summary = self.neighborhood_volume_summary().head(top_n)
        equity_scores = self.equity_priority_scores().head(top_n)

        return {
            "total_cases_analyzed": int(len(self.data)),
            "unique_neighborhoods": int(self.data["Neighborhood"].nunique()),
            "unique_categories": int(self.data["Category"].nunique()),
            "avg_days_open": round(self.average_days_open(), 2),
            "neighborhoods_with_most_above_average_cases": neighborhood_summary.to_dict(orient="records"),
            "slowest_categories_by_avg_days_open": category_summary.to_dict(orient="records"),
            "top_equity_priority_neighborhoods": equity_scores.to_dict(orient="records"),
        }

    def _require_columns(self, columns: list[str]) -> None:
        missing = [column for column in columns if column not in self.data.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _round_float_columns(df: pd.DataFrame) -> pd.DataFrame:
        rounded = df.copy()
        for column in rounded.select_dtypes(include=["float"]).columns:
            rounded[column] = rounded[column].round(2)
        return rounded

    @staticmethod
    def _scale_by_max(series: pd.Series) -> pd.Series:
        max_value = series.max()
        if max_value == 0:
            return series * 0
        return series / max_value
