"""Live priority queue for 311 service request handling."""

from __future__ import annotations

import heapq
from itertools import count
from typing import Any

import pandas as pd

from service_request_equity.sorting import CaseSorter


class FairServiceQueue:
    """Manage active, treated, and deleted requests in a heap-backed queue."""

    def __init__(
        self,
        requests_df: pd.DataFrame | None = None,
        urgency_ranking: dict[str, int] | None = None,
        case_id_column: str = "CaseID",
    ) -> None:
        self.sorter = CaseSorter(urgency_ranking)
        self.case_id_column = case_id_column
        if requests_df is None:
            self.active_requests = pd.DataFrame()
        else:
            self.active_requests = requests_df.copy().reset_index(drop=True)
            self._require_case_id_column(self.active_requests)
        self.treated_requests = pd.DataFrame()
        self.deleted_requests = pd.DataFrame()
        self._heap: list[tuple[int, float, int, dict[str, Any]]] = []
        self._counter = count()
        self._rebuild_heap()

    def __len__(self) -> int:
        return len(self._heap)

    def add_request(self, request: dict[str, Any]) -> None:
        """Add a request to the active queue and refresh priorities."""
        self._require_case_id(request)
        self.active_requests = self._append_request(self.active_requests, request)
        self._rebuild_heap()

    def peek_next_request(self) -> dict[str, Any]:
        """Return the highest-priority active request without removing it."""
        if not self._heap:
            raise IndexError("peek from empty FairServiceQueue")
        return self._heap[0][-1].copy()

    def pop_next_request(self) -> dict[str, Any]:
        """Treat and remove the highest-priority active request."""
        next_request = self.peek_next_request()
        return self.mark_treated(next_request[self.case_id_column])

    def mark_treated(self, case_id: Any) -> dict[str, Any]:
        """Move a request from active to treated requests."""
        request = self._remove_active_request(case_id)
        self.treated_requests = self._append_request(self.treated_requests, request)
        self._rebuild_heap()
        return request.copy()

    def delete_request(self, case_id: Any) -> dict[str, Any]:
        """Move a request from active to deleted requests."""
        request = self._remove_active_request(case_id)
        self.deleted_requests = self._append_request(self.deleted_requests, request)
        self._rebuild_heap()
        return request.copy()

    def queue_dataframe(self) -> pd.DataFrame:
        """Return active requests in queue order with urgency scores."""
        return self._rank_active_requests()

    def _rebuild_heap(self) -> None:
        self._heap = []
        self._counter = count()

        ranked = self._rank_active_requests()
        for request in ranked.to_dict(orient="records"):
            heapq.heappush(self._heap, self._heap_entry(request))

    def _rank_active_requests(self) -> pd.DataFrame:
        if self.active_requests.empty:
            return self.active_requests.copy()

        try:
            return self.sorter.sort_by_urgency(self.active_requests)
        except ValueError as exc:
            if str(exc) == "No rows match the configured urgency ranking.":
                return self.active_requests.iloc[0:0].copy()
            raise

    def _heap_entry(self, request: dict[str, Any]) -> tuple[int, float, int, dict[str, Any]]:
        days_open = request["days_open"]
        days_open_priority = float("inf") if pd.isna(days_open) else -float(days_open)
        return (
            int(request["urgency_score"]),
            days_open_priority,
            next(self._counter),
            request,
        )

    def _remove_active_request(self, case_id: Any) -> dict[str, Any]:
        self._require_case_id_column(self.active_requests)
        matches = self.active_requests[self.case_id_column] == case_id
        match_count = int(matches.sum())

        if match_count == 0:
            raise KeyError(f"Active request not found: {case_id}")
        if match_count > 1:
            raise ValueError(f"Multiple active requests found for case id: {case_id}")

        request = self.active_requests.loc[matches].iloc[0].to_dict()
        self.active_requests = self.active_requests.loc[~matches].reset_index(drop=True)
        return request

    def _require_case_id(self, request: dict[str, Any]) -> None:
        if self.case_id_column not in request:
            raise KeyError(f"Missing required field: {self.case_id_column}")

    def _require_case_id_column(self, df: pd.DataFrame) -> None:
        if self.case_id_column not in df.columns:
            raise KeyError(f"Missing required column: {self.case_id_column}")

    @staticmethod
    def _append_request(df: pd.DataFrame, request: dict[str, Any]) -> pd.DataFrame:
        return pd.concat([df, pd.DataFrame([request])], ignore_index=True)
