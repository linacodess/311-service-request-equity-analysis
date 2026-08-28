"""Simulation logic for completing cases from the fair service queue."""

from __future__ import annotations

from typing import Any

import pandas as pd

from service_request_equity.delay_tracker import DelayTracker
from service_request_equity.fair_queue import FairServiceQueue


class FairQueueSimulation:
    """Track simulated completions without modifying the original dataset."""

    def __init__(
        self,
        active_df: pd.DataFrame,
        completed_case_ids: list[Any] | None = None,
        case_id_column: str = "CaseID",
    ) -> None:
        self.initial_active_df = active_df.copy().reset_index(drop=True)
        self.case_id_column = case_id_column
        self._completed_case_ids = list(completed_case_ids or [])
        self._require_case_id_column(self.initial_active_df)

    @property
    def completed_case_ids(self) -> list[Any]:
        """Return the case IDs completed during the simulation."""
        return self._completed_case_ids.copy()

    def active_cases(self) -> pd.DataFrame:
        """Return initially open cases that have not been completed yet."""
        completed_ids = set(self._completed_case_ids)
        active = self.initial_active_df[~self.initial_active_df[self.case_id_column].isin(completed_ids)]
        return active.copy().reset_index(drop=True)

    def simulated_completed_cases(self) -> pd.DataFrame:
        """Return initially open cases completed during the simulation."""
        completed = self.initial_active_df[
            self.initial_active_df[self.case_id_column].isin(self._completed_case_ids)
        ].copy()
        if not completed.empty and "Status" in completed.columns:
            completed["Status"] = "Closed"
        return completed.reset_index(drop=True)

    def delay_tracker_data(self) -> pd.DataFrame:
        """Return remaining active cases used for simulation delay boosts."""
        return self.active_cases()

    def delay_tracker(self) -> DelayTracker:
        """Build a delay tracker from the current simulation state."""
        tracker = DelayTracker()
        data = self.delay_tracker_data()
        if not data.empty:
            tracker.refresh(data)
        return tracker

    def queue_dataframe(self) -> pd.DataFrame:
        """Return the current active cases in strict fair queue order."""
        queue = FairServiceQueue(self.active_cases(), delay_tracker=self.delay_tracker())
        return queue.queue_dataframe()

    def complete_next_cases(self, count: int = 100) -> pd.DataFrame:
        """Mark the next cases from the strict queue as completed in the simulation."""
        if count <= 0:
            raise ValueError("count must be greater than zero.")

        selected = self.queue_dataframe().head(count).copy()
        completed_ids = set(self._completed_case_ids)
        new_case_ids = [
            case_id
            for case_id in selected[self.case_id_column].tolist()
            if case_id not in completed_ids
        ]
        self._completed_case_ids.extend(new_case_ids)
        return selected.reset_index(drop=True)

    def reset(self) -> None:
        """Clear all simulated completions."""
        self._completed_case_ids = []

    def summary(self) -> dict[str, int]:
        """Return simple simulation totals for the dashboard."""
        return {
            "active_cases": int(len(self.active_cases())),
            "completed_cases": int(len(self._completed_case_ids)),
        }

    def _require_case_id_column(self, df: pd.DataFrame) -> None:
        if self.case_id_column not in df.columns:
            raise KeyError(f"Missing required column: {self.case_id_column}")
