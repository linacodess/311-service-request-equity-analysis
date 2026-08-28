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

    def get_historical_cases(self) -> pd.DataFrame:
        """Return initially closed cases for historical delay analysis."""
        return self.cases_with_status(self._loaded_data(), "Closed")

    def get_active_cases(
        self,
        today: pd.Timestamp | None = None,
        max_days_open: int | None = None,
    ) -> pd.DataFrame:
        """Return initially open cases with usable days_open values for queue ranking."""
        return self.prepare_active_requests(
            self._loaded_data(),
            today=today,
            max_days_open=max_days_open,
        )

    def _loaded_data(self) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("Data has not been loaded yet.")
        return self.df

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
    def cases_with_status(df: pd.DataFrame, status: str) -> pd.DataFrame:
        """Return cases matching one Status value."""
        status_values = df["Status"].astype("string").str.strip().str.casefold()
        return df.loc[status_values == status.casefold()].copy().reset_index(drop=True)

    @classmethod
    def prepare_active_requests(
        cls,
        df: pd.DataFrame,
        today: pd.Timestamp | None = None,
        max_days_open: int | None = None,
    ) -> pd.DataFrame:
        """Return open requests with usable days_open values for queue ranking."""
        if max_days_open is not None and max_days_open <= 0:
            raise ValueError("max_days_open must be greater than zero.")

        active = cls.cases_with_status(df, "Open")
        if active.empty:
            return active

        active["days_open"] = pd.to_numeric(active["days_open"], errors="coerce")
        missing_days_open = active["days_open"].isna()
        if missing_days_open.any():
            if "OpenedDate" not in active.columns:
                raise KeyError("Open requests with missing days_open require OpenedDate.")

            opened = pd.to_datetime(active.loc[missing_days_open, "OpenedDate"], errors="coerce")
            current_day = pd.Timestamp.today().normalize() if today is None else pd.Timestamp(today).normalize()
            active.loc[missing_days_open, "days_open"] = (
                (current_day - opened).dt.total_seconds().div(86400).clip(lower=0)
            )

        if max_days_open is not None:
            active = active[active["days_open"] <= max_days_open]

        return active.reset_index(drop=True)

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
