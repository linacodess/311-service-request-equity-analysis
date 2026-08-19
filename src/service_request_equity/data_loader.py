"""CSV loading and validation for 311 service request datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

CORE_COLUMNS = (
    "CaseID",
    "Status",
    "Category",
    "Neighborhood",
    "Latitude",
    "Longitude",
)


class DataLoader:
    """Load and lightly clean 311 service request data."""

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self.df: pd.DataFrame | None = None

    @property
    def is_processed(self) -> bool:
        """Return whether a DataFrame has been loaded successfully."""
        return self.df is not None and not self.df.empty

    def load(self, nrows: int | None = None) -> pd.DataFrame:
        """Load, validate, and clean a 311 CSV file."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {self.filepath}")

        if self.filepath.suffix.lower() != ".csv":
            raise ValueError("DataLoader only supports CSV files.")

        df = pd.read_csv(self.filepath, index_col=False, nrows=nrows)
        if df.empty:
            raise ValueError("CSV loaded successfully but contains no rows.")

        df = self._normalize_boston_columns(df)
        self._validate_columns(df)
        cleaned = self._clean_core_fields(df)
        self.df = cleaned
        return cleaned

    def get_basic_stats(self) -> dict[str, Any]:
        """Return high-level dataset statistics."""
        if self.df is None:
            raise ValueError("Data has not been loaded yet.")

        return {
            "shape": self.df.shape,
            "total_cases": int(len(self.df)),
            "unique_neighborhoods": int(self.df["Neighborhood"].nunique()),
            "unique_categories": int(self.df["Category"].nunique()),
        }

    def filter_by_neighborhood(self, neighborhoods: list[str]) -> pd.DataFrame:
        """Return rows matching the given neighborhoods, case-insensitively."""
        if self.df is None:
            raise ValueError("Data has not been loaded yet.")
        if not neighborhoods:
            raise ValueError("At least one neighborhood is required.")

        targets = {name.casefold().strip() for name in neighborhoods}
        mask = self.df["Neighborhood"].str.casefold().isin(targets)
        filtered = self.df.loc[mask].copy()

        if filtered.empty:
            raise ValueError("No rows matched the requested neighborhood filter.")

        return filtered

    @staticmethod
    def _validate_columns(df: pd.DataFrame) -> None:
        missing = [column for column in CORE_COLUMNS if column not in df.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _normalize_boston_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Support both the original sample columns and Boston's newer export columns."""
        column_mapping = {
            "case_enquiry_id": "CaseID",
            "case_status": "Status",
            "type": "Category",
            "neighborhood": "Neighborhood",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "open_dt": "OpenedDate",
            "closed_dt": "ClosedDate",
        }
        normalized = df.copy()
        for source, target in column_mapping.items():
            if source in normalized.columns and target not in normalized.columns:
                normalized[target] = normalized[source]
        return normalized

    @staticmethod
    def _clean_core_fields(df: pd.DataFrame) -> pd.DataFrame:
        cleaned = df.copy()

        cleaned["Category"] = cleaned["Category"].astype("string").str.strip()
        cleaned["Neighborhood"] = cleaned["Neighborhood"].astype("string").str.strip()
        cleaned["Latitude"] = pd.to_numeric(cleaned["Latitude"], errors="coerce")
        cleaned["Longitude"] = pd.to_numeric(cleaned["Longitude"], errors="coerce")

        if "days_open" in cleaned.columns:
            cleaned["days_open"] = pd.to_numeric(cleaned["days_open"], errors="coerce")
        else:
            cleaned["days_open"] = DataLoader._calculate_days_open(cleaned)

        cleaned = cleaned.dropna(subset=["Category", "Neighborhood"])
        cleaned = cleaned[cleaned["Category"] != ""]
        cleaned = cleaned[cleaned["Neighborhood"] != ""]
        return cleaned.reset_index(drop=True)

    @staticmethod
    def _calculate_days_open(df: pd.DataFrame) -> pd.Series:
        if "OpenedDate" not in df.columns or "ClosedDate" not in df.columns:
            raise KeyError("Missing days_open and unable to compute it without OpenedDate and ClosedDate.")

        opened = pd.to_datetime(df["OpenedDate"], errors="coerce")
        closed = pd.to_datetime(df["ClosedDate"], errors="coerce")
        return (closed - opened).dt.total_seconds() / 86400
