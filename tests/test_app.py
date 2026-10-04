import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import app


class DirectoryRouteTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True)
        self.client = app.app.test_client()
        self.supabase_env = patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "",
                "SUPABASE_ANON_KEY": "",
            },
        )
        self.supabase_env.start()

    def tearDown(self):
        self.supabase_env.stop()
        app.cached_supabase_client.cache_clear()

    def test_directory_loads_real_csv_and_shows_profiles(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Company profiles", response.data)
        self.assertIn(b"Aadvik Foods &amp; Products Pvt Ltd", response.data)
        self.assertIn(b"Showing 1\xe2\x80\x9325 of 1592 companies", response.data)

    def test_search_filters_companies_and_reports_result_count(self):
        response = self.client.get("/", query_string={"q": "Aadvik Foods"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Aadvik Foods &amp; Products Pvt Ltd", response.data)
        self.assertIn(b"Showing 1\xe2\x80\x931 of 1 companies", response.data)
        self.assertNotIn(b"Showing 1\xe2\x80\x9325 of 1592 companies", response.data)

    def test_page_query_is_clamped_to_available_pages(self):
        response = self.client.get("/", query_string={"page": 999})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Page 64 of 64", response.data)
        self.assertIn(b"Showing 1576\xe2\x80\x931592 of 1592 companies", response.data)

    def test_missing_csv_returns_clear_service_unavailable_page(self):
        with patch.object(app, "CSV_PATH", Path("missing-company-data.csv")):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Company data is unavailable", response.data)
        self.assertIn(b"missing-company-data.csv", response.data)

    def test_supabase_fetches_all_batches_and_maps_database_fields(self):
        database_record = {
            "company_name": "Aadvik Foods",
            "company_description": "Dairy ingredient supplier",
            **{
                column: ""
                for column in app.DATABASE_COLUMNS.values()
                if column not in {"company_name", "company_description"}
            },
        }
        supabase = MagicMock()
        query = supabase.table.return_value
        query.select.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.execute.side_effect = [
            SimpleNamespace(data=[database_record] * app.SUPABASE_PAGE_SIZE),
            SimpleNamespace(data=[database_record]),
        ]

        with (
            patch.dict(
                "os.environ",
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_ANON_KEY": "public-test-key",
                },
            ),
            patch.object(app, "create_client", return_value=supabase),
        ):
            companies = app.load_companies()

        self.assertEqual(len(companies), app.SUPABASE_PAGE_SIZE + 1)
        self.assertEqual(companies[0]["Company Name"], "Aadvik Foods")
        self.assertEqual(
            companies[0]["Company Description"],
            "Dairy ingredient supplier",
        )
        self.assertEqual(
            [call.args for call in query.range.call_args_list],
            [(0, 999), (1000, 1999)],
        )

    def test_partial_supabase_configuration_is_not_silently_ignored(self):
        with patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://example.supabase.co"},
        ):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Set both SUPABASE_URL and SUPABASE_ANON_KEY", response.data)


if __name__ == "__main__":
    unittest.main()
