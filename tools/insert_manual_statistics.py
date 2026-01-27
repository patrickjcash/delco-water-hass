#!/usr/bin/env python3
"""
Manual statistics insertion tool for Del-Co Water.

Use this script to manually insert historical usage/cost data that
couldn't be retrieved from PDFs (e.g., old bills not available).

Usage:
    python insert_manual_statistics.py

The script will prompt you for the data and generate SQL statements
that you can run against your Home Assistant database.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def parse_date(date_str: str) -> datetime:
    """Parse date in MM/DD/YY format."""
    return datetime.strptime(date_str, "%m/%d/%y").replace(
        hour=12, minute=0, second=0, tzinfo=timezone.utc
    )


def generate_sql_for_statistics(
    db_path: str | None = None,
    consumption_statistic_id: str = "delco_water:consumption",
    cost_statistic_id: str = "delco_water:cost",
):
    """Generate SQL statements for inserting manual statistics."""

    print("=" * 60)
    print("Del-Co Water Manual Statistics Insertion Tool")
    print("=" * 60)
    print()
    print("This tool helps you insert missing historical data.")
    print("You'll need to provide the service_to date, usage, and cost")
    print("for each billing period you want to add.")
    print()

    # Collect entries
    entries = []

    while True:
        print("-" * 40)
        date_str = input("Service TO date (MM/DD/YY) or 'done': ").strip()

        if date_str.lower() == 'done':
            break

        try:
            service_date = parse_date(date_str)
        except ValueError:
            print("Invalid date format. Use MM/DD/YY (e.g., 01/31/25)")
            continue

        try:
            usage_gallons = float(input("Usage in gallons: ").strip().replace(",", ""))
        except ValueError:
            print("Invalid number")
            continue

        try:
            cost = float(input("Cost in USD: ").strip().replace("$", "").replace(",", ""))
        except ValueError:
            print("Invalid number")
            continue

        entries.append({
            "date": service_date,
            "date_str": date_str,
            "usage_gallons": usage_gallons,
            "cost": cost,
        })

        print(f"  Added: {date_str} - {usage_gallons:,.0f} gal, ${cost:.2f}")

    if not entries:
        print("No entries to insert.")
        return

    # Sort by date
    entries.sort(key=lambda x: x["date"])

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"{'Date':<15} {'Usage (gal)':<15} {'Cost':<12}")
    print("-" * 42)
    for e in entries:
        print(f"{e['date_str']:<15} {e['usage_gallons']:>12,.0f}   ${e['cost']:>8.2f}")

    print()
    print("=" * 60)
    print("SQL STATEMENTS")
    print("=" * 60)
    print()
    print("-- First, find your metadata IDs:")
    print("SELECT id, statistic_id FROM statistics_meta WHERE statistic_id LIKE 'delco_water%';")
    print()
    print("-- Replace <CONSUMPTION_META_ID> and <COST_META_ID> with actual IDs from above query")
    print()
    print("-- IMPORTANT: You need to calculate cumulative sums correctly!")
    print("-- First, find the last sum values:")
    print(f"-- SELECT sum FROM statistics WHERE metadata_id = <CONSUMPTION_META_ID> ORDER BY start_ts DESC LIMIT 1;")
    print(f"-- SELECT sum FROM statistics WHERE metadata_id = <COST_META_ID> ORDER BY start_ts DESC LIMIT 1;")
    print()

    consumption_sum = float(input("Enter current consumption sum (or 0 if starting fresh): ") or "0")
    cost_sum = float(input("Enter current cost sum (or 0 if starting fresh): ") or "0")

    print()
    print("-- Run these SQL statements in your HA database:")
    print("-- sqlite3 /config/home-assistant_v2.db")
    print()

    for e in entries:
        timestamp = int(e["date"].timestamp())
        consumption_sum += e["usage_gallons"]
        cost_sum += e["cost"]

        print(f"-- {e['date_str']}: {e['usage_gallons']:,.0f} gal, ${e['cost']:.2f}")
        print(f"INSERT INTO statistics (created_ts, start_ts, metadata_id, state, sum)")
        print(f"VALUES ({int(datetime.now().timestamp())}, {timestamp}, <CONSUMPTION_META_ID>, {e['usage_gallons']}, {consumption_sum});")
        print()
        print(f"INSERT INTO statistics (created_ts, start_ts, metadata_id, state, sum)")
        print(f"VALUES ({int(datetime.now().timestamp())}, {timestamp}, <COST_META_ID>, {e['cost']}, {cost_sum});")
        print()

    print("-- After inserting, restart Home Assistant to see the changes.")

    # Optionally write to a file
    output_file = Path("manual_statistics.sql")
    if input(f"\nSave SQL to {output_file}? (y/n): ").lower() == 'y':
        with open(output_file, "w") as f:
            f.write("-- Del-Co Water Manual Statistics Insertion\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")

            consumption_sum_reset = float(input("Re-enter starting consumption sum: ") or "0")
            cost_sum_reset = float(input("Re-enter starting cost sum: ") or "0")

            consumption_sum = consumption_sum_reset
            cost_sum = cost_sum_reset

            for e in entries:
                timestamp = int(e["date"].timestamp())
                consumption_sum += e["usage_gallons"]
                cost_sum += e["cost"]

                f.write(f"-- {e['date_str']}: {e['usage_gallons']:,.0f} gal, ${e['cost']:.2f}\n")
                f.write(f"INSERT INTO statistics (created_ts, start_ts, metadata_id, state, sum)\n")
                f.write(f"VALUES ({int(datetime.now().timestamp())}, {timestamp}, <CONSUMPTION_META_ID>, {e['usage_gallons']}, {consumption_sum});\n\n")
                f.write(f"INSERT INTO statistics (created_ts, start_ts, metadata_id, state, sum)\n")
                f.write(f"VALUES ({int(datetime.now().timestamp())}, {timestamp}, <COST_META_ID>, {e['cost']}, {cost_sum});\n\n")

        print(f"Saved to {output_file}")


if __name__ == "__main__":
    generate_sql_for_statistics()
