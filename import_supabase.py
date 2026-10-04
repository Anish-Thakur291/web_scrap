import argparse
import csv
import os
from pathlib import Path

from supabase import create_client

from app import CSV_COLUMNS, DATABASE_COLUMNS

DEFAULT_CSV_PATH = Path(__file__).with_name("ingredientsnetwork_clean.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = [
            column
            for column in CSV_COLUMNS
            if column not in (reader.fieldnames or [])
        ]
        if missing_columns:
            raise ValueError(
                "The company CSV is missing required columns: "
                + ", ".join(missing_columns)
            )
        return [
            {
                database_column: (record.get(label) or "").strip()
                for label, database_column in DATABASE_COLUMNS.items()
            }
            for record in reader
        ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace Supabase company profiles with the cleaned CSV."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="CSV to import (defaults to ingredientsnetwork_clean.csv)",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise SystemExit(
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before importing."
        )

    records = read_csv(args.csv_path)
    if not records:
        raise ValueError("Refusing to replace the company table with an empty CSV.")

    supabase = create_client(supabase_url, service_key)
    result = supabase.rpc(
        "replace_company_profiles",
        {"profiles": records},
    ).execute()
    if result.data != len(records):
        raise RuntimeError(
            f"Supabase reported importing {result.data!r} records; "
            f"expected {len(records)}."
        )
    print(f"Imported {result.data} company profiles into Supabase.")


if __name__ == "__main__":
    main()
