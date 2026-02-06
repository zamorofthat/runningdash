#!/usr/bin/env python3
"""
Ingest Strava and Oura data into SQLite for running analysis dashboard.

Usage: python3 ingest.py /path/to/runningdata/

The script expects:
- export_*/activities.csv (Strava export)
- oura_*_trends.csv (Oura export)

Safe to re-run - uses upsert logic to avoid duplicates.
"""

import csv
import sqlite3
import sys
import os
import glob
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "running_dashboard.db"


def parse_strava_date(date_str: str) -> tuple[str, int, str]:
    """Parse Strava date format and extract components.

    Returns: (date_iso, hour_of_day, day_of_week)
    """
    # Format: "Oct 12, 2023, 1:24:12 PM"
    dt = datetime.strptime(date_str, "%b %d, %Y, %I:%M:%S %p")
    return (
        dt.strftime("%Y-%m-%d"),
        dt.hour,
        dt.strftime("%A")  # Monday, Tuesday, etc.
    )


def safe_float(value: str) -> float | None:
    """Safely convert string to float, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def safe_int(value: str) -> int | None:
    """Safely convert string to int, returning None for empty/invalid."""
    f = safe_float(value)
    return int(f) if f is not None else None


def create_schema(conn: sqlite3.Connection):
    """Create database tables and views."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY,
            date DATE,
            name TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            pace_min_km REAL,
            avg_hr INTEGER,
            max_hr INTEGER,
            elevation_gain REAL,
            temp_c REAL,
            humidity REAL,
            weather TEXT,
            relative_effort INTEGER,
            hour_of_day INTEGER,
            day_of_week TEXT,
            calories INTEGER,
            -- Fueling estimates (1 gel = 30g carbs every 3 miles, starting at mile 3)
            gels_estimated INTEGER,
            carbs_g INTEGER
        );

        CREATE TABLE IF NOT EXISTS sleep (
            date DATE PRIMARY KEY,
            sleep_score INTEGER,
            readiness_score INTEGER,
            hrv INTEGER,
            resting_hr INTEGER,
            deep_sleep_min INTEGER,
            rem_sleep_min INTEGER,
            total_sleep_min INTEGER
        );

        DROP VIEW IF EXISTS run_with_sleep;
        CREATE VIEW run_with_sleep AS
        SELECT
            r.*,
            COALESCE(
                -- For morning runs (before noon), use same-day sleep data
                CASE WHEN r.hour_of_day < 12 THEN s_same.sleep_score END,
                -- Otherwise use previous night's sleep data
                s_prev.sleep_score
            ) as sleep_score,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.readiness_score END,
                s_prev.readiness_score
            ) as readiness_score,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.hrv END,
                s_prev.hrv
            ) as hrv,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.resting_hr END,
                s_prev.resting_hr
            ) as resting_hr,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.deep_sleep_min END,
                s_prev.deep_sleep_min
            ) as deep_sleep_min,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.rem_sleep_min END,
                s_prev.rem_sleep_min
            ) as rem_sleep_min,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.total_sleep_min END,
                s_prev.total_sleep_min
            ) as total_sleep_min
        FROM runs r
        LEFT JOIN sleep s_prev ON date(r.date, '-1 day') = s_prev.date
        LEFT JOIN sleep s_same ON date(r.date) = s_same.date;
    """)


def ingest_strava(conn: sqlite3.Connection, data_dir: Path) -> int:
    """Ingest Strava activities, filtering for runs only."""
    # Find the Strava export folder
    strava_dirs = list(data_dir.glob("export_*"))
    if not strava_dirs:
        print("Warning: No Strava export folder found (export_*)")
        return 0

    activities_file = strava_dirs[0] / "activities.csv"
    if not activities_file.exists():
        print(f"Warning: {activities_file} not found")
        return 0

    count = 0
    with open(activities_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Filter for runs only
            if row.get("Activity Type") != "Run":
                continue

            # Parse date and time components
            date_str = row.get("Activity Date", "")
            if not date_str:
                continue

            try:
                date_iso, hour_of_day, day_of_week = parse_strava_date(date_str)
            except ValueError as e:
                print(f"Warning: Could not parse date '{date_str}': {e}")
                continue

            # Calculate pace (min/km) from distance and time
            distance_m = safe_float(row.get("Distance"))  # in meters
            moving_time = safe_float(row.get("Moving Time"))  # in seconds

            distance_km = distance_m / 1000 if distance_m else None

            pace_min_km = None
            if distance_km and moving_time and distance_km > 0:
                pace_min_km = (moving_time / 60) / distance_km

            # Get activity ID
            activity_id = safe_int(row.get("Activity ID"))
            if not activity_id:
                continue

            # Get calories from Strava
            calories = safe_int(row.get("Calories"))

            # Calculate fueling estimates for long runs (9+ miles / ~14.5km)
            # Protocol: 1 gel (30g carbs) every 3 miles, starting at mile 3
            gels_estimated = None
            carbs_g = None
            if distance_km and distance_km >= 14.48:  # 9 miles
                distance_miles = distance_km * 0.621371
                # First gel at mile 3, then every 3 miles after
                # e.g., 10 miles = gels at 3, 6, 9 = 3 gels
                gels_estimated = max(0, int((distance_miles - 3) // 3) + 1)
                carbs_g = gels_estimated * 30

            # Upsert the run
            conn.execute("""
                INSERT OR REPLACE INTO runs (
                    id, date, name, distance_km, duration_sec, pace_min_km,
                    avg_hr, max_hr, elevation_gain, temp_c, humidity,
                    weather, relative_effort, hour_of_day, day_of_week,
                    calories, gels_estimated, carbs_g
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_id,
                date_iso,
                row.get("Activity Name"),
                distance_km,
                safe_int(row.get("Moving Time")),
                pace_min_km,
                safe_int(row.get("Average Heart Rate")),
                safe_int(row.get("Max Heart Rate")),
                safe_float(row.get("Elevation Gain")),
                safe_float(row.get("Weather Temperature")),
                safe_float(row.get("Humidity")),
                row.get("Weather Condition"),
                safe_int(row.get("Relative Effort")),
                hour_of_day,
                day_of_week,
                calories,
                gels_estimated,
                carbs_g
            ))
            count += 1

    conn.commit()
    return count


def ingest_oura(conn: sqlite3.Connection, data_dir: Path) -> int:
    """Ingest Oura sleep/readiness data."""
    # Find the Oura file
    oura_files = list(data_dir.glob("oura_*_trends.csv"))
    if not oura_files:
        print("Warning: No Oura trends file found (oura_*_trends.csv)")
        return 0

    oura_file = oura_files[0]

    count = 0
    with open(oura_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            date = row.get("date", "").strip()
            if not date:
                continue

            # Convert deep sleep from seconds to minutes
            deep_sleep_sec = safe_int(row.get("Deep Sleep Duration"))
            deep_sleep_min = deep_sleep_sec // 60 if deep_sleep_sec else None

            rem_sleep_sec = safe_int(row.get("REM Sleep Duration"))
            rem_sleep_min = rem_sleep_sec // 60 if rem_sleep_sec else None

            total_sleep_sec = safe_int(row.get("Total Sleep Duration"))
            total_sleep_min = total_sleep_sec // 60 if total_sleep_sec else None

            conn.execute("""
                INSERT OR REPLACE INTO sleep (
                    date, sleep_score, readiness_score, hrv, resting_hr,
                    deep_sleep_min, rem_sleep_min, total_sleep_min
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date,
                safe_int(row.get("Sleep Score")),
                safe_int(row.get("Readiness Score")),
                safe_int(row.get("Average HRV")),
                safe_int(row.get("Average Resting Heart Rate")),
                deep_sleep_min,
                rem_sleep_min,
                total_sleep_min
            ))
            count += 1

    conn.commit()
    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ingest.py /path/to/runningdata/")
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        sys.exit(1)

    print(f"Database: {DB_PATH}")
    print(f"Data source: {data_dir}")
    print()

    conn = sqlite3.connect(DB_PATH)

    # Create schema
    print("Creating schema...")
    create_schema(conn)

    # Ingest Strava
    print("Ingesting Strava runs...")
    run_count = ingest_strava(conn, data_dir)
    print(f"  {run_count} runs loaded")

    # Ingest Oura
    print("Ingesting Oura sleep data...")
    sleep_count = ingest_oura(conn, data_dir)
    print(f"  {sleep_count} sleep records loaded")

    # Summary stats
    print()
    print("Summary:")

    cur = conn.execute("SELECT MIN(date), MAX(date) FROM runs")
    min_date, max_date = cur.fetchone()
    print(f"  Run date range: {min_date} to {max_date}")

    cur = conn.execute("SELECT SUM(distance_km) FROM runs")
    total_km = cur.fetchone()[0]
    print(f"  Total distance: {total_km:.1f} km ({total_km * 0.621371:.1f} miles)")

    cur = conn.execute("SELECT COUNT(*) FROM run_with_sleep WHERE sleep_score IS NOT NULL")
    joined = cur.fetchone()[0]
    print(f"  Runs with sleep data: {joined}")

    cur = conn.execute("SELECT COUNT(*), SUM(gels_estimated), SUM(carbs_g) FROM runs WHERE gels_estimated IS NOT NULL")
    long_runs, total_gels, total_carbs = cur.fetchone()
    print(f"  Long runs (9+ mi): {long_runs} ({total_gels} gels, {total_carbs}g carbs)")

    conn.close()
    print()
    print("Done!")


if __name__ == "__main__":
    main()
