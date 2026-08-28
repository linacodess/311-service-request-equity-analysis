"""Tests for Streamlit map helper functions."""

from __future__ import annotations

import unittest

from service_request_equity.map_visualization import geometry_rings


class TestMapVisualization(unittest.TestCase):
    def test_geometry_rings_supports_polygon(self) -> None:
        polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        }

        self.assertEqual(geometry_rings(polygon), polygon["coordinates"])

    def test_geometry_rings_supports_multipolygon(self) -> None:
        multipolygon = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                [[[2, 2], [3, 2], [3, 3], [2, 2]]],
            ],
        }

        self.assertEqual(
            geometry_rings(multipolygon),
            [
                [[0, 0], [1, 0], [1, 1], [0, 0]],
                [[2, 2], [3, 2], [3, 3], [2, 2]],
            ],
        )

    def test_geometry_rings_ignores_unsupported_geometry(self) -> None:
        self.assertEqual(geometry_rings({"type": "Point", "coordinates": [0, 0]}), [])


if __name__ == "__main__":
    unittest.main()
