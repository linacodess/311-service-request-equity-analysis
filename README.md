# 311 Service Request Equity Analysis

This tool prioritizes city service requests while helping prevent the same neighborhoods from repeatedly waiting longer.

In many U.S. cities, 311 is the non-emergency service residents use to report problems such as broken streetlights, missed trash, graffiti, and unsafe property conditions.

This project started as a CS2100 class project using 311 service request data. The first goal was to load the data, create visualizations, and build a priority queue for service requests based on:

- the type of service requested
- how many days the case had been open

The project also uses a map visualization to make the geographic distribution of cases easier to understand.

After finishing the coursework version, I continued improving the project because a priority queue can still reinforce unfair outcomes if it only looks at request type and days open. This improved version refactors the code and adds a fairer queue model that considers neighborhood-level delays.

## Demo

A video or screenshot of the dashboard will be added here.

## Table of Contents

- [Main Question](#main-question)
- [What The Project Does](#what-the-project-does)
- [Initial Priority Ranking](#initial-priority-ranking)
- [Fair Service Queue](#fair-service-queue)
- [How To Run It](#how-to-run-it)
- [Updating The Application Data](#updating-the-application-data)
- [Dashboard Views](#dashboard-views)
- [Project Structure](#project-structure)
- [Tests](#tests)

## Main Question

The question behind this project is:

**How can 311 service requests be prioritized without repeatedly disadvantaging the same neighborhoods?**

At first, the queue focused on urgency and case duration. That helped show which cases should be handled first, but it also raised a fairness concern: if the system only looks at the request type and days open, some neighborhoods may still experience slower service over time.

## What The Project Does

- Loads and cleans 311 service request data with Pandas
- Sorts cases by service urgency and days open
- Builds a Fair Service Queue that accounts for neighborhood delay patterns
- Uses a prepared 2026 dataset of open cases from the 10 ranked categories, capped at 110 days open
- Simulates completing batches of queue cases
- Tracks neighborhood delay boosts separately with a `DelayTracker`
- Shows neighborhood delay changes before and after the simulation
- Maps active queue cases with Boston neighborhood boundaries

## Initial Priority Ranking

The first priority queue used a manual ranking system for service categories. My ranking focused first on public safety and quick intervention, then on health, community impact, and longer-term infrastructure concerns.

| Rank | Service Category | Reasoning |
|---:|---|---|
| 1 | Needle Pickup | A public health and safety issue that can directly harm residents. |
| 2 | Street Light Outages | Dark streets can increase the risk of accidents or unsafe conditions. |
| 3 | Parking Enforcement | Can affect traffic flow and safety, and the city can usually respond quickly. |
| 4 | Sign Repair | Important for circulation, navigation, and accident prevention. |
| 5 | Bed Bugs | A health and housing issue that can spread if not handled quickly. |
| 6 | Poor Conditions of Property | Important for housing quality and neighborhood well-being. |
| 7 | Missed Trash / Recycling / Yard Waste / Bulk Item | Can affect public health, cleanliness, pests, and neighborhood quality of life. |
| 8 | Requests for Street Cleaning | Helps maintain clean public spaces, especially after events or storms. |
| 9 | Graffiti Removal | Can affect neighborhood appearance and local business perception, but is usually less urgent for safety. |
| 10 | Abandoned Bicycle | Usually lower safety impact, but affects public space and accessibility. |

This ranking is not perfect. It reflects the criteria I chose at the time: immediate safety, health impact, ease of response, and community impact. One limitation is that a category-based ranking can miss neighborhood-level service patterns.

## Fair Service Queue

The main improvement after the coursework version is a **Fair Service Queue**.

Instead of only sorting by service type and days open, the queue also considers each neighborhood's average delay. If a neighborhood has been waiting longer than the citywide average, cases from that neighborhood receive a temporary boost in the queue.

This delay boost is a temporary priority advantage. It helps cases from neighborhoods with longer average waits move ahead of similar cases, without replacing the urgency ranking.

The idea is:

```text
fair queue priority:
  1. service urgency
  2. neighborhood average delay boost
  3. days open
```

The boost should not replace urgency. A serious safety issue should still stay near the top. The goal is to help service operators avoid always prioritizing the same neighborhoods when other areas have also been waiting longer.

Over time, as delayed neighborhoods receive faster responses, their neighborhood average delay should decrease. When the gap becomes smaller, the boost becomes smaller too. Ideally, the queue gradually depends more on urgency and days open because neighborhood-level delays have become more balanced.

The project now separates this logic into four parts:

- `sorting.py`: ranks and sorts requests
- `delay_tracker.py`: calculates neighborhood delay boosts
- `fair_queue.py`: builds and manages the ranked queue
- `simulation.py`: tracks active and completed cases as the simulation changes

The Streamlit dashboard uses open cases only. Completed cases are removed from the active simulation queue so the neighborhood delay boosts can be recalculated from the cases still waiting.

## Why This Matters

311 data is not only a technical dataset. It reflects how residents ask for help and how city services respond. A queue that only looks at urgency may be efficient, but it may not be fair if some neighborhoods consistently wait longer.

This project explores how data analysis can be used not just to describe a problem, but also to design a system that supports fairer service distribution.

## How To Run It

The project requires Python 3.10 or newer.

Install the project and start the dashboard:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
streamlit run app.py
```

By default, the app uses `data/app_queue_cases_110_days.csv`. This prepared 2026 dataset contains open, queue-eligible cases capped at 110 days open so stale records do not dominate the simulation. If the prepared file is not available, the app falls back to `data/sample_311_cases.csv`.

## Updating The Application Data

The prepared CSV is included, so this step is optional. It is only needed when updating the dashboard with newer Boston data.

Download the latest CSV from the official [Boston 311 Service Requests dataset](https://data.boston.gov/dataset/311-service-requests), save it in `data/raw/`, and run:

```bash
python scripts/prepare_app_data.py data/raw/311_service_requests_2026.csv
```

The script uses the existing data loader to clean the file, keeps open cases from the 10 ranked categories, calculates how many days they have been open, applies the 110-day limit, and updates `data/app_queue_cases_110_days.csv`.

The loader accepts the project's original column names and the newer Boston export names. A CSV needs values for case ID, status, category, neighborhood, latitude, and longitude. It also needs either `days_open` or date fields that can be used to calculate it.

The map can use the official [Boston Neighborhood Boundaries dataset](https://data.boston.gov/dataset/bpda-neighborhood-boundaries). GeoJSON is a file format for geographic boundaries. Save that file as `data/raw/boston_neighborhood_boundaries.geojson`.

## Dashboard Views

The Streamlit dashboard includes:

- **Overview**: the project explanation, neighborhoods represented, queue cases loaded, categories represented, and the prepared day cap
- **Queue**: current queue metrics, a category filter, case cards, and the Complete cases button, which processes up to 5,000 cases at a time
- **Impact**: before-and-after average days open for the 12 neighborhoods with the highest current delay boosts
- **Map**: active queue cases plotted over Boston neighborhood boundaries

## Built With

- Python
- Pandas for loading, cleaning, and analyzing data
- Streamlit for the dashboard
- Matplotlib for charts and maps
- Pytest for automated tests

## Project Structure

```text
app.py                              Streamlit dashboard
scripts/prepare_app_data.py         Optional data refresh tool
src/service_request_equity/
  data_loader.py                    Loads and cleans 311 data
  sorting.py                        Applies the priority ranking
  delay_tracker.py                  Calculates neighborhood delay boosts
  fair_queue.py                     Builds the ranked queue
  simulation.py                     Tracks the changing simulation
  map_visualization.py              Draws neighborhood boundaries
data/
  app_queue_cases_110_days.csv      Prepared dashboard data
  sample_311_cases.csv              Small fallback dataset
tests/                              Automated tests
```

## Tests

Install the development tools:

```bash
pip install -e ".[dev]"
```

Then run:

```bash
pytest
```

The tests cover data loading, sorting, delay boosts, queue behavior, simulations, map boundaries, and preparation of the dashboard data.

## Author

[Lina Boutayeb](https://github.com/linacodess)

## Acknowledgments

The initial requirements, file structure, and testing scaffolds were provided through Northeastern University's CS2100 course. I developed the project implementations, priority ranking, fair queue, simulation, data updates, and Streamlit dashboard as part of this project and its continued development.
