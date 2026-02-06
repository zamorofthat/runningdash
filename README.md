# Running Dashboard

A SQLite-backed Grafana dashboard for analyzing running performance data. Built for a conference talk on debugging your body using data.

> "Debug the most complex production system of all: your body"

## Overview

This dashboard answers the question: **Why did that run suck?**

- Was the "easy" run actually too hard?
- Did heat and humidity affect performance?
- Did the trail just suck?
- Was sleep the problem?

## Data Sources

| Source | Data | Key Fields |
|--------|------|------------|
| Strava | Running activities | pace, HR, distance, weather, elevation |
| Oura | Sleep/recovery | sleep score, HRV, readiness |

## Quick Start

### 1. Ingest Data

```bash
python3 ingest.py ~/Downloads/runningdata/
```

The script expects this folder structure:
```
runningdata/
├── export_*/activities.csv    # Strava export
└── oura_*_trends.csv          # Oura export
```

### 2. Configure Grafana

Install the SQLite datasource plugin:
```bash
grafana-cli plugins install frser-sqlite-datasource
```

Add a new SQLite datasource:
- **Name:** sqlite
- **UID:** sqlite
- **Path:** `/Users/azamora/Projects/runningdash/running_dashboard.db`

### 3. Import Dashboard

1. Go to **Dashboards > Import**
2. Upload `dashboard.json`
3. Select the SQLite datasource

## Database Schema

### Tables

```sql
runs (
  id INTEGER PRIMARY KEY,      -- Strava activity ID
  date DATE,
  name TEXT,
  distance_km REAL,
  duration_sec INTEGER,
  pace_min_km REAL,            -- Calculated: duration / distance
  avg_hr INTEGER,
  max_hr INTEGER,
  elevation_gain REAL,         -- meters
  temp_c REAL,                 -- Weather temperature
  humidity REAL,               -- Weather humidity %
  weather TEXT,                -- Weather condition
  relative_effort INTEGER,     -- Strava's effort score
  hour_of_day INTEGER,         -- 0-23
  day_of_week TEXT,            -- Monday, Tuesday, etc.
  calories INTEGER,            -- Strava calorie estimate
  gels_estimated INTEGER,      -- Estimated gels (1 per 3mi for 9+ mi runs)
  carbs_g INTEGER              -- Estimated carbs (gels * 30g)
)

sleep (
  date DATE PRIMARY KEY,
  sleep_score INTEGER,         -- Oura sleep score (0-100)
  readiness_score INTEGER,     -- Oura readiness score (0-100)
  hrv INTEGER,                 -- Heart rate variability (ms)
  resting_hr INTEGER,          -- Resting heart rate (bpm)
  deep_sleep_min INTEGER,
  rem_sleep_min INTEGER,
  total_sleep_min INTEGER
)
```

### Views

```sql
run_with_sleep
  -- Joins each run to the previous night's sleep data
  -- For morning runs (before noon), uses same-day sleep record
  -- For afternoon/evening runs, uses previous day's sleep record
```

## Dashboard Panels

### Row 0: Context Header
- Total Runs
- Total Miles
- Date Range
- Avg Weekly Miles
- Avg Pace

### Row 1: Was the Easy Run Actually Too Hard?
- **Effort vs Pace Scatter** - Dots above trendline = working harder than pace suggests
- **HR Drift Detection** - Relative effort and HR over time
- **Relative Effort Distribution** - Histogram showing effort levels (most should be easy)

### Row 2: Did the Weather Wreck Me?
- **Temperature vs Pace** - Expect ~5 sec/km slower per 5°C above 15°C
- **Temperature vs HR** - Same pace, higher HR in heat
- **Humidity vs Pace** - High humidity = slower
- **Weather Heatmap** - Temp × Humidity with pace as color

### Row 3: Did the Trail Just Suck?
- **Elevation Gain vs Pace** - More climbing = slower
- **Flat vs Hilly Comparison** - Quantify the "hill tax"

### Row 4: Was Sleep the Problem?
- **Sleep Score vs Pace** - Sleep <70 = degradation?
- **HRV vs Relative Effort** - Low HRV = same pace feels harder
- **Readiness Score vs Pace** - Trust the readiness score?
- **Deep Sleep vs Pace** - Deep sleep = better recovery?

### Row 5: The Big Picture
- **Training Load Timeline** - Weekly mileage vs avg sleep score
- **Monthly Pace Trend** - Getting faster or slower?
- **Best/Worst Runs Table** - Top 5 fastest and slowest with conditions

### Row 6: Did I Fuel Properly?
- **Long Runs Stats** - Count of 9+ mile runs, total gels, total carbs
- **Carb Replacement %** - Average percentage of calories replaced by gels
- **Carb Calories vs Total Burned** - Bar chart comparing intake to output by distance
- **Long Run Fueling Log** - Table of all long runs with fueling data
- **Gels vs Pace** - Does more fueling correlate with better paces?

*Fueling protocol: 1 gel (30g carbs) every 3 miles, starting at mile 3*

### Row 7: Putting It All Together
- **Optimal Conditions Matrix** - Sleep score × Temperature heatmap
- **Pace by Day of Week** - Never run hard on Monday?
- **Pace by Time of Day** - Morning vs afternoon runner?

## Re-ingestion

The ingest script uses upsert logic (INSERT OR REPLACE), so it's safe to re-run after exporting new data:

```bash
# Export fresh data from Strava and Oura
# Place in ~/Downloads/runningdata/
python3 ingest.py ~/Downloads/runningdata/
```

The dashboard auto-refreshes with new data.

## Exporting Data

### Strava
1. Go to Settings > My Account > Download or Delete Your Account
2. Request your archive
3. Extract the zip to `runningdata/export_*/`

### Oura
1. Go to the Oura web dashboard
2. Export > Trends
3. Save CSV to `runningdata/oura_*_trends.csv`

## Verification

Check data loaded correctly:

```bash
sqlite3 running_dashboard.db "SELECT COUNT(*) FROM runs; SELECT COUNT(*) FROM sleep;"
```

Test the sleep join:

```bash
sqlite3 running_dashboard.db "SELECT COUNT(*) FROM run_with_sleep WHERE sleep_score IS NOT NULL;"
```

## Requirements

- Python 3.10+
- Grafana 9.0+ with [SQLite datasource plugin](https://grafana.com/grafana/plugins/frser-sqlite-datasource/)
