"""Tests for the live fair service queue."""

from __future__ import annotations

import unittest

import pandas as pd

from service_request_equity.delay_tracker import DelayTracker
from service_request_equity.fair_queue import FairServiceQueue


class TestFairServiceQueue(unittest.TestCase):
    def setUp(self) -> None:
        self.requests = pd.DataFrame(
            {
                "CaseID": [101, 102, 103],
                "Category": ["Parking Enforcement", "Needle Pickup", "Street Light Outages"],
                "Neighborhood": ["Roxbury", "Dorchester", "Jamaica Plain"],
                "days_open": [5, 1, 8],
            }
        )

    def test_peek_uses_urgency_then_days_open(self) -> None:
        queue = FairServiceQueue(self.requests)

        self.assertEqual(queue.peek_next_request()["CaseID"], 102)

        queue.add_request(
            {
                "CaseID": 104,
                "Category": "Needle Pickup",
                "Neighborhood": "Roxbury",
                "days_open": 4,
            }
        )

        self.assertEqual(queue.peek_next_request()["CaseID"], 104)

    def test_pop_next_request_moves_request_to_treated(self) -> None:
        queue = FairServiceQueue(self.requests)

        treated = queue.pop_next_request()

        self.assertEqual(treated["CaseID"], 102)
        self.assertNotIn(102, queue.active_requests["CaseID"].tolist())
        self.assertEqual(queue.treated_requests["CaseID"].tolist(), [102])
        self.assertEqual(queue.peek_next_request()["CaseID"], 103)

    def test_delete_request_removes_without_treating(self) -> None:
        queue = FairServiceQueue(self.requests)

        deleted = queue.delete_request(102)

        self.assertEqual(deleted["CaseID"], 102)
        self.assertNotIn(102, queue.active_requests["CaseID"].tolist())
        self.assertEqual(queue.deleted_requests["CaseID"].tolist(), [102])
        self.assertTrue(queue.treated_requests.empty)
        self.assertEqual(queue.peek_next_request()["CaseID"], 103)

    def test_unranked_categories_are_not_queued(self) -> None:
        queue = FairServiceQueue(
            pd.DataFrame(
                {
                    "CaseID": [201],
                    "Category": ["Noise Complaint"],
                    "Neighborhood": ["Roxbury"],
                    "days_open": [10],
                }
            )
        )

        self.assertEqual(len(queue), 0)
        self.assertTrue(queue.queue_dataframe().empty)

    def test_delay_tracker_boost_breaks_urgency_ties(self) -> None:
        tracker = DelayTracker()
        tracker.refresh(
            pd.DataFrame(
                {
                    "Neighborhood": ["Roxbury", "Dorchester"],
                    "days_open": [20, 1],
                }
            )
        )
        queue = FairServiceQueue(
            pd.DataFrame(
                {
                    "CaseID": [201, 202],
                    "Category": ["Needle Pickup", "Needle Pickup"],
                    "Neighborhood": ["Dorchester", "Roxbury"],
                    "days_open": [10, 1],
                }
            ),
            delay_tracker=tracker,
        )

        self.assertEqual(queue.peek_next_request()["CaseID"], 202)
        self.assertEqual(queue.queue_dataframe()["neighborhood_delay_boost"].tolist(), [9.5, 0.0])


if __name__ == "__main__":
    unittest.main()
