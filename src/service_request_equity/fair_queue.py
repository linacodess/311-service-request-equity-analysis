"""Live priority queue for fair 311 service request handling."""

from __future__ import annotations

import heapq
from itertools import count
from typing import Any

import pandas as pd

from service_request_equity.sorting import CaseSorter, DEFAULT_URGENCY_RANKING


class FairServiceQueue:
    """Heap-backed live queue for service requests."""

    def __init__(
        self,
        urgency_ranking: dict[str, int] | None = None,
        urgency_weight: float = 10.0,
        days_open_weight: float = 0.25,
        neighborhood_boost_weight: float = 1.0,
        max_neighborhood_boost: float = 5.0,
    ) -> None:
        CaseSorter._require_non_negative_weights(
            urgency_weight=urgency_weight,
            days_open_weight=days_open_weight,
            neighborhood_boost_weight=neighborhood_boost_weight,
            max_neighborhood_boost=max_neighborhood_boost,
        )
        self.urgency_ranking = urgency_ranking or DEFAULT_URGENCY_RANKING.copy()
        self.urgency_weight = urgency_weight
        self.days_open_weight = days_open_weight
        self.neighborhood_boost_weight = neighborhood_boost_weight
        self.max_neighborhood_boost = max_neighborhood_boost
        self.neighborhood_avg_days_open: dict[str, float] = {}
        self.citywide_avg_days_open: float | None = None
        self._heap: list[tuple[float, int, float, int, dict[str, Any]]] = []
        self._counter = count()

    def __len__(self) -> int:
        return len(self._heap)

    def load_historical_delays(self, df: pd.DataFrame) -> None:
        """Load neighborhood delay averages used for fairness boosts."""
        CaseSorter._require_columns(df, ["Neighborhood", "days_open"])
        CaseSorter._require_numeric_days_open(df)
        valid = df.dropna(subset=["Neighborhood", "days_open"])
        if valid.empty:
            raise ValueError("Historical delay data must contain at least one valid row.")

        self.citywide_avg_days_open = float(valid["days_open"].mean())
        self.neighborhood_avg_days_open = valid.groupby("Neighborhood")["days_open"].mean().to_dict()
        self._rebuild_heap()

    def update_neighborhood_delay(
        self,
        neighborhood: str,
        avg_days_open: float,
        citywide_avg_days_open: float | None = None,
    ) -> None:
        """Update delay statistics and refresh queued request priorities."""
        if avg_days_open < 0:
            raise ValueError("avg_days_open must be non-negative.")
        if citywide_avg_days_open is not None and citywide_avg_days_open < 0:
            raise ValueError("citywide_avg_days_open must be non-negative.")

        self.neighborhood_avg_days_open[neighborhood] = float(avg_days_open)
        if citywide_avg_days_open is not None:
            self.citywide_avg_days_open = float(citywide_avg_days_open)
        self._rebuild_heap()

    def add_request(self, request: dict[str, Any]) -> None:
        """Add one request to the live priority queue."""
        scored = self._score_request(request)
        heapq.heappush(self._heap, self._heap_entry(scored))

    def pop_next_request(self) -> dict[str, Any]:
        """Remove and return the highest-priority request."""
        if not self._heap:
            raise IndexError("pop from empty FairServiceQueue")
        return heapq.heappop(self._heap)[-1].copy()

    def peek_next_request(self) -> dict[str, Any]:
        """Return the highest-priority request without removing it."""
        if not self._heap:
            raise IndexError("peek from empty FairServiceQueue")
        return self._heap[0][-1].copy()

    def _score_request(self, request: dict[str, Any]) -> dict[str, Any]:
        missing = [column for column in ["Category", "Neighborhood", "days_open"] if column not in request]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required field(s): {missing_display}")

        category = request["Category"]
        if category not in self.urgency_ranking:
            raise ValueError(f"Category missing urgency ranking: {category}")

        days_open_value = pd.to_numeric(pd.Series([request["days_open"]]), errors="coerce").iloc[0]
        if pd.isna(days_open_value):
            raise ValueError("days_open must be numeric.")
        days_open = float(days_open_value)
        if days_open < 0:
            raise ValueError("days_open must be non-negative.")

        neighborhood = request["Neighborhood"]
        neighborhood_avg = self.neighborhood_avg_days_open.get(neighborhood)
        neighborhood_delay_boost = 0.0
        if neighborhood_avg is not None and self.citywide_avg_days_open is not None:
            delay_gap = max(neighborhood_avg - self.citywide_avg_days_open, 0)
            neighborhood_delay_boost = min(
                delay_gap * self.neighborhood_boost_weight,
                self.max_neighborhood_boost,
            )

        urgency_score = self.urgency_ranking[category]
        max_rank = max(self.urgency_ranking.values())
        fair_queue_score = (
            (max_rank - urgency_score + 1) * self.urgency_weight
            + days_open * self.days_open_weight
            + neighborhood_delay_boost
        )

        scored = request.copy()
        scored["urgency_score"] = urgency_score
        scored["neighborhood_avg_days_open"] = (
            round(neighborhood_avg, 2) if neighborhood_avg is not None else None
        )
        scored["neighborhood_delay_boost"] = round(neighborhood_delay_boost, 2)
        scored["fair_queue_score"] = round(fair_queue_score, 2)
        return scored

    def _heap_entry(
        self,
        request: dict[str, Any],
    ) -> tuple[float, int, float, int, dict[str, Any]]:
        return (
            -request["fair_queue_score"],
            request["urgency_score"],
            -float(request["days_open"]),
            next(self._counter),
            request,
        )

    def _rebuild_heap(self) -> None:
        requests = [entry[-1] for entry in self._heap]
        self._heap = []
        self._counter = count()
        for request in requests:
            scored = self._score_request(request)
            heapq.heappush(self._heap, self._heap_entry(scored))
