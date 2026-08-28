# 311 Service Request Equity Analysis

This project started as a CS2100 class project using 311 service request data. The first goal was to load the data, create visualizations, and build a priority queue for service requests based on:

- the type of service requested
- how many days the case had been open

The project also uses a map visualization to make the geographic distribution of cases easier to understand.

After finishing the coursework version, I continued improving the project because a priority queue can still reinforce unfair outcomes if it only looks at request type and days open. This improved version refactors the code and adds a fairer queue model that considers neighborhood-level delays.

## Main Question

The question behind this project is:

**How can 311 service requests be prioritized without repeatedly disadvantaging the same neighborhoods?**

At first, the queue focused on urgency and case duration. That helped show which cases should be handled first, but it also raised a fairness concern: if the system only looks at the request type and days open, some neighborhoods may still experience slower service over time.

## What The Project Does

- Loads and cleans 311 service request data with Pandas
- Sorts cases by service urgency and days open
- Builds a Fair Service Queue that accounts for neighborhood delay patterns
- Uses open cases from the last selected number of days for the active queue
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

The idea is:

```text
fair queue priority:
  1. service urgency
  2. neighborhood average delay boost
  3. days open
```

The boost should not replace urgency. A serious safety issue should still stay near the top. The goal is to help service operators avoid always prioritizing the same neighborhoods when other areas have also been waiting longer.

Over time, as delayed neighborhoods receive faster responses, their neighborhood average delay should decrease. When the gap becomes smaller, the boost becomes smaller too. Ideally, the queue gradually depends more on urgency and days open because neighborhood-level delays have become more balanced.

The project now separates this logic into three parts:

- `sorting.py`: ranks and sorts requests
- `fair_queue.py`: manages the live queue state
- `delay_tracker.py`: calculates neighborhood delay boosts

The Streamlit dashboard uses open cases only. Completed cases are removed from the active simulation queue so the neighborhood delay boosts can be recalculated from the cases still waiting.

## Why This Matters

311 data is not only a technical dataset. It reflects how residents ask for help and how city services respond. A queue that only looks at urgency may be efficient, but it may not be fair if some neighborhoods consistently wait longer.

This project explores how data analysis can be used not just to describe a problem, but also to design a system that supports fairer service distribution.

## How To Run It

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

By default, the app uses `data/raw/311_service_requests_2026.csv` when it exists. Otherwise, it falls back to `data/sample_311_cases.csv`.

## Run With A Larger Dataset

Large raw datasets are not committed to this repo. Put the 2026 CSV in `data/raw/`, then run:

```bash
streamlit run app.py
```

The project supports both the original class-project CSV format and the newer official Boston 311 export format.

The larger 311 CSV files and Boston neighborhood boundary GeoJSON can be downloaded from [Analyze Boston](https://data.boston.gov/), Boston's official open data portal.

## Dashboard Views

The Streamlit dashboard includes:

- **Simulation**: current queue metrics, the complete-next-cases button, and the strict queue preview
- **Neighborhood Impact**: before/after average days open by neighborhood and the current delay boost table
- **Map**: active queue cases plotted over Boston neighborhood boundaries

## Tests

```bash
pytest
```
