"""Urgency ranking and sorting helpers for 311 service request data."""

from __future__ import annotations

import pandas as pd

DEFAULT_URGENCY_RANKING: dict[str, int] = {
    "Needle Pickup": 1,
    "Street Light Outages": 2,
    "Parking Enforcement": 3,
    "Sign Repair": 4,
    "Bed Bugs": 5,
    "Poor Conditions of Property": 6,
    "Missed Trash / Recycling / Yard Waste / Bulk Item": 7,
    "Requests for Street Cleaning": 8,
    "Graffiti Removal": 9,
    "Abandoned Bicycle": 10,
}


class CaseSorter:
    """Sort cases by duration and by a documented urgency ranking."""

    def __init__(self, urgency_ranking: dict[str, int] | None = None) -> None:
        self.urgency_ranking = urgency_ranking or DEFAULT_URGENCY_RANKING.copy()

    def sort_by_days_open(self, df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
        """Return cases sorted by how long they stayed open."""
        self._require_columns(df, ["days_open"])
        self._require_numeric_days_open(df)
        return df.sort_values("days_open", ascending=ascending, na_position="last").copy()

    def filter_ranked_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only categories represented in the urgency ranking."""
        self._require_columns(df, ["Category"])
        ranked = df[df["Category"].isin(self.urgency_ranking)].copy()
        if ranked.empty:
            raise ValueError("No rows match the configured urgency ranking.")
        return ranked

    def add_urgency_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add an urgency_score column, where 1 means most urgent."""
        self._require_columns(df, ["Category"])
        scored = df.copy()
        scored["urgency_score"] = scored["Category"].map(self.urgency_ranking)

        missing = sorted(scored.loc[scored["urgency_score"].isna(), "Category"].dropna().unique())
        if missing:
            missing_display = ", ".join(missing[:5])
            raise ValueError(f"Categories missing urgency rankings: {missing_display}")

        scored["urgency_score"] = scored["urgency_score"].astype(int)
        return scored

    def sort_by_urgency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep ranked categories, then sort by urgency and days open."""
        self._require_columns(df, ["Category", "days_open"])
        ranked = self.filter_ranked_categories(df)
        self._require_numeric_days_open(ranked)
        scored = self.add_urgency_scores(ranked)
        return scored.sort_values(
            ["urgency_score", "days_open"],
            ascending=[True, False],
            na_position="last",
        ).reset_index(drop=True)

    def sort_by_fair_service_queue(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Keep ranked categories, then sort by urgency, days open, and delay fairness."""
        self._require_columns(df, ["Category", "Neighborhood", "days_open", "neighborhood_delay_boost"])

        ranked = self.filter_ranked_categories(df)
        self._require_numeric_days_open(ranked)
        queued = self.add_urgency_scores(ranked)
        queued["neighborhood_delay_boost"] = (
            pd.to_numeric(queued["neighborhood_delay_boost"], errors="coerce")
            .fillna(0)
            .clip(lower=0)
            .round(2)
        )

        return queued.sort_values(
            ["urgency_score", "neighborhood_delay_boost", "days_open"],
            ascending=[True, False, False],
            na_position="last",
        ).reset_index(drop=True)

    @staticmethod
    def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
        missing = [column for column in columns if column not in df.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _require_numeric_days_open(df: pd.DataFrame) -> None:
        if not pd.api.types.is_numeric_dtype(df["days_open"]):
            raise ValueError("days_open must be numeric.")
