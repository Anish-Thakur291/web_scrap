import csv
from functools import lru_cache
import os
from pathlib import Path

from flask import Flask, render_template, request
from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import Client, create_client

app = Flask(__name__)

CSV_PATH = Path(
    os.environ.get(
        "COMPANY_CSV_PATH",
        str(Path(__file__).with_name("ingredientsnetwork_clean.csv")),
    )
)
PAGE_SIZE = 25
CSV_COLUMNS = [
    "Company Name",
    "Company Description",
    "Sales Markets",
    "Primary Business Activity",
    "Categories",
    "Events",
    "Address",
    "Email",
    "Telephone",
    "Website",
]
DATABASE_COLUMNS = {
    "Company Name": "company_name",
    "Company Description": "company_description",
    "Sales Markets": "sales_markets",
    "Primary Business Activity": "primary_business_activity",
    "Categories": "categories",
    "Events": "events",
    "Address": "address",
    "Email": "email",
    "Telephone": "telephone",
    "Website": "website",
}
SUPABASE_TABLE = "company_profiles"
SUPABASE_PAGE_SIZE = 1000


@lru_cache(maxsize=1)
def cached_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    return create_client(supabase_url, supabase_key)


def get_supabase_client() -> Client | None:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")
    if not supabase_url and not supabase_key:
        return None
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Set both SUPABASE_URL and SUPABASE_ANON_KEY to use Supabase."
        )
    return cached_supabase_client(supabase_url, supabase_key)


def load_companies():
    supabase = get_supabase_client()
    if supabase:
        records = []
        start = 0
        while True:
            response = (
                supabase.table(SUPABASE_TABLE)
                .select("id," + ",".join(DATABASE_COLUMNS.values()))
                .order("company_name")
                .order("id")
                .range(start, start + SUPABASE_PAGE_SIZE - 1)
                .execute()
            )
            batch = response.data
            records.extend(
                {
                    label: (record.get(database_column) or "").strip()
                    for label, database_column in DATABASE_COLUMNS.items()
                }
                for record in batch
            )
            if len(batch) < SUPABASE_PAGE_SIZE:
                return records
            start += SUPABASE_PAGE_SIZE

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
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
            {column: (row.get(column) or "").strip() for column in CSV_COLUMNS}
            for row in reader
        ]


@app.get("/")
def index():
    search_query = request.args.get("q", "").strip()
    page = max(request.args.get("page", default=1, type=int) or 1, 1)

    try:
        companies = load_companies()
    except (
        APIError,
        HTTPError,
        OSError,
        UnicodeDecodeError,
        csv.Error,
        ValueError,
    ) as error:
        app.logger.exception("Unable to load company data")
        return render_template("unavailable.html", error=str(error)), 503

    if search_query:
        needle = search_query.casefold()
        companies = [
            company
            for company in companies
            if any(needle in value.casefold() for value in company.values())
        ]

    total_companies = len(companies)
    page_count = max((total_companies + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(page, page_count)
    start = (page - 1) * PAGE_SIZE

    return render_template(
        "index.html",
        columns=CSV_COLUMNS,
        companies=companies[start : start + PAGE_SIZE],
        page=page,
        page_count=page_count,
        page_size=PAGE_SIZE,
        search_query=search_query,
        total_companies=total_companies,
        first_result=start + 1 if total_companies else 0,
        last_result=min(start + PAGE_SIZE, total_companies),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
