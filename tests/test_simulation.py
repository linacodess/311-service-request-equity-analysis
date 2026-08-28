"""Tests for fair queue simulation state updates."""

from __future__ import annotations

import unittest

import pandas as pd

from service_request_equity.simulation import FairQueueSimulation


class TestFairQueueSimulation(unittest.TestCase):
    def setUp(self) -> None:
        self.active = pd.DataFrame(
            {
                "CaseID": [101, 102, 103],
                "Status": ["Open", "Open", "Open"],
                "Category": ["Needle Pickup", "Needle Pickup", "Parking Enforcement"],
                "Neighborhood": ["Dorchester", "Roxbury", "Dorchester"],
                "days_open": [8, 1, 5],
            }
        )

    def test_starts_from_initial_active_cases(self) -> None:
        simulation = FairQueueSimulation(self.active)

        self.assertEqual(simulation.summary()["active_cases"], 3)
        self.assertEqual(simulation.summary()["completed_cases"], 0)
        self.assertEqual(simulation.completed_case_ids, [])

    def test_complete_next_cases_moves_cases_out_of_active_queue(self) -> None:
        simulation = FairQueueSimulation(self.active)

        completed = simulation.complete_next_cases(count=1)

        self.assertEqual(completed.loc[0, "CaseID"], 101)
        self.assertEqual(simulation.completed_case_ids, [101])
        self.assertNotIn(101, simulation.active_cases()["CaseID"].tolist())
        self.assertEqual(simulation.simulated_completed_cases()["Status"].tolist(), ["Closed"])

    def test_delay_tracker_data_uses_remaining_active_cases(self) -> None:
        simulation = FairQueueSimulation(self.active)

        simulation.complete_next_cases(count=2)
        tracker_data = simulation.delay_tracker_data()

        self.assertEqual(len(tracker_data), 1)
        self.assertEqual(set(tracker_data["CaseID"]), {103})
        self.assertEqual(set(simulation.simulated_completed_cases()["CaseID"]), {101, 102})

    def test_reset_clears_simulated_completion_state(self) -> None:
        simulation = FairQueueSimulation(self.active)

        simulation.complete_next_cases(count=2)
        simulation.reset()

        self.assertEqual(simulation.completed_case_ids, [])
        self.assertEqual(simulation.summary()["active_cases"], 3)
        self.assertTrue(simulation.simulated_completed_cases().empty)

    def test_complete_next_cases_requires_positive_count(self) -> None:
        simulation = FairQueueSimulation(self.active)

        with self.assertRaises(ValueError):
            simulation.complete_next_cases(count=0)


if __name__ == "__main__":
    unittest.main()
