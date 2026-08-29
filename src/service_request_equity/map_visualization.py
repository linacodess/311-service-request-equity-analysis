"""Map helpers for the Streamlit dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

NEIGHBORHOOD_BOUNDARIES_PATH = Path("data/raw/boston_neighborhood_boundaries.geojson")


def plot_neighborhood_boundaries(
    ax: plt.Axes,
    boundaries_path: str | Path = NEIGHBORHOOD_BOUNDARIES_PATH,
) -> None:
    """Draw Boston neighborhood boundaries onto a Matplotlib axis."""
    path = Path(boundaries_path)
    if not path.exists():
        return

    boundaries = json.loads(path.read_text(encoding="utf-8"))
    for feature in boundaries.get("features", []):
        geometry = feature.get("geometry") or {}
        for ring in geometry_rings(geometry):
            if not ring:
                continue
            longitudes = [point[0] for point in ring]
            latitudes = [point[1] for point in ring]
            ax.fill(
                longitudes,
                latitudes,
                facecolor="#f7f3ef",
                edgecolor="#95cde8",
                linewidth=0.7,
                alpha=0.58,
                zorder=0,
            )


def geometry_rings(geometry: dict) -> list[list[list[float]]]:
    """Return drawable coordinate rings from a GeoJSON geometry."""
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Polygon":
        return coordinates
    if geometry_type == "MultiPolygon":
        return [ring for polygon in coordinates for ring in polygon]
    return []
