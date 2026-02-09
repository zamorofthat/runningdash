# Grafana Local Setup Guide

## Prerequisites
- Docker Desktop installed and running

## Step 1: Start Grafana Container

```bash
# Remove any existing grafana container (safe to run even if none exists)
docker rm -f grafana 2>/dev/null

# Start Grafana with SQLite plugin pre-installed
docker run -d --name grafana -p 3000:3000 \
  -v /Users/azamora/Projects/runningdash:/var/lib/grafana/data \
  -e "GF_INSTALL_PLUGINS=frser-sqlite-datasource" \
  grafana/grafana:latest
```

## Step 2: Verify Container is Running

```bash
docker ps | grep grafana
```

You should see something like:
```
abc123  grafana/grafana:latest  ...  Up X seconds  0.0.0.0:3000->3000/tcp  grafana
```

If it's not running, check logs:
```bash
docker logs grafana
```

## Step 3: Access Grafana

1. Open http://localhost:3000
2. Login with:
   - **Username:** `admin`
   - **Password:** `admin`
3. You'll be prompted to change the password (you can skip)

## Step 4: Configure SQLite Data Source

1. Click the hamburger menu (☰) → **Connections** → **Data sources**
2. Click **Add data source**
3. Search for **SQLite** and select it
4. Configure:
   - **Name:** `sqlite`
   - **Path:** `/var/lib/grafana/data/running_dashboard.db`
5. Click **Save & test**
6. You should see "Data source is working"

**Important:** The UID must be `sqlite` (check under "Settings" section). The dashboard references this UID.

## Step 5: Import Dashboard

1. Click hamburger menu (☰) → **Dashboards**
2. Click **New** → **Import**
3. Click **Upload dashboard JSON file**
4. Select `/Users/azamora/Projects/runningdash/dashboard.json`
   - Or drag and drop the file
5. Select the **sqlite** data source when prompted
6. Click **Import**

## Step 6: Verify Data

The dashboard should load with all panels populated. Check:
- **Total Runs:** 339
- **Total Miles:** ~1,448
- **Runs with Garmin Data:** 200 (Row 8)

## Troubleshooting

### Container won't start
```bash
# Check if port 3000 is in use
lsof -i :3000

# Try a different port
docker run -d --name grafana -p 3001:3000 \
  -v /Users/azamora/Projects/runningdash:/var/lib/grafana/data \
  -e "GF_INSTALL_PLUGINS=frser-sqlite-datasource" \
  grafana/grafana:latest
# Then access http://localhost:3001
```

### SQLite plugin not found
```bash
# Restart container to trigger plugin install
docker restart grafana
# Wait 30 seconds, then try again
```

### Database not found
Verify the database exists:
```bash
ls -la /Users/azamora/Projects/runningdash/running_dashboard.db
```

Verify it has data:
```bash
sqlite3 /Users/azamora/Projects/runningdash/running_dashboard.db "SELECT COUNT(*) FROM runs;"
# Should return: 339
```

### Panels show "No data"
1. Check data source is configured correctly
2. Verify the data source UID is exactly `sqlite` (lowercase)
3. Try clicking the panel title → Edit → Run query

## Stopping Grafana

```bash
docker stop grafana
```

## Restarting Grafana (after computer restart)

```bash
docker start grafana
```

Or if the container was removed:
```bash
docker run -d --name grafana -p 3000:3000 \
  -v /Users/azamora/Projects/runningdash:/var/lib/grafana/data \
  -e "GF_INSTALL_PLUGINS=frser-sqlite-datasource" \
  grafana/grafana:latest
```

## File Locations

| File | Purpose |
|------|---------|
| `running_dashboard.db` | SQLite database with all run/sleep/Garmin data |
| `dashboard.json` | Grafana dashboard definition (42 panels, 8 rows) |
| `ingest.py` | Script to re-import data from exports |
| `export.py` | Script to export data to CSV/JSON/S3/Cribl |

---

## Dashboard Modifications (2026-02-08)

### Time Range Filtering

All queries now respond to Grafana's time picker. SQLite date filtering format:
```sql
WHERE date >= date($__from/1000, 'unixepoch') AND date <= date($__to/1000, 'unixepoch')
```

### Time Picker Quick Ranges

Added custom quick ranges:
- Individual years: 2023, 2024, 2025, 2026
- Relative: Last 6 months, Last 1 year, All time
- Default: Last 5 years

### Removed Panels

- **Date Range** stat panel (redundant with time picker)

### Panel Type Conversions

The SQLite plugin has compatibility issues with Grafana's timeseries and heatmap visualizations. These panels were converted:

**Timeseries → Bar Chart:**
| Panel | Reason |
|-------|--------|
| Training Load vs Sleep → Weekly Mileage | Weekly aggregates display better as bars |
| Monthly Pace Trend | Monthly aggregates display better as bars |

**Timeseries → Scatter Plot (XY Chart):**
| Panel | Reason |
|-------|--------|
| HR Drift Detection → Relative Effort Over Time | "Data outside time range" error |
| Training Effect Trend → Aerobic Training Effect | "Data outside time range" error |
| VO2max Trend | "Data outside time range" error |

**Heatmap → Scatter Plot (XY Chart):**
| Panel | Reason |
|-------|--------|
| Weather Heatmap (Temp x Humidity) → Weather: Temp vs Humidity | "no heatmap fields found" error |
| Optimal Conditions (Temp x Sleep) | "no heatmap fields found" error |

### Query Fixes

- **Best & Worst Runs**: Fixed UNION ALL syntax (wrapped subqueries with `SELECT * FROM (...)`)
- **80/20 Analysis pie chart**: Fixed `reduceOptions` with `"values": true` to show both Easy/Hard slices

### Color Scheme

Consistent colors based on data meaning:

| Color | Meaning | Panels |
|-------|---------|--------|
| Blue | Distance/Volume | Total Runs, Total Miles, Avg Weekly Miles, Weekly Mileage bar chart, Aerobic Training Effect |
| Green | Performance/Fitness | Avg Pace, Monthly Pace bar chart, VO2max scatter, Running Dynamics |
| Orange | Effort | Relative Effort Over Time scatter |
| Red | Hard zones | 80/20 pie chart (hard portion) |
| Purple | Sleep/Recovery | Sleep Score vs Pace, HRV vs Effort, Body Battery vs Pace, Deep Sleep vs Pace |
| Green→Red gradient | Effort intensity | Relative Effort Distribution histogram |

### Axis Adjustments

- **Relative Effort Over Time**: Y-axis capped at 200 (via field override) to prevent outliers from compressing the main data cluster

### Layout Changes

Top stats redistributed (4 panels × width 6 = 24 total):
- Total Runs (blue)
- Total Miles (blue)
- Avg Weekly Miles (blue)
- Avg Pace (green)

### Known Limitations

1. **SQLite + Timeseries**: The frser-sqlite-datasource plugin doesn't work reliably with Grafana's timeseries visualization. Use bar charts or scatter plots instead.

2. **SQLite + Heatmaps**: Heatmap panels don't recognize SQLite data format. Use scatter plots as alternative.

3. **Time variables**: Must use `date($__from/1000, 'unixepoch')` format for SQLite date comparisons (converts milliseconds to Unix timestamp to date string).

---

## Dashboard Modifications (2026-02-08) - Golden Grot Refinements

### Panel Title Renames — Infrastructure Language

Reinforcing the "body as infrastructure" metaphor:

| Original | New |
|----------|-----|
| Weekly Training Intensity | Load Distribution by Zone |
| VO2max Trend | System Capacity Trend (VO2max) |
| Current VO2max | Max System Capacity |
| Avg Training Load | Avg System Load |
| Running Dynamics (Averages) | Runtime Performance Metrics |
| Aerobic Training Effect | Processing Efficiency Score |
| Body Battery Drain by Distance | Resource Depletion Under Load |
| Relative Effort Over Time | System Stress Over Time |
| Relative Effort Distribution | Stress Distribution |
| Runs with Garmin Data | Total System Logs |
| Easy Zone % (Target: 80%) | Easy Zone % (SLO: 80%) |

### Best & Worst Runs Table Enhancement

Added sleep_score and elevation_gain columns to enable root-cause analysis:
- Each row now reads like a post-incident review
- Example: "bad sleep + hot + hilly = worst performance"

### 80/20 Trend Chart

Replaced the redundant 80/20 pie chart (Row 8) with a **monthly Easy Zone % trend** bar chart:
- Shows whether training polarization is improving or degrading over time
- Threshold line at 80% (the SLO target)
- Color-coded: red <50%, orange 50-70%, yellow 70-80%, green >80%

### Row 7: "What Actually Matters" Panel

Added new synthesis panel showing pace impact of each variable:
- Cool Temp (<20C)
- Good Sleep (>75)
- Flat Route (<50m)
- Low Humidity (<70%)
- High HRV (>40)

Values show seconds per km faster when condition is favorable. This is the diagnostic conclusion — after checking everything in Rows 1-6, Row 7 tells you which factors matter most.

### Color Scheme by Section

| Row | Color | Meaning |
|-----|-------|---------|
| Row 1 (Effort) | Green/Orange | Effort metrics |
| Row 2 (Weather) | Orange | Environmental factors |
| Row 3 (Terrain) | Blue | Elevation/route analysis |
| Row 4 (Sleep) | Purple | Pre-run system state |
| Row 5 (Big Picture) | Blue/Green | Volume and performance |
| Row 6 (Fuel) | Yellow/Orange | Resource provisioning |
| Row 7 (Synthesis) | Multi-color | Pulling from all sections |
| Row 8 (Advanced) | Blue | Garmin deep telemetry |
