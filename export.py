#!/usr/bin/env python3
"""
Export running dashboard data to various formats and destinations.

Usage:
  python3 export.py csv                     # Export to CSV files
  python3 export.py json                    # Export to JSON files
  python3 export.py parquet                 # Export to Parquet files
  python3 export.py s3 s3://bucket/prefix   # Upload to S3
  python3 export.py cribl https://endpoint  # Send to Cribl

Options:
  --format FORMAT    Output format: csv, json, ndjson, parquet (default: csv)
  --tables TABLES    Comma-separated tables (default: runs,sleep,run_with_sleep)
  --output DIR       Output directory (default: ./export)
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "running_dashboard.db"
DEFAULT_TABLES = ["runs", "sleep", "run_with_sleep"]


def get_connection():
    """Get SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def export_csv(output_dir: Path, tables: list[str]):
    """Export tables to CSV files."""
    import csv

    conn = get_connection()
    output_dir.mkdir(parents=True, exist_ok=True)

    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        filepath = output_dir / f"{table}.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())  # Header
            writer.writerows(rows)

        print(f"  {table}.csv ({len(rows)} rows)")

    conn.close()


def export_json(output_dir: Path, tables: list[str], ndjson: bool = False):
    """Export tables to JSON or NDJSON files."""
    conn = get_connection()
    output_dir.mkdir(parents=True, exist_ok=True)

    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]

        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        ext = "ndjson" if ndjson else "json"
        filepath = output_dir / f"{table}.{ext}"

        with open(filepath, "w") as f:
            if ndjson:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
            else:
                json.dump(rows, f, indent=2)

        print(f"  {table}.{ext} ({len(rows)} rows)")

    conn.close()


def export_parquet(output_dir: Path, tables: list[str]):
    """Export tables to Parquet files."""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas required. Install with: pip install pandas pyarrow")
        sys.exit(1)

    conn = get_connection()
    output_dir.mkdir(parents=True, exist_ok=True)

    for table in tables:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)

        if df.empty:
            print(f"  {table}: empty, skipping")
            continue

        filepath = output_dir / f"{table}.parquet"
        df.to_parquet(filepath, index=False)

        print(f"  {table}.parquet ({len(df)} rows)")

    conn.close()


def upload_s3(s3_path: str, output_dir: Path, fmt: str):
    """Upload exported files to S3."""
    try:
        import boto3
    except ImportError:
        print("Error: boto3 required. Install with: pip install boto3")
        sys.exit(1)

    # Parse s3://bucket/prefix
    if not s3_path.startswith("s3://"):
        print("Error: S3 path must start with s3://")
        sys.exit(1)

    parts = s3_path[5:].split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""

    s3 = boto3.client("s3")

    ext_map = {"csv": ".csv", "json": ".json", "ndjson": ".ndjson", "parquet": ".parquet"}
    ext = ext_map.get(fmt, ".csv")

    for filepath in output_dir.glob(f"*{ext}"):
        key = f"{prefix}/{filepath.name}" if prefix else filepath.name
        s3.upload_file(str(filepath), bucket, key)
        print(f"  Uploaded: s3://{bucket}/{key}")


def send_cribl(endpoint: str, tables: list[str], token: str = None):
    """Send data to Cribl Stream/Lake via HTTP."""
    try:
        import requests
    except ImportError:
        print("Error: requests required. Install with: pip install requests")
        sys.exit(1)

    conn = get_connection()

    headers = {"Content-Type": "application/x-ndjson"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]

        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        # Add metadata to each event
        events = []
        for row in rows:
            row["_sourcetype"] = "running_data"
            row["_source"] = table
            events.append(json.dumps(row))

        payload = "\n".join(events)

        try:
            response = requests.post(endpoint, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            print(f"  {table}: sent {len(rows)} events ({response.status_code})")
        except requests.RequestException as e:
            print(f"  {table}: failed - {e}")

    conn.close()


def send_cribl_hec(endpoint: str, tables: list[str], token: str):
    """Send data to Cribl via HEC (Splunk-compatible) endpoint."""
    try:
        import requests
    except ImportError:
        print("Error: requests required. Install with: pip install requests")
        sys.exit(1)

    conn = get_connection()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Splunk {token}"
    }

    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]

        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        # HEC format
        events = []
        for row in rows:
            events.append({
                "event": row,
                "sourcetype": "running_data",
                "source": table
            })

        try:
            response = requests.post(endpoint, headers=headers, json=events, timeout=30)
            response.raise_for_status()
            print(f"  {table}: sent {len(rows)} events ({response.status_code})")
        except requests.RequestException as e:
            print(f"  {table}: failed - {e}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export running dashboard data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 export.py csv
  python3 export.py parquet
  python3 export.py s3 s3://my-bucket/running --format parquet
  python3 export.py cribl https://cribl.example.com:9997/ingest --token $TOKEN
  python3 export.py cribl-hec https://cribl:8088/services/collector/event --token $TOKEN
        """
    )

    parser.add_argument("command", choices=["csv", "json", "ndjson", "parquet", "s3", "cribl", "cribl-hec"],
                        help="Export command")
    parser.add_argument("destination", nargs="?", default=None,
                        help="Destination (S3 path or Cribl endpoint)")
    parser.add_argument("--format", "-f", default="csv", choices=["csv", "json", "ndjson", "parquet"],
                        help="Output format for S3 upload (default: csv)")
    parser.add_argument("--tables", "-t", default=",".join(DEFAULT_TABLES),
                        help="Comma-separated table names")
    parser.add_argument("--output", "-o", default="./export",
                        help="Output directory (default: ./export)")
    parser.add_argument("--token", default=os.environ.get("CRIBL_TOKEN"),
                        help="Auth token for Cribl (or set CRIBL_TOKEN env var)")

    args = parser.parse_args()
    tables = [t.strip() for t in args.tables.split(",")]
    output_dir = Path(args.output)

    print(f"Database: {DB_PATH}")
    print(f"Tables: {', '.join(tables)}")
    print()

    if args.command == "csv":
        print("Exporting to CSV...")
        export_csv(output_dir, tables)

    elif args.command == "json":
        print("Exporting to JSON...")
        export_json(output_dir, tables, ndjson=False)

    elif args.command == "ndjson":
        print("Exporting to NDJSON...")
        export_json(output_dir, tables, ndjson=True)

    elif args.command == "parquet":
        print("Exporting to Parquet...")
        export_parquet(output_dir, tables)

    elif args.command == "s3":
        if not args.destination:
            print("Error: S3 path required (e.g., s3://bucket/prefix)")
            sys.exit(1)

        print(f"Exporting to {args.format.upper()}...")
        if args.format == "csv":
            export_csv(output_dir, tables)
        elif args.format == "json":
            export_json(output_dir, tables)
        elif args.format == "ndjson":
            export_json(output_dir, tables, ndjson=True)
        elif args.format == "parquet":
            export_parquet(output_dir, tables)

        print(f"\nUploading to {args.destination}...")
        upload_s3(args.destination, output_dir, args.format)

    elif args.command == "cribl":
        if not args.destination:
            print("Error: Cribl endpoint required")
            sys.exit(1)

        print(f"Sending to Cribl: {args.destination}")
        send_cribl(args.destination, tables, args.token)

    elif args.command == "cribl-hec":
        if not args.destination:
            print("Error: Cribl HEC endpoint required")
            sys.exit(1)
        if not args.token:
            print("Error: Token required for HEC (use --token or CRIBL_TOKEN env var)")
            sys.exit(1)

        print(f"Sending to Cribl HEC: {args.destination}")
        send_cribl_hec(args.destination, tables, args.token)

    print("\nDone!")


if __name__ == "__main__":
    main()
