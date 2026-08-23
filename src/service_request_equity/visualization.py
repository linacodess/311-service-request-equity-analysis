"""Matplotlib visualizations for the 311 service request analysis."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import pandas as pd


class Visualizer:
    """Create static visual artifacts for portfolio and README use."""

    NEIGHBORHOOD_BOUNDARIES_PATH = Path("data/raw/boston_neighborhood_boundaries.geojson")
    DELAY_COLORMAP = LinearSegmentedColormap.from_list(
        "delay_green_to_brown",
        ["#1a9850", "#fee08b", "#d73027", "#4d1f0c"],
    )

    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data.copy()

    def plot_case_map(self, save_path: str | Path) -> Path:
        """Save a longitude/latitude scatter plot of cases."""
        self._require_columns(["Longitude", "Latitude", "days_open"])
        output = self._prepare_output_path(save_path)
        coords = self.data.dropna(subset=["Longitude", "Latitude"])
        days_open = pd.to_numeric(coords["days_open"], errors="coerce")
        color_cap = self._percentile_cap(days_open, percentile=0.95)

        if coords.empty:
            raise ValueError("No valid coordinates available for map plot.")

        fig, ax = plt.subplots(figsize=(10, 7))
        self._plot_neighborhood_boundaries(ax)
        scatter = ax.scatter(
            coords["Longitude"],
            coords["Latitude"],
            c=days_open.clip(upper=color_cap),
            cmap=self.DELAY_COLORMAP,
            vmin=0,
            vmax=color_cap,
            s=8,
            alpha=0.28,
            edgecolors="none",
            zorder=2,
        )
        ax.set_title("311 Service Requests by Location")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal", adjustable="box")
        fig.colorbar(scatter, ax=ax, label=f"Days open (capped at {color_cap:g})")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def plot_neighborhood_delays(self, summary: pd.DataFrame, save_path: str | Path, top_n: int = 10) -> Path:
        """Save a bar chart of neighborhoods with the longest average delays."""
        self._require_summary_columns(summary, ["Neighborhood", "avg_days_open"])
        output = self._prepare_output_path(save_path)
        plot_data = summary.head(top_n).sort_values("avg_days_open")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(plot_data["Neighborhood"], plot_data["avg_days_open"], color="#2b6cb0")
        if "citywide_avg_days_open" in plot_data.columns and not plot_data.empty:
            citywide_avg = float(plot_data["citywide_avg_days_open"].iloc[0])
            ax.axvline(citywide_avg, color="#742a2a", linestyle="--", linewidth=1.5, label="Citywide average")
            ax.legend()
        ax.set_title("Neighborhoods With Longest Average Days Open")
        ax.set_xlabel("Average days open")
        ax.set_ylabel("Neighborhood")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def plot_category_durations(self, summary: pd.DataFrame, save_path: str | Path, top_n: int = 10) -> Path:
        """Save a bar chart of categories by average days open."""
        output = self._prepare_output_path(save_path)
        plot_data = summary.head(top_n).sort_values("avg_days_open")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(plot_data["Category"], plot_data["avg_days_open"], color="#b7791f")
        ax.invert_yaxis()
        ax.set_title("311 Categories by Average Days Open")
        ax.set_xlabel("Average days open")
        ax.set_ylabel("Category")
        fig.tight_layout()
        fig.savefig(output, dpi=180)
        plt.close(fig)
        return output

    def create_fair_queue_preview_html(
        self,
        queue_df: pd.DataFrame,
        save_path: str | Path,
        top_n: int = 25,
    ) -> Path:
        """Save an interactive HTML preview of the first cases in queue order."""
        self._require_summary_columns(
            queue_df,
            ["CaseID", "Status", "Category", "Neighborhood", "urgency_score", "neighborhood_delay_boost", "days_open"],
        )
        output = self._prepare_output_path(save_path)
        ranked = queue_df.copy().reset_index(drop=True)
        ranked.insert(0, "queue_rank", range(1, len(ranked) + 1))

        strict_preview = ranked.head(top_n)
        diverse_preview = self._diverse_queue_preview(ranked, top_n)

        strict_queue_json = self._queue_preview_json(strict_preview)
        diverse_queue_json = self._queue_preview_json(diverse_preview)
        output.write_text(
            self._fair_queue_html(strict_queue_json, diverse_queue_json, len(strict_preview), len(diverse_preview)),
            encoding="utf-8",
        )
        return output

    @staticmethod
    def _diverse_queue_preview(queue_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
        candidate_df = queue_df.dropna(subset=["days_open"])
        if not candidate_df.empty:
            queue_df = candidate_df

        selected_indices: list[int] = []
        seen_categories: set[str] = set()
        seen_neighborhoods: set[str] = set()

        def add_row(index: int) -> None:
            selected_indices.append(index)
            row = queue_df.loc[index]
            seen_categories.add(str(row["Category"]))
            seen_neighborhoods.add(str(row["Neighborhood"]))

        for index, row in queue_df.iterrows():
            category = str(row["Category"])
            if category not in seen_categories:
                add_row(index)
            if len(selected_indices) == top_n:
                break

        if len(selected_indices) < top_n:
            for index, row in queue_df.iterrows():
                neighborhood = str(row["Neighborhood"])
                if index not in selected_indices and neighborhood not in seen_neighborhoods:
                    add_row(index)
                if len(selected_indices) == top_n:
                    break

        if len(selected_indices) < top_n:
            for index in queue_df.index:
                if index not in selected_indices:
                    add_row(index)
                if len(selected_indices) == top_n:
                    break

        return queue_df.loc[selected_indices].sort_values("queue_rank").copy().reset_index(drop=True)

    @staticmethod
    def _queue_preview_json(queue_df: pd.DataFrame) -> str:
        rows = queue_df[
            [
                "queue_rank",
                "CaseID",
                "Status",
                "Category",
                "Neighborhood",
                "urgency_score",
                "neighborhood_delay_boost",
                "days_open",
            ]
        ]
        rows = rows.astype(object).where(pd.notna(rows), None)
        return json.dumps(rows.to_dict(orient="records"), indent=2, allow_nan=False)

    def _require_columns(self, columns: list[str]) -> None:
        missing = [column for column in columns if column not in self.data.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _require_summary_columns(df: pd.DataFrame, columns: list[str]) -> None:
        missing = [column for column in columns if column not in df.columns]
        if missing:
            missing_display = ", ".join(missing)
            raise KeyError(f"Missing required column(s): {missing_display}")

    @staticmethod
    def _prepare_output_path(save_path: str | Path) -> Path:
        output = Path(save_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    @staticmethod
    def _percentile_cap(series: pd.Series, percentile: float) -> float:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if numeric.empty:
            return 1.0
        cap = float(numeric.quantile(percentile))
        return max(cap, 1.0)

    @classmethod
    def _plot_neighborhood_boundaries(cls, ax: plt.Axes) -> None:
        if not cls.NEIGHBORHOOD_BOUNDARIES_PATH.exists():
            return

        boundaries = json.loads(cls.NEIGHBORHOOD_BOUNDARIES_PATH.read_text(encoding="utf-8"))
        for feature in boundaries.get("features", []):
            geometry = feature.get("geometry") or {}
            for ring in cls._geometry_rings(geometry):
                if not ring:
                    continue
                longitudes = [point[0] for point in ring]
                latitudes = [point[1] for point in ring]
                ax.fill(
                    longitudes,
                    latitudes,
                    facecolor="#fffaf6",
                    edgecolor="#96add6",
                    linewidth=0.7,
                    alpha=0.58,
                    zorder=0,
                )

    @staticmethod
    def _geometry_rings(geometry: dict) -> list[list[list[float]]]:
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        if geometry_type == "Polygon":
            return coordinates
        if geometry_type == "MultiPolygon":
            return [ring for polygon in coordinates for ring in polygon]
        return []

    @staticmethod
    def _fair_queue_html(strict_queue_json: str, diverse_queue_json: str, strict_count: int, diverse_count: int) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fair Service Queue Preview</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: "Intuitive UX", Inter, Aptos, "Helvetica Neue", Arial, sans-serif;
      --dark-blue: #00408c;
      --blue: #96add6;
      --red: #e85234;
      --peach: #f9b8af;
      --cream: #f2eee9;
      --pink: #f2d7d3;
      --ink: #16324f;
      --muted: #536b8a;
      --label: #3f5f88;
      --line: #d9e2ef;
      --surface: #fffaf6;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--cream);
    }}
    main {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 28px;
    }}
    h1 {{
      margin: 0 0 8px;
      color: var(--dark-blue);
      font-size: 30px;
    }}
    .summary {{
      margin: 0 0 22px;
      color: var(--muted);
      line-height: 1.45;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(240px, 280px);
      gap: 18px;
      align-items: start;
    }}
    .layout > section {{
      min-width: 0;
    }}
    .controls {{
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(160px, 220px) minmax(160px, 220px);
      gap: 10px;
      margin-bottom: 14px;
    }}
    .view-toggle {{
      display: inline-flex;
      gap: 4px;
      padding: 4px;
      margin-bottom: 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 250, 246, 0.72);
    }}
    .view-toggle button {{
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--label);
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      padding: 8px 14px;
    }}
    .view-toggle button.active {{
      background: var(--dark-blue);
      color: #ffffff;
    }}
    .view-note {{
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }}
    input, select {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--ink);
      font: inherit;
      padding: 10px 12px;
    }}
    input:focus, select:focus {{
      border-color: rgba(232, 82, 52, 0.55);
      box-shadow: 0 0 0 3px rgba(249, 184, 175, 0.42);
      outline: none;
    }}
    .view-toggle button:focus {{
      box-shadow: 0 0 0 3px rgba(249, 184, 175, 0.42);
      outline: none;
    }}
    .queue-list {{
      display: grid;
      gap: 10px;
    }}
    .queue-row {{
      display: grid;
      grid-template-columns: 42px minmax(78px, 0.7fr) minmax(145px, 1.35fr) minmax(120px, 1fr) minmax(58px, 0.45fr) minmax(96px, 0.7fr) minmax(64px, 0.45fr);
      gap: 10px;
      align-items: center;
      border: 1px solid rgba(0, 64, 140, 0.14);
      border-left: 5px solid var(--blue);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: 0 8px 22px rgba(0, 64, 140, 0.06);
      padding: 12px 12px 12px 10px;
      transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }}
    .queue-row:hover {{
      border-color: rgba(232, 82, 52, 0.32);
      box-shadow: 0 10px 28px rgba(232, 82, 52, 0.10);
      transform: translateY(-1px);
    }}
    .queue-row:first-child {{
      border-left-color: var(--red);
      background: linear-gradient(90deg, rgba(249, 184, 175, 0.28), var(--surface) 34%);
    }}
    .queue-row:first-child .rank {{
      background: var(--red);
    }}
    .queue-row.is-hidden {{
      display: none;
    }}
    .label {{
      display: block;
      margin-bottom: 3px;
      color: var(--label);
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }}
    .value {{
      display: block;
      min-width: 0;
      overflow-wrap: anywhere;
      font-size: 14px;
      font-weight: 700;
    }}
    .rank {{
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: var(--dark-blue);
      color: #ffffff;
      font-weight: 800;
    }}
    .score {{
      display: inline-grid;
      min-width: 32px;
      height: 30px;
      place-items: center;
      border-radius: 999px;
      background: rgba(150, 173, 214, 0.35);
      color: var(--dark-blue);
      font-weight: 800;
    }}
    .metric {{
      display: grid;
      gap: 5px;
    }}
    .bar {{
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(150, 173, 214, 0.25);
    }}
    .bar span {{
      display: block;
      height: 100%;
      width: var(--bar-width);
      border-radius: inherit;
      background: var(--dark-blue);
    }}
    .empty-state {{
      display: none;
      border: 1px dashed var(--blue);
      border-radius: 8px;
      background: rgba(255, 250, 246, 0.74);
      padding: 22px;
      color: var(--muted);
      text-align: center;
    }}
    .empty-state.is-visible {{
      display: block;
    }}
    aside {{
      border: 1px solid rgba(0, 64, 140, 0.14);
      border-top: 5px solid var(--red);
      border-radius: 8px;
      background: rgba(255, 250, 246, 0.82);
      padding: 18px;
      position: sticky;
      top: 18px;
      box-shadow: 0 8px 22px rgba(0, 64, 140, 0.06);
    }}
    aside h2 {{
      margin: 0 0 12px;
      color: var(--dark-blue);
      font-size: 18px;
    }}
    .rule {{
      border-top: 1px solid var(--line);
      padding: 12px 0;
    }}
    .rule:first-of-type {{
      border-top: 0;
    }}
    .rule strong {{
      display: block;
      margin-bottom: 4px;
      color: var(--dark-blue);
    }}
    .rule span {{
      color: var(--muted);
      line-height: 1.45;
    }}
    @media (max-width: 900px) {{
      main {{
        padding: 18px;
      }}
      .layout {{
        grid-template-columns: 1fr;
      }}
      .controls {{
        grid-template-columns: 1fr;
      }}
      .view-toggle {{
        display: flex;
      }}
      .view-toggle button {{
        flex: 1;
      }}
      .queue-row {{
        grid-template-columns: 42px 1fr;
      }}
      .queue-row > div:not(.rank) {{
        grid-column: 2;
      }}
      aside {{
        position: static;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Fair Service Queue Preview</h1>
    <p class="summary">
      Compare the exact queue order with a more diverse preview that makes the fairness logic easier to read.
    </p>
    <div class="layout">
      <section>
        <div class="view-toggle" aria-label="Queue view">
          <button type="button" class="active" data-view="diverse">Diverse preview</button>
          <button type="button" data-view="strict">Strict queue</button>
        </div>
        <p id="view-note" class="view-note"></p>
        <div class="controls" aria-label="Queue filters">
          <input id="case-search" type="search" placeholder="Search case ID">
          <select id="category-filter" aria-label="Filter by category"></select>
          <select id="neighborhood-filter" aria-label="Filter by neighborhood"></select>
        </div>
        <div id="queue-list" class="queue-list" aria-label="Fair service queue preview"></div>
        <div id="empty-state" class="empty-state">No cases match these filters.</div>
      </section>
      <aside>
        <h2>Queue Rules</h2>
        <div class="rule">
          <strong>1. Urgency score</strong>
          <span>Lower numbers move first.</span>
        </div>
        <div class="rule">
          <strong>2. Delay boost</strong>
          <span>If urgency is tied, neighborhoods with longer average delays move up.</span>
        </div>
        <div class="rule">
          <strong>3. Days open</strong>
          <span>If both are tied, the case open longer moves first.</span>
        </div>
        <div class="rule">
          <strong>Preview modes</strong>
          <span>Strict queue shows the true next cases. Diverse preview samples more categories and neighborhoods, then keeps them in queue-rank order.</span>
        </div>
      </aside>
    </div>
  </main>
  <script>
    const strictQueueRows = {strict_queue_json};
    const diverseQueueRows = {diverse_queue_json};
    const viewNotes = {{
      diverse: "Showing {diverse_count} ranked cases chosen to include more categories and neighborhoods, still ordered by queue rank.",
      strict: "Showing the first {strict_count} cases in exact queue order."
    }};
    let currentView = "diverse";
    let queueRows = diverseQueueRows;
    const queueList = document.querySelector("#queue-list");
    const emptyState = document.querySelector("#empty-state");
    const caseSearch = document.querySelector("#case-search");
    const categoryFilter = document.querySelector("#category-filter");
    const neighborhoodFilter = document.querySelector("#neighborhood-filter");
    const viewNote = document.querySelector("#view-note");

    function formatNumber(value) {{
      if (value === null || value === undefined || Number.isNaN(value)) {{
        return "n/a";
      }}
      return Number(value).toLocaleString(undefined, {{ maximumFractionDigits: 2 }});
    }}

    function safeText(value) {{
      if (value === null || value === undefined) {{
        return "n/a";
      }}
      return String(value).replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[char]));
    }}

    function uniqueValues(key) {{
      return [...new Set(queueRows.map((row) => row[key]).filter(Boolean))].sort();
    }}

    function fillSelect(select, label, values) {{
      select.innerHTML = `<option value="">${{label}}</option>`;
      values.forEach((value) => {{
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }});
    }}

    function barWidth(value) {{
      const numeric = Number(value) || 0;
      const maxDelayBoost = Math.max(...queueRows.map((row) => Number(row.neighborhood_delay_boost) || 0), 1);
      return `${{Math.max((numeric / maxDelayBoost) * 100, numeric > 0 ? 8 : 0)}}%`;
    }}

    function createRow(row) {{
      const item = document.createElement("article");
      item.className = "queue-row";
      item.dataset.caseId = String(row.CaseID).toLowerCase();
      item.dataset.category = row.Category || "";
      item.dataset.neighborhood = row.Neighborhood || "";
      item.innerHTML = `
        <div class="rank">${{row.queue_rank}}</div>
        <div>
          <span class="label">Case ID</span>
          <span class="value">${{safeText(row.CaseID)}}</span>
        </div>
        <div>
          <span class="label">Category</span>
          <span class="value">${{safeText(row.Category)}}</span>
        </div>
        <div>
          <span class="label">Neighborhood</span>
          <span class="value">${{safeText(row.Neighborhood)}}</span>
        </div>
        <div>
          <span class="label">Urgency</span>
          <span class="score">${{row.urgency_score}}</span>
        </div>
        <div class="metric">
          <span class="label">Delay Boost</span>
          <span class="value">${{formatNumber(row.neighborhood_delay_boost)}}</span>
          <span class="bar" aria-hidden="true"><span style="--bar-width: ${{barWidth(row.neighborhood_delay_boost)}}"></span></span>
        </div>
        <div>
          <span class="label">Days Open</span>
          <span class="value">${{formatNumber(row.days_open)}}</span>
        </div>
      `;
      queueList.appendChild(item);
    }}

    function renderQueue() {{
      queueList.innerHTML = "";
      caseSearch.value = "";
      fillSelect(categoryFilter, "All categories", uniqueValues("Category"));
      fillSelect(neighborhoodFilter, "All neighborhoods", uniqueValues("Neighborhood"));
      viewNote.textContent = viewNotes[currentView];
      queueRows.forEach(createRow);
      applyFilters();
    }}

    function setView(view) {{
      currentView = view;
      queueRows = view === "strict" ? strictQueueRows : diverseQueueRows;
      document.querySelectorAll(".view-toggle button").forEach((button) => {{
        button.classList.toggle("active", button.dataset.view === view);
      }});
      renderQueue();
    }}

    function applyFilters() {{
      const query = caseSearch.value.trim().toLowerCase();
      const category = categoryFilter.value;
      const neighborhood = neighborhoodFilter.value;
      let visible = 0;

      document.querySelectorAll(".queue-row").forEach((row) => {{
        const matchesSearch = !query || row.dataset.caseId.includes(query);
        const matchesCategory = !category || row.dataset.category === category;
        const matchesNeighborhood = !neighborhood || row.dataset.neighborhood === neighborhood;
        const shouldShow = matchesSearch && matchesCategory && matchesNeighborhood;
        row.classList.toggle("is-hidden", !shouldShow);
        if (shouldShow) {{
          visible += 1;
        }}
      }});
      emptyState.classList.toggle("is-visible", visible === 0);
    }}

    document.querySelectorAll(".view-toggle button").forEach((button) => {{
      button.addEventListener("click", () => setView(button.dataset.view));
    }});
    [caseSearch, categoryFilter, neighborhoodFilter].forEach((control) => {{
      control.addEventListener("input", applyFilters);
    }});
    renderQueue();
  </script>
</body>
</html>
"""
