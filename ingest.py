#!/usr/bin/env python3
"""
Ingest Strava, Garmin, and Oura data into SQLite or PostgreSQL for running analysis dashboard.

Usage:
  SQLite (local):     python3 ingest.py /path/to/runningdata/
  PostgreSQL (cloud): python3 ingest.py /path/to/runningdata/ --postgres "postgresql://user:pass@host/db"

Data Flow
=========

    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │     Strava      │    │     Garmin      │    │      Oura       │
    │  export_*/      │    │  */DI_CONNECT/  │    │  oura_*_trends  │
    │  activities.csv │    │  *_summarized   │    │     .csv        │
    │                 │    │  Activities.json│    │                 │
    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
             │                      │                      │
             │ Runs: date, distance │ Runs: VO2max, power  │ Sleep: score,
             │ pace, HR, weather,   │ training effect,     │ HRV, readiness,
             │ relative effort      │ running dynamics     │ deep/REM sleep
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────┐
                         │    ingest.py     │
                         │                  │
                         │ 1. Load Strava   │
                         │ 2. Load Garmin   │
                         │ 3. Match by date │
                         │    + distance    │
                         │ 4. Load Oura     │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │    SQLite DB     │
                         │                  │
                         │ Tables:          │
                         │  - runs          │
                         │  - garmin_runs   │
                         │  - sleep         │
                         │                  │
                         │ Views:           │
                         │  - run_with_sleep│
                         └──────────────────┘

Expected Input Files
====================

- export_*/activities.csv (Strava export)
- */DI_CONNECT/DI-Connect-Fitness/*_summarizedActivities.json (Garmin export)
- oura_*_trends.csv (Oura export)

Matching Logic
==============

Garmin runs are matched to Strava runs by:
1. Same date
2. Distance within 5% tolerance

This allows enriching Strava runs with Garmin's advanced metrics (VO2max,
training effect, running dynamics, HR zones) while keeping Strava as the
source of truth for basic run data.

Sleep data is joined via the run_with_sleep view:
- Morning runs (before noon) use same-day sleep data
- Afternoon/evening runs use previous night's sleep data

Safe to re-run - uses upsert logic to avoid duplicates.
"""

import argparse
import csv
import json
import sqlite3
import sys
import os
import glob
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "running_dashboard.db"

# PostgreSQL support (optional)
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


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
            carbs_g INTEGER,
            -- Garmin metrics (matched by date/distance)
            garmin_id BIGINT,
            aerobic_te REAL,
            anaerobic_te REAL,
            training_load REAL,
            vo2max REAL,
            avg_power INTEGER,
            avg_ground_contact_time REAL,
            avg_vertical_oscillation REAL,
            avg_stride_length REAL,
            body_battery_change INTEGER,
            hr_zone_1_sec INTEGER,
            hr_zone_2_sec INTEGER,
            hr_zone_3_sec INTEGER,
            hr_zone_4_sec INTEGER,
            hr_zone_5_sec INTEGER
        );

        CREATE TABLE IF NOT EXISTS garmin_runs (
            id INTEGER PRIMARY KEY,
            date DATE,
            name TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            min_hr INTEGER,
            calories REAL,
            elevation_gain REAL,
            elevation_loss REAL,
            avg_speed REAL,
            max_speed REAL,
            avg_cadence REAL,
            max_cadence REAL,
            steps INTEGER,
            -- Training metrics
            aerobic_te REAL,
            anaerobic_te REAL,
            training_load REAL,
            vo2max REAL,
            training_effect_label TEXT,
            -- Running dynamics
            avg_power INTEGER,
            max_power INTEGER,
            norm_power INTEGER,
            avg_ground_contact_time REAL,
            avg_vertical_oscillation REAL,
            avg_vertical_ratio REAL,
            avg_stride_length REAL,
            -- HR zones (milliseconds)
            hr_zone_0_ms INTEGER,
            hr_zone_1_ms INTEGER,
            hr_zone_2_ms INTEGER,
            hr_zone_3_ms INTEGER,
            hr_zone_4_ms INTEGER,
            hr_zone_5_ms INTEGER,
            -- Body metrics
            body_battery_change INTEGER,
            water_estimated REAL,
            -- Temperature
            min_temp REAL,
            max_temp REAL,
            -- Workout perception
            workout_feel INTEGER,
            workout_rpe INTEGER,
            -- Location
            location_name TEXT,
            start_lat REAL,
            start_lon REAL
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


def create_schema_postgres(conn):
    """Create PostgreSQL database tables and views."""
    cur = conn.cursor()

    cur.execute("DROP VIEW IF EXISTS run_with_sleep")
    cur.execute("DROP TABLE IF EXISTS runs CASCADE")
    cur.execute("DROP TABLE IF EXISTS sleep CASCADE")
    cur.execute("DROP TABLE IF EXISTS garmin_runs CASCADE")

    cur.execute("""
        CREATE TABLE runs (
            id BIGINT PRIMARY KEY,
            date DATE,
            name TEXT,
            distance_km DOUBLE PRECISION,
            duration_sec INTEGER,
            pace_min_km DOUBLE PRECISION,
            avg_hr INTEGER,
            max_hr INTEGER,
            elevation_gain DOUBLE PRECISION,
            temp_c DOUBLE PRECISION,
            humidity DOUBLE PRECISION,
            weather TEXT,
            relative_effort INTEGER,
            hour_of_day INTEGER,
            day_of_week TEXT,
            calories INTEGER,
            gels_estimated INTEGER,
            carbs_g INTEGER,
            garmin_id BIGINT,
            aerobic_te DOUBLE PRECISION,
            anaerobic_te DOUBLE PRECISION,
            training_load DOUBLE PRECISION,
            vo2max DOUBLE PRECISION,
            avg_power INTEGER,
            avg_ground_contact_time DOUBLE PRECISION,
            avg_vertical_oscillation DOUBLE PRECISION,
            avg_stride_length DOUBLE PRECISION,
            body_battery_change INTEGER,
            hr_zone_1_sec INTEGER,
            hr_zone_2_sec INTEGER,
            hr_zone_3_sec INTEGER,
            hr_zone_4_sec INTEGER,
            hr_zone_5_sec INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE garmin_runs (
            id BIGINT PRIMARY KEY,
            date DATE,
            name TEXT,
            distance_km DOUBLE PRECISION,
            duration_sec INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            min_hr INTEGER,
            calories DOUBLE PRECISION,
            elevation_gain DOUBLE PRECISION,
            elevation_loss DOUBLE PRECISION,
            avg_speed DOUBLE PRECISION,
            max_speed DOUBLE PRECISION,
            avg_cadence DOUBLE PRECISION,
            max_cadence DOUBLE PRECISION,
            steps INTEGER,
            aerobic_te DOUBLE PRECISION,
            anaerobic_te DOUBLE PRECISION,
            training_load DOUBLE PRECISION,
            vo2max DOUBLE PRECISION,
            training_effect_label TEXT,
            avg_power INTEGER,
            max_power INTEGER,
            norm_power INTEGER,
            avg_ground_contact_time DOUBLE PRECISION,
            avg_vertical_oscillation DOUBLE PRECISION,
            avg_vertical_ratio DOUBLE PRECISION,
            avg_stride_length DOUBLE PRECISION,
            hr_zone_0_ms INTEGER,
            hr_zone_1_ms INTEGER,
            hr_zone_2_ms INTEGER,
            hr_zone_3_ms INTEGER,
            hr_zone_4_ms INTEGER,
            hr_zone_5_ms INTEGER,
            body_battery_change INTEGER,
            water_estimated DOUBLE PRECISION,
            min_temp DOUBLE PRECISION,
            max_temp DOUBLE PRECISION,
            workout_feel INTEGER,
            workout_rpe INTEGER,
            location_name TEXT,
            start_lat DOUBLE PRECISION,
            start_lon DOUBLE PRECISION
        )
    """)

    cur.execute("""
        CREATE TABLE sleep (
            date DATE PRIMARY KEY,
            sleep_score INTEGER,
            readiness_score INTEGER,
            hrv INTEGER,
            resting_hr INTEGER,
            deep_sleep_min INTEGER,
            rem_sleep_min INTEGER,
            total_sleep_min INTEGER
        )
    """)

    cur.execute("""
        CREATE VIEW run_with_sleep AS
        SELECT
            r.*,
            COALESCE(
                CASE WHEN r.hour_of_day < 12 THEN s_same.sleep_score END,
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
        LEFT JOIN sleep s_prev ON (r.date - INTERVAL '1 day')::DATE = s_prev.date
        LEFT JOIN sleep s_same ON r.date = s_same.date
    """)

    conn.commit()


def ingest_strava(conn, data_dir: Path, is_postgres: bool = False) -> int:
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

    cur = conn.cursor() if is_postgres else conn
    placeholder = "%s" if is_postgres else "?"

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

            values = (
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
            )

            if is_postgres:
                cur.execute(f"""
                    INSERT INTO runs (
                        id, date, name, distance_km, duration_sec, pace_min_km,
                        avg_hr, max_hr, elevation_gain, temp_c, humidity,
                        weather, relative_effort, hour_of_day, day_of_week,
                        calories, gels_estimated, carbs_g
                    ) VALUES ({', '.join([placeholder] * 18)})
                    ON CONFLICT (id) DO UPDATE SET
                        date = EXCLUDED.date, name = EXCLUDED.name,
                        distance_km = EXCLUDED.distance_km, duration_sec = EXCLUDED.duration_sec,
                        pace_min_km = EXCLUDED.pace_min_km, avg_hr = EXCLUDED.avg_hr,
                        max_hr = EXCLUDED.max_hr, elevation_gain = EXCLUDED.elevation_gain,
                        temp_c = EXCLUDED.temp_c, humidity = EXCLUDED.humidity,
                        weather = EXCLUDED.weather, relative_effort = EXCLUDED.relative_effort,
                        hour_of_day = EXCLUDED.hour_of_day, day_of_week = EXCLUDED.day_of_week,
                        calories = EXCLUDED.calories, gels_estimated = EXCLUDED.gels_estimated,
                        carbs_g = EXCLUDED.carbs_g
                """, values)
            else:
                cur.execute(f"""
                    INSERT OR REPLACE INTO runs (
                        id, date, name, distance_km, duration_sec, pace_min_km,
                        avg_hr, max_hr, elevation_gain, temp_c, humidity,
                        weather, relative_effort, hour_of_day, day_of_week,
                        calories, gels_estimated, carbs_g
                    ) VALUES ({', '.join([placeholder] * 18)})
                """, values)
            count += 1

    conn.commit()
    return count


def ingest_garmin(conn, data_dir: Path, is_postgres: bool = False) -> int:
    """Ingest Garmin activities, filtering for runs only."""
    # Find the Garmin export folder (UUID-named folder with DI_CONNECT)
    garmin_dirs = list(data_dir.glob("*/DI_CONNECT/DI-Connect-Fitness"))
    if not garmin_dirs:
        print("Warning: No Garmin export folder found")
        return 0

    # Find the summarizedActivities JSON file
    json_files = list(garmin_dirs[0].glob("*_summarizedActivities.json"))
    if not json_files:
        print(f"Warning: No summarizedActivities.json found in {garmin_dirs[0]}")
        return 0

    with open(json_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    activities = data[0].get("summarizedActivitiesExport", [])

    count = 0
    for activity in activities:
        # Filter for running activities only
        activity_type = activity.get("activityType", "")
        if activity_type not in ("running", "treadmill_running"):
            continue

        # Parse timestamp
        ts = activity.get("startTimeLocal") or activity.get("beginTimestamp")
        if not ts:
            continue

        dt = datetime.fromtimestamp(ts / 1000)
        date_iso = dt.strftime("%Y-%m-%d")

        # Get activity ID
        activity_id = activity.get("activityId")
        if not activity_id:
            continue

        # Distance in centimeters -> km
        distance_cm = activity.get("distance", 0)
        distance_km = distance_cm / 100000 if distance_cm else None

        # Duration in ms -> seconds
        duration_ms = activity.get("duration", 0)
        duration_sec = int(duration_ms / 1000) if duration_ms else None

        # HR zone times (ms)
        hr_zone_0 = activity.get("hrTimeInZone_0")
        hr_zone_1 = activity.get("hrTimeInZone_1")
        hr_zone_2 = activity.get("hrTimeInZone_2")
        hr_zone_3 = activity.get("hrTimeInZone_3")
        hr_zone_4 = activity.get("hrTimeInZone_4")
        hr_zone_5 = activity.get("hrTimeInZone_5")

        cur = conn.cursor() if is_postgres else conn
        placeholder = "%s" if is_postgres else "?"

        values = (
            activity_id,
            date_iso,
            activity.get("name"),
            distance_km,
            duration_sec,
            activity.get("avgHr"),
            activity.get("maxHr"),
            activity.get("minHr"),
            activity.get("calories"),
            activity.get("elevationGain"),
            activity.get("elevationLoss"),
            activity.get("avgSpeed"),
            activity.get("maxSpeed"),
            activity.get("avgRunCadence"),
            activity.get("maxRunCadence"),
            activity.get("steps"),
            activity.get("aerobicTrainingEffect"),
            activity.get("anaerobicTrainingEffect"),
            activity.get("activityTrainingLoad"),
            activity.get("vO2MaxValue"),
            activity.get("trainingEffectLabel"),
            activity.get("avgPower"),
            activity.get("maxPower"),
            activity.get("normPower"),
            activity.get("avgGroundContactTime"),
            activity.get("avgVerticalOscillation"),
            activity.get("avgVerticalRatio"),
            activity.get("avgStrideLength"),
            hr_zone_0,
            hr_zone_1,
            hr_zone_2,
            hr_zone_3,
            hr_zone_4,
            hr_zone_5,
            activity.get("differenceBodyBattery"),
            activity.get("waterEstimated"),
            activity.get("minTemperature"),
            activity.get("maxTemperature"),
            activity.get("workoutFeel"),
            activity.get("workoutRpe"),
            activity.get("locationName"),
            activity.get("startLatitude"),
            activity.get("startLongitude")
        )

        cols = """id, date, name, distance_km, duration_sec,
                avg_hr, max_hr, min_hr, calories,
                elevation_gain, elevation_loss, avg_speed, max_speed,
                avg_cadence, max_cadence, steps,
                aerobic_te, anaerobic_te, training_load, vo2max, training_effect_label,
                avg_power, max_power, norm_power,
                avg_ground_contact_time, avg_vertical_oscillation,
                avg_vertical_ratio, avg_stride_length,
                hr_zone_0_ms, hr_zone_1_ms, hr_zone_2_ms,
                hr_zone_3_ms, hr_zone_4_ms, hr_zone_5_ms,
                body_battery_change, water_estimated,
                min_temp, max_temp,
                workout_feel, workout_rpe,
                location_name, start_lat, start_lon"""

        if is_postgres:
            cur.execute(f"""
                INSERT INTO garmin_runs ({cols})
                VALUES ({', '.join([placeholder] * 43)})
                ON CONFLICT (id) DO NOTHING
            """, values)
        else:
            cur.execute(f"""
                INSERT OR REPLACE INTO garmin_runs ({cols})
                VALUES ({', '.join([placeholder] * 43)})
            """, values)
        count += 1

    conn.commit()
    return count


def match_garmin_to_strava(conn, is_postgres: bool = False) -> int:
    """Match Garmin runs to Strava runs by date and distance, update with Garmin metrics."""
    cur = conn.cursor() if is_postgres else conn
    placeholder = "%s" if is_postgres else "?"

    # Match runs within same date and distance within 5%
    cur.execute("""
        SELECT
            r.id as strava_id,
            g.id as garmin_id,
            g.aerobic_te,
            g.anaerobic_te,
            g.training_load,
            g.vo2max,
            g.avg_power,
            g.avg_ground_contact_time,
            g.avg_vertical_oscillation,
            g.avg_stride_length,
            g.body_battery_change,
            g.hr_zone_1_ms,
            g.hr_zone_2_ms,
            g.hr_zone_3_ms,
            g.hr_zone_4_ms,
            g.hr_zone_5_ms
        FROM runs r
        JOIN garmin_runs g ON r.date = g.date
            AND ABS(r.distance_km - g.distance_km) < (r.distance_km * 0.05)
        WHERE r.garmin_id IS NULL
    """)

    matches = cur.fetchall()

    for match in matches:
        values = (
            match[1],  # garmin_id
            match[2],  # aerobic_te
            match[3],  # anaerobic_te
            match[4],  # training_load
            match[5],  # vo2max
            match[6],  # avg_power
            match[7],  # avg_ground_contact_time
            match[8],  # avg_vertical_oscillation
            match[9],  # avg_stride_length
            match[10], # body_battery_change
            match[11] // 1000 if match[11] else None,  # hr_zone_1_sec
            match[12] // 1000 if match[12] else None,  # hr_zone_2_sec
            match[13] // 1000 if match[13] else None,  # hr_zone_3_sec
            match[14] // 1000 if match[14] else None,  # hr_zone_4_sec
            match[15] // 1000 if match[15] else None,  # hr_zone_5_sec
            match[0]   # strava_id
        )
        cur.execute(f"""
            UPDATE runs SET
                garmin_id = {placeholder},
                aerobic_te = {placeholder},
                anaerobic_te = {placeholder},
                training_load = {placeholder},
                vo2max = {placeholder},
                avg_power = {placeholder},
                avg_ground_contact_time = {placeholder},
                avg_vertical_oscillation = {placeholder},
                avg_stride_length = {placeholder},
                body_battery_change = {placeholder},
                hr_zone_1_sec = {placeholder},
                hr_zone_2_sec = {placeholder},
                hr_zone_3_sec = {placeholder},
                hr_zone_4_sec = {placeholder},
                hr_zone_5_sec = {placeholder}
            WHERE id = {placeholder}
        """, values)

    conn.commit()
    return len(matches)


def ingest_oura(conn, data_dir: Path, is_postgres: bool = False) -> int:
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

            cur = conn.cursor() if is_postgres else conn
            placeholder = "%s" if is_postgres else "?"

            values = (
                date,
                safe_int(row.get("Sleep Score")),
                safe_int(row.get("Readiness Score")),
                safe_int(row.get("Average HRV")),
                safe_int(row.get("Average Resting Heart Rate")),
                deep_sleep_min,
                rem_sleep_min,
                total_sleep_min
            )

            if is_postgres:
                cur.execute(f"""
                    INSERT INTO sleep (
                        date, sleep_score, readiness_score, hrv, resting_hr,
                        deep_sleep_min, rem_sleep_min, total_sleep_min
                    ) VALUES ({', '.join([placeholder] * 8)})
                    ON CONFLICT (date) DO UPDATE SET
                        sleep_score = EXCLUDED.sleep_score,
                        readiness_score = EXCLUDED.readiness_score,
                        hrv = EXCLUDED.hrv,
                        resting_hr = EXCLUDED.resting_hr,
                        deep_sleep_min = EXCLUDED.deep_sleep_min,
                        rem_sleep_min = EXCLUDED.rem_sleep_min,
                        total_sleep_min = EXCLUDED.total_sleep_min
                """, values)
            else:
                cur.execute(f"""
                    INSERT OR REPLACE INTO sleep (
                        date, sleep_score, readiness_score, hrv, resting_hr,
                        deep_sleep_min, rem_sleep_min, total_sleep_min
                    ) VALUES ({', '.join([placeholder] * 8)})
                """, values)
            count += 1

    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Strava, Garmin, and Oura data into SQLite or PostgreSQL"
    )
    parser.add_argument("data_dir", help="Path to runningdata directory")
    parser.add_argument(
        "--postgres",
        metavar="URL",
        help="PostgreSQL connection URL (e.g., postgresql://user:pass@host/db)"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        sys.exit(1)

    is_postgres = args.postgres is not None

    if is_postgres:
        if not HAS_PSYCOPG2:
            print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
            sys.exit(1)
        print(f"Database: PostgreSQL")
        conn = psycopg2.connect(args.postgres)
    else:
        print(f"Database: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)

    print(f"Data source: {data_dir}")
    print()

    # Create schema
    print("Creating schema...")
    if is_postgres:
        create_schema_postgres(conn)
    else:
        create_schema(conn)

    # Ingest Strava
    print("Ingesting Strava runs...")
    run_count = ingest_strava(conn, data_dir, is_postgres)
    print(f"  {run_count} runs loaded")

    # Ingest Garmin
    print("Ingesting Garmin runs...")
    garmin_count = ingest_garmin(conn, data_dir, is_postgres)
    print(f"  {garmin_count} runs loaded")

    # Match Garmin to Strava
    print("Matching Garmin metrics to Strava runs...")
    match_count = match_garmin_to_strava(conn, is_postgres)
    print(f"  {match_count} runs matched")

    # Ingest Oura
    print("Ingesting Oura sleep data...")
    sleep_count = ingest_oura(conn, data_dir, is_postgres)
    print(f"  {sleep_count} sleep records loaded")

    # Summary stats
    print()
    print("Summary:")

    cur = conn.cursor() if is_postgres else conn
    cur.execute("SELECT MIN(date), MAX(date) FROM runs")
    min_date, max_date = cur.fetchone()
    print(f"  Run date range: {min_date} to {max_date}")

    cur.execute("SELECT SUM(distance_km) FROM runs")
    total_km = cur.fetchone()[0]
    if total_km:
        print(f"  Total distance: {total_km:.1f} km ({total_km * 0.621371:.1f} miles)")

    cur.execute("SELECT COUNT(*) FROM run_with_sleep WHERE sleep_score IS NOT NULL")
    joined = cur.fetchone()[0]
    print(f"  Runs with sleep data: {joined}")

    cur.execute("SELECT COUNT(*), SUM(gels_estimated), SUM(carbs_g) FROM runs WHERE gels_estimated IS NOT NULL")
    long_runs, total_gels, total_carbs = cur.fetchone()
    print(f"  Long runs (9+ mi): {long_runs} ({total_gels or 0} gels, {total_carbs or 0}g carbs)")

    cur.execute("SELECT COUNT(*) FROM runs WHERE garmin_id IS NOT NULL")
    garmin_matched = cur.fetchone()[0]
    print(f"  Runs with Garmin data: {garmin_matched}")

    cur.execute("SELECT AVG(vo2max) FROM runs WHERE vo2max IS NOT NULL")
    avg_vo2 = cur.fetchone()[0]
    if avg_vo2:
        print(f"  Average VO2max: {avg_vo2:.1f}")

    conn.close()
    print()
    print("Done!")


if __name__ == "__main__":
    main()
