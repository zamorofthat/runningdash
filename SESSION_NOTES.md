# Running Dashboard Session Notes

## Project Overview

Built a SQLite-backed Grafana dashboard for a conference talk: **"Debug the most complex production system of all: your body"**

### Files Created

| File | Purpose |
|------|---------|
| `ingest.py` | Parses Strava + Oura CSVs, loads SQLite |
| `running_dashboard.db` | SQLite database with all data |
| `dashboard.json` | Grafana dashboard (32+ panels, 7 rows) |
| `README.md` | Setup and usage documentation |

---

## Data Summary

| Source | Records | Date Range |
|--------|---------|------------|
| Strava runs | 339 | Oct 2023 - Feb 2026 |
| Oura sleep | 488 | Sep 2024 - Mar 2026 |
| Runs with sleep data | 203 | (joined) |
| Long runs (9+ mi) | 30 | (with fueling estimates) |

**Total distance:** 2,329 km (1,448 miles)

---

## Key Findings & Stories

### 1. The Hero's Journey

| Milestone | Date | Pace |
|-----------|------|------|
| First run | Oct 2023 | 8:38/km |
| First 5K race | Nov 2024 | 5:71/km |
| Brooklyn Half | Apr 2025 | 5:46/km (1:11 finish) |
| 5K PR | May 2025 | **4:53/km** |
| NYC Marathon | Nov 2025 | 6:53/km (**4:17 finish**) |

**Volume growth:**
- 2023: 21 miles
- 2024: 357 miles
- 2025: 931 miles

---

### 2. The 80/20 Rule Analysis

**Important: Easy zone is HR < 159** (user-specific threshold)

#### All-Time Distribution
| Zone | Runs | % |
|------|------|---|
| Easy (<159 HR) | 136 | 41.3% |
| Tempo/Hard (159+) | 193 | 58.7% |

Still not 80/20, but not as bad as initially calculated with wrong zones.

---

### 3. NYC vs Tokyo Marathon Training Blocks

#### Weekly Structure
| Block | Runs/Week | Hard/Week | Easy/Week |
|-------|-----------|-----------|-----------|
| NYC (Aug-Oct '25) | 3.2 | 1.6 | 1.6 |
| Tokyo (Dec-Feb '26) | 3.9 | **2.5** | 1.4 |

**Key insight:** Tokyo block has 2 intentional interval/tempo runs per week.

#### Zone Distribution
| Block | Easy (<159) | Hard (159+) |
|-------|-------------|-------------|
| NYC | 48.9% | 51.1% |
| Tokyo | 35.9% | 64.1% |

**Why Tokyo looks "worse":** Intentional polarized training with 2 structured hard days per week.

#### The Real Story
| Metric | NYC | Tokyo | Better? |
|--------|-----|-------|---------|
| Easy pace | 5:85/km | **6:02/km** | Tokyo (slower = truly easy) |
| Hard runs/week | 1.6 | 2.5 | Tokyo (intentional) |
| Structure | ad hoc | planned | Tokyo |

**Narrative:** "The dashboard said I was running harder for Tokyo. But that's intentional polarization - 2 hard days, the rest truly easy."

---

### 4. Weather Impact

| Conditions | Pace | HR |
|------------|------|-----|
| Cold (<10°C) | 5:74/km | 158 |
| Hot (20°C+) | 5:92/km | 163 |

**Cost:** 18 sec/km slower + 5 bpm higher in heat.

---

### 5. The Becca Factor

| Type | Avg Pace | Difference |
|------|----------|------------|
| Solo runs | 5:87/km | — |
| With Becca | 7:29/km | +1:42 slower |

**Story:** Social runs aren't training runs. And that's okay.

---

### 6. Sleep & Race Performance

| Race | Sleep Score | Readiness | Result |
|------|-------------|-----------|--------|
| Brooklyn Half | 79 | 89 | 1:11 (great) |
| NYC Marathon | **61** | **65** | 4:17 (survived) |

**Story:** "I ran my first marathon on 61% battery."

---

### 7. Fueling Analysis

**Protocol:** 1 gel (30g carbs) every 3 miles, starting at mile 3

| Stat | Value |
|------|-------|
| Long runs (9+ mi) | 30 |
| Total gels consumed | 119 |
| Total carbs | 3,570g |
| Avg calorie replacement | 23.9% |

**By distance:**
| Distance | Gels | Carbs | Calories Burned | Replace % |
|----------|------|-------|-----------------|-----------|
| 13 mi (half) | 4 | 120g | 2,000 | 24% |
| 26 mi (marathon) | 8 | 240g | 4,137 | 23% |

---

## Dashboard Structure

### Row 0: Context Header
- Total Runs, Total Miles, Date Range, Avg Weekly Miles, Avg Pace

### Row 1: Was the Easy Run Actually Too Hard?
- Effort vs Pace scatter
- HR Drift Detection
- Relative Effort histogram

### Row 2: Did the Weather Wreck Me?
- Temp vs Pace, Temp vs HR, Humidity vs Pace
- Weather Heatmap (Temp × Humidity)

### Row 3: Did the Trail Just Suck?
- Elevation Gain vs Pace
- Flat vs Hilly comparison (the "hill tax")

### Row 4: Was Sleep the Problem?
- Sleep Score vs Pace
- HRV vs Relative Effort
- Readiness Score vs Pace
- Deep Sleep vs Pace

### Row 5: The Big Picture
- Training Load vs Sleep (weekly)
- Monthly Pace Trend
- Best/Worst Runs table

### Row 6: Did I Fuel Properly?
- Long run stats (count, gels, carbs, replacement %)
- Carb Calories vs Total Burned bar chart
- Long Run Fueling Log table
- Gels vs Pace scatter

### Row 7: Putting It All Together
- Optimal Conditions heatmap (Temp × Sleep)
- Pace by Day of Week
- Pace by Time of Day

---

## TODO / Next Steps

1. **Add Training Structure Panel** - Hard vs easy runs per week over time (stacked bar or dual line chart)

2. **NYC vs Tokyo Comparison View** - Side-by-side training block comparison panel

3. **Recalibrate HR zones** - Current threshold is 159 for easy/tempo split

4. **Add annotations** - Mark race days, injuries, travel on timeline

---

## Talk Structure (Suggested)

1. **Hook:** "I ran a marathon on 61% battery. Here's how I knew I was screwed."

2. **The Data:** Show the dashboard - 339 runs, 1,448 miles, 2+ years

3. **Bug #1:** The 80/20 violation - "Every run above this line was too hard"

4. **Bug #2:** Temperature heatmap - "Why August sucked"

5. **Bug #3:** The Becca runs - humor break

6. **Bug #4:** Sleep vs race performance - marathon on 61 sleep score

7. **The Fix:** NYC vs Tokyo comparison - "I found the bug but the fix is harder than code"

8. **Payoff:** Marathon finish with full context

---

## Commands

```bash
# Re-ingest data after new exports
python3 ingest.py ~/Downloads/runningdata/

# Verify data
sqlite3 running_dashboard.db "SELECT COUNT(*) FROM runs; SELECT COUNT(*) FROM sleep;"

# Check training block zones (Easy = HR < 159)
sqlite3 running_dashboard.db "
SELECT
  CASE WHEN avg_hr < 159 THEN 'Easy' ELSE 'Hard' END as zone,
  COUNT(*) as runs
FROM runs
WHERE date BETWEEN '2025-12-01' AND '2026-02-28'
  AND avg_hr IS NOT NULL
GROUP BY 1;
"
```

---

## Grafana Setup

1. Install SQLite plugin: `grafana-cli plugins install frser-sqlite-datasource`
2. Add datasource with UID `sqlite`, path: `/Users/azamora/Projects/runningdash/running_dashboard.db`
3. Import `dashboard.json`
