# NSW Solar & Battery Installation Tracker

Interactive dashboard tracking rooftop solar and battery installations across New South Wales, built from Clean Energy Regulator (CER) postcode-level data.

**[View Dashboard](https://bhanurekhab.github.io/nsw-solar-dashboard/NSWSolar_Dashboard.html)**

## What This Project Does

- Processes CER small-scale technology certificate data at postcode level
- Filters to NSW postcodes (2000–2999) and reshapes monthly installation columns into a clean long format
- Calculates yearly summaries with year-on-year growth percentages
- Identifies top postcodes by installation volume with suburb names
- Produces projected full-year figures for the current incomplete year
- Tracks battery uptake separately from solar

## Data Source

- **Solar installations:** [CER Small Generation Unit (SGU) data](https://www.cleanenergyregulator.gov.au) — 645 NSW postcodes with installations, from 2,811 national rows
- **Battery installations:** [CER Battery data](https://www.cleanenergyregulator.gov.au) — 628 NSW postcodes with installations, from 2,473 national rows

Solar data covers 2011–2026. Battery data covers July 2025 – August 2026. Downloaded October 2026.

## Dashboard Pages

The HTML dashboard has three pages:

1. **Overview** — total installations, current year activity, top postcodes, yearly summary table
2. **Growth Trends** — year-on-year growth rates, quarterly patterns, cumulative installation curves
3. **Battery Uptake** — battery installation volumes, growth trajectory, comparison with solar uptake

## Pipeline Outputs

| File | Description |
|------|-------------|
| `nsw_solar_monthly.csv` | 98,261 rows — one row per postcode per month (2011–2026) |
| `nsw_solar_yearly_summary.csv` | 16 rows — yearly totals with growth % and projections |
| `nsw_battery_monthly.csv` | 7,770 rows — battery installations by postcode and month |
| `nsw_battery_yearly_summary.csv` | Yearly battery totals with growth % |
| `nsw_solar_quarterly_summary.csv` | 63 rows — quarterly aggregations |
| `nsw_top_postcodes.csv` | Top 20 postcodes by total installations with suburb names |
| `nsw_dashboard_cards.csv` | Pre-calculated values for dashboard summary cards |
| `issues_log.txt` | Data quality notes from the cleaning process |

## How to Run

```bash
pip install -r requirements.txt
python nsw_solar_pipeline.py
```

Place the CER source CSVs in the `data/` folder. The pipeline reads them, filters to NSW, and writes all output files to `output/`.

## Key Findings

- NSW has recorded over **1.1 million rooftop solar installations** since 2011
- Growth peaked in 2020–2021 and has moderated but remains strong
- Projected 2026 battery installations (166,629) about 13% above projected 2025, based on 8 months of data — the federal Cheaper Home Batteries rebate from 1 July 2025 coincides with the start of the dataset
- Marsden Park/Box Hill (2765), Kellyville/Rouse Hill (2155) and Central Coast/Wyong (2259) are the top three postcodes by total installations

## Tools

- **Python** (Pandas) — ETL pipeline and data cleaning
- **HTML/CSS/JavaScript** — interactive dashboard
- **CER open data** — source datasets
