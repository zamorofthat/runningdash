# Dashboard Preview

Visual mockup of the Grafana dashboard layout.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  DEBUGGING YOUR RUNNING: CONVERTING DATA TO INSIGHT                                     │
├─────────────────┬─────────────────┬─────────────────────────┬───────────────┬───────────┤
│   Total Runs    │   Total Miles   │       Date Range        │ Avg Weekly Mi │ Avg Pace  │
│      339        │     1,448       │  2023-10-12 to 2026-02  │     12.3      │  5.87     │
├─────────────────┴─────────────────┴─────────────────────────┴───────────────┴───────────┤
│  ROW 1: WAS THE EASY RUN ACTUALLY TOO HARD?                                             │
├───────────────────────────┬───────────────────────────┬─────────────────────────────────┤
│   Effort vs Pace Scatter  │   HR Drift Detection      │   Relative Effort Distribution  │
│                           │                           │                                 │
│    HR ▲                   │   effort ▲    · ·         │   ▐██                           │
│       │  · ·  ·           │          │ ·  ·  · ·      │   ▐████                         │
│       │ ·  · ·· ·         │          │·  ·   ·  ·     │   ▐██████                       │
│       │· · ·· · ·         │          └──────────► t   │   ▐████████                     │
│       └──────────► pace   │                           │   ▐██████                       │
│                           │                           │   └──────────► effort           │
├───────────────────────────┴───────────────────────────┴─────────────────────────────────┤
│  ROW 2: DID THE WEATHER WRECK ME?                                                       │
├──────────────────┬──────────────────┬──────────────────┬────────────────────────────────┤
│  Temp vs Pace    │  Temp vs HR      │  Humidity vs Pace│   Weather Heatmap              │
│                  │                  │                  │   ┌─────────────────┐          │
│  pace ▲   ·      │  HR ▲      ·     │  pace ▲    ·     │   │░░▒▒▓▓██████████│ humid    │
│      │ ·  · ·    │     │   · · ·    │      │  · · ·    │   │░░▒▒▓▓████████░░│          │
│      │  · · · ·  │     │ · · · ·    │      │ · · · ·   │   │░░▒▒▓▓██████░░░░│          │
│      └────────►  │     └────────►   │      └────────►  │   │░░▒▒▓▓████░░░░░░│          │
│           temp   │          temp    │        humidity  │   └─────────────────┘ temp    │
├──────────────────┴──────────────────┴──────────────────┴────────────────────────────────┤
│  ROW 3: DID THE TRAIL JUST SUCK?                                                        │
├─────────────────────────────────────────┬───────────────────────────────────────────────┤
│   Elevation Gain vs Pace                │   Flat vs Hilly: The Hill Tax                 │
│                                         │                                               │
│   pace ▲       ·  ·                     │   ┌─────┐                                     │
│        │    ·  · ·  ·                   │   │█████│ 5.90  Flat (<50m)                   │
│        │  · · · ·  ·  ·                 │   │█████│ 5.97  Rolling                       │
│        │ · · · ·                        │   │█████│ 6.17  Hilly (>100m)                 │
│        └─────────────────► elevation    │   └─────┘                                     │
├─────────────────────────────────────────┴───────────────────────────────────────────────┤
│  ROW 4: WAS SLEEP THE PROBLEM?                                                          │
├──────────────────┬──────────────────┬──────────────────┬────────────────────────────────┤
│ Sleep vs Pace    │ HRV vs Effort    │ Readiness vs Pace│ Deep Sleep vs Pace             │
│                  │                  │                  │                                │
│ pace ▲  ·  ·     │ effort ▲   ·     │ pace ▲   ·  ·    │ pace ▲     ·  ·                │
│     │ ·  · · ·   │       │ · · ·    │     │  · · · ·   │     │   · · · ·                │
│     │· · · · ·   │       │  · · ·   │     │ · · · ·    │     │  · · · ·                 │
│     └─────────►  │       └───────►  │     └─────────►  │     └───────────►              │
│       sleep score│          HRV     │      readiness   │        deep sleep min          │
├──────────────────┴──────────────────┴──────────────────┴────────────────────────────────┤
│  ROW 5: THE BIG PICTURE                                                                 │
├─────────────────────────────────────────┬───────────────────────────────────────────────┤
│  Training Load vs Sleep (Weekly)        │   Monthly Pace Trend                          │
│                                         │                                               │
│  miles ▲          ╱╲    ╱╲   sleep     │   pace ▲                                       │
│       │    ╱╲   ╱    ╲╱   ╲            │        │ ·                                     │
│       │  ╱    ╲╱              ╲        │        │   ·  ·                                │
│       │╱                        ╲      │        │     ·  · ·  · ·                       │
│       └─────────────────────────► week │        └─────────────────► month               │
├─────────────────────────────────────────┴───────────────────────────────────────────────┤
│  Best & Worst Runs                                                                      │
│ ┌──────────┬────────────┬─────────────────────────────┬───────┬────────┬──────┬───────┐ │
│ │ category │ date       │ name                        │ pace  │ dist   │ HR   │ temp  │ │
│ ├──────────┼────────────┼─────────────────────────────┼───────┼────────┼──────┼───────┤ │
│ │ Fastest  │ 2025-05-03 │ Mindful 5k                  │ 4.53  │ 3.2    │ 172  │ 18    │ │
│ │ Fastest  │ 2025-01-01 │ Fear Less 5K                │ 5.05  │ 3.1    │ 168  │ 5     │ │
│ │ Slowest  │ 2024-07-05 │ Morning run with Becca      │ 8.53  │ 3.9    │      │ 20    │ │
│ │ Slowest  │ 2024-06-26 │ Nike Run Club: The Shifter  │ 7.93  │ 3.2    │ 141  │       │ │
│ └──────────┴────────────┴─────────────────────────────┴───────┴────────┴──────┴───────┘ │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  ROW 6: DID I FUEL PROPERLY?                                                            │
├────────────────┬────────────────┬────────────────┬────────────────┬─────────────────────┤
│ Long Runs      │ Total Gels     │ Total Carbs    │ Avg Carb       │ Carb Cal vs Burned  │
│   (9+ mi)      │  Consumed      │  Consumed      │ Replacement    │                     │
│     30         │    119         │   3,570g       │   23.9%        │  ▐██ carbs          │
│                │                │                │                │  ▐████████ burned   │
├────────────────┴────────────────┴────────────────┴────────────────┤                     │
│  Long Run Fueling Log                                             │  9mi  13mi  26mi    │
│ ┌────────────┬─────────────────────────┬───────┬──────┬─────────┐ ├─────────────────────┤
│ │ date       │ name                    │ miles │ gels │ carbs   │ │ Gels vs Pace        │
│ ├────────────┼─────────────────────────┼───────┼──────┼─────────┤ │                     │
│ │ 2025-11-02 │ NYC Marathon            │ 26.3  │ 8    │ 240g    │ │ pace ▲   ·          │
│ │ 2025-10-04 │ Morning Run             │ 21.0  │ 7    │ 210g    │ │      │ · · ·        │
│ │ 2026-01-18 │ Morning Run             │ 19.3  │ 6    │ 180g    │ │      │  · ·  ·      │
│ │ 2025-04-27 │ Brooklyn half!          │ 13.3  │ 4    │ 120g    │ │      └──────► gels  │
│ └────────────┴─────────────────────────┴───────┴──────┴─────────┘ └─────────────────────┤
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  ROW 7: PUTTING IT ALL TOGETHER                                                         │
├───────────────────────────┬───────────────────────────┬─────────────────────────────────┤
│  Optimal Conditions       │  Pace by Day of Week      │  Pace by Time of Day            │
│  (Temp × Sleep Heatmap)   │                           │                                 │
│  ┌─────────────────┐      │  ▐███ 5.82  Mon           │  ▐████ 6.12  Early (0-6)        │
│  │░░▒▒▓▓██████████│ sleep│  ▐███ 5.74  Tue           │  ▐███  5.89  Morning (6-12)     │
│  │░░▒▒▓▓████████░░│      │  ▐███ 5.93  Wed           │  ▐███  5.91  Afternoon (12-18)  │
│  │░░▒▒▓▓██████░░░░│      │  ▐███ 5.77  Thu           │  ▐██   5.77  Evening (18-24)    │
│  │░░▒▒▓▓████░░░░░░│      │  ▐███ 5.88  Fri           │                                 │
│  └─────────────────┘ temp │  ▐███ 5.86  Sat           │                                 │
│   green=fast, red=slow    │  ▐███ 5.93  Sun           │                                 │
├───────────────────────────┴───────────────────────────┴─────────────────────────────────┤
│  ROW 8: ADVANCED METRICS (GARMIN)                                                       │
├──────────────────┬──────────────────┬──────────────────┬────────────────────────────────┤
│ Real 80/20       │ Training Effect  │  VO2max Trend    │ Running Dynamics               │
│   (Pie Chart)    │   Trend          │                  │                                │
│   ┌────────┐     │  TE ▲     ·      │  VO2 ▲           │  Ground Contact │ 264 ms       │
│   │ ██░░░░ │     │     │  · · ·     │      │    ╱──╲   │  Stride Length  │ 92 cm        │
│   │ ██░░░░ │     │     │ · ·  ·  ·  │      │ ╱─╱    ╲  │  Vertical Osc   │ 7.6 cm       │
│   │ ██████ │     │     └────────►   │      └───────►   │  Avg Power      │ 378 W        │
│   └────────┘     │        date      │       date       │                                │
│ ██ Easy (10%)    │  · Aerobic       │                  │                                │
│ ░░ Hard (90%)    │  · Anaerobic     │                  │                                │
├──────────────────┴──────────────────┴──────────────────┴────────────────────────────────┤
│  Body Battery          │  Weekly Training Intensity    │  Stats                         │
│  Drain by Distance     │  (Stacked Bar)                │  ┌──────────────────────────┐  │
│                        │                               │  │ Runs w/ Garmin │   200   │  │
│  drain ▲   ·  ·        │  hrs ▲ ████████  ░░░░        │  │ Current VO2max │   49    │  │
│       │ ·  ·  · ·      │      │ ████████  ░░░░        │  │ Avg Load       │   156   │  │
│       │  · ·  ·  ·     │      │ ████████  ░░░░        │  │ Easy Zone %    │  9.9%   │  │
│       └──────────► km  │      └──────────► week       │  └──────────────────────────┘  │
│                        │  ████ Easy (Z1-2) ░░ Hard    │   (Target: 80% easy)           │
└────────────────────────┴───────────────────────────────┴────────────────────────────────┘
```

---

## Panel Summary

| Row | Panel | Type | Purpose |
|-----|-------|------|---------|
| 0 | Total Runs | Stat | Count of all runs |
| 0 | Total Miles | Stat | Sum of distance |
| 0 | Date Range | Stat | First to last run |
| 0 | Avg Weekly Miles | Stat | Mileage per week |
| 0 | Avg Pace | Stat | Overall average pace |
| 1 | Effort vs Pace | XY Scatter | HR by pace - dots above line = too hard |
| 1 | HR Drift Detection | Time Series | Relative effort over time |
| 1 | Relative Effort Distribution | Histogram | Should be mostly easy |
| 2 | Temp vs Pace | XY Scatter | Heat slows you down |
| 2 | Temp vs HR | XY Scatter | Same pace, higher HR in heat |
| 2 | Humidity vs Pace | XY Scatter | Humidity impact |
| 2 | Weather Heatmap | Heatmap | Temp × Humidity sweet spot |
| 3 | Elevation vs Pace | XY Scatter | Hill impact |
| 3 | Flat vs Hilly | Bar Chart | Quantify the hill tax |
| 4 | Sleep Score vs Pace | XY Scatter | Sleep impact |
| 4 | HRV vs Relative Effort | XY Scatter | Recovery vs perceived effort |
| 4 | Readiness vs Pace | XY Scatter | Trust the readiness score? |
| 4 | Deep Sleep vs Pace | XY Scatter | Deep sleep recovery |
| 5 | Training Load vs Sleep | Dual Axis | Weekly miles + sleep |
| 5 | Monthly Pace Trend | Time Series | Getting faster? |
| 5 | Best & Worst Runs | Table | Top/bottom 5 with conditions |
| 6 | Long Runs (9+ mi) | Stat | Count |
| 6 | Total Gels | Stat | Sum |
| 6 | Total Carbs | Stat | Sum in grams |
| 6 | Avg Carb Replacement | Stat | % of calories replaced |
| 6 | Carb Cal vs Burned | Bar Chart | Intake vs output |
| 6 | Long Run Fueling Log | Table | All long runs with fueling |
| 6 | Gels vs Pace | XY Scatter | Fueling correlation |
| 7 | Optimal Conditions | Heatmap | Temp × Sleep score |
| 7 | Pace by Day of Week | Bar Chart | Best/worst days |
| 7 | Pace by Time of Day | Bar Chart | Morning vs evening |
| 8 | Real 80/20 Analysis | Pie Chart | Actual time in easy vs hard zones |
| 8 | Training Effect Trend | Time Series | Aerobic/anaerobic TE over time |
| 8 | VO2max Trend | Time Series | VO2max progression |
| 8 | Running Dynamics | Bar Chart | Ground contact, stride, osc, power |
| 8 | Body Battery Drain | XY Scatter | Energy drain by distance |
| 8 | Weekly Training Intensity | Stacked Bar | Easy vs hard hours per week |
| 8 | Runs with Garmin Data | Stat | Count of matched runs |
| 8 | Current VO2max | Stat | Latest VO2max estimate |
| 8 | Avg Training Load | Stat | Average training load per run |
| 8 | Easy Zone % | Stat | % time in easy zones (target: 80%) |

---

## To View the Real Dashboard

```bash
# Option 1: Docker
docker run -d -p 3000:3000 \
  -v /Users/azamora/Projects/runningdash:/data \
  grafana/grafana

# Option 2: Homebrew (macOS)
brew services start grafana

# Then:
# 1. Open http://localhost:3000 (admin/admin)
# 2. Configuration > Data Sources > Add SQLite
#    - Name: sqlite
#    - UID: sqlite
#    - Path: /Users/azamora/Projects/runningdash/running_dashboard.db
# 3. Dashboards > Import > Upload dashboard.json
```
