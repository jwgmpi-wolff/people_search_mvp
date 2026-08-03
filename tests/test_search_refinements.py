import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("people_search_entrypoint", ROOT / "app.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SearchRefinementTests(unittest.TestCase):
    def test_search_applies_all_refinements_to_provider_query(self):
        candidates = [
            {
                "title": "Zoe Adams - Profile",
                "url": "https://example.test/zoe",
                "snippet": "",
                "source": "test",
            }
        ]

        enriched = [
            {
                **candidates[0],
                "score": 1,
                "record": {
                    "name": "Zoe Adams",
                    "summary": "Extracted public record.",
                    "fields": [{"label": "Record ID", "value": "ABC-123"}],
                    "source_name": "example.test",
                    "extraction": "page",
                },
            }
        ]
        with MODULE.app.test_client() as client, patch.object(
            MODULE, "fetch_results", return_value=(candidates, [])
        ) as fetch_results, patch.object(
            MODULE, "enrich_search_results", return_value=enriched
        ):
            response = client.post(
                "/search",
                data={
                    "query": "software engineer",
                    "entity": "public",
                    "source": "public_records",
                    "country": "United States",
                    "state": "Washington",
                    "county": "King County",
                    "city": "Seattle",
                    "public_record_type": "assessor",
                    "social_media_site": "linkedin",
                    "sort_by": "last_name",
                    "max_results": "75",
                },
            )

        self.assertEqual(response.status_code, 200)
        launched_query = fetch_results.call_args.args[1]
        for expected in (
            "public profile",
            "Seattle",
            "King County",
            "Washington",
            "United States",
            "county assessor",
            "site:.gov",
            "site:linkedin.com",
        ):
            self.assertIn(expected, launched_query)
        self.assertEqual(
            response.get_json()["results"][0]["record"]["fields"][0]["value"],
            "ABC-123",
        )
        self.assertNotIn("url", response.get_json()["results"][0])
        self.assertEqual(fetch_results.call_args.args[2], 75)

    def test_extracts_structured_data_from_record_page(self):
        html = """
        <html><head>
          <script type="application/ld+json">
            {"@type":"Person","name":"Jane Doe","jobTitle":"Engineer","description":"Public profile details."}
          </script>
        </head><body>
          <table><tr><th>Record ID</th><td>ABC-123</td></tr></table>
        </body></html>
        """

        record = MODULE.extract_record_from_html(
            html,
            {
                "title": "Jane Doe - Profile",
                "url": "https://records.example.gov/jane",
                "snippet": "Excerpt",
            },
        )

        self.assertEqual(record["name"], "Jane Doe")
        self.assertEqual(record["summary"], "Public profile details.")
        self.assertIn({"label": "Occupation", "value": "Engineer"}, record["fields"])
        self.assertIn({"label": "Record ID", "value": "ABC-123"}, record["fields"])

    def test_results_can_sort_by_first_or_last_name(self):
        results = [
            {"title": "Zoe Adams - Profile", "score": 2},
            {"title": "Amy Young - Profile", "score": 5},
        ]

        by_first = MODULE.sort_search_results(results, "first_name")
        by_last = MODULE.sort_search_results(results, "last_name")

        self.assertEqual(
            [item["title"] for item in by_first],
            ["Amy Young - Profile", "Zoe Adams - Profile"],
        )
        self.assertEqual(
            [item["title"] for item in by_last],
            ["Zoe Adams - Profile", "Amy Young - Profile"],
        )

    def test_home_page_exposes_refinement_dropdowns(self):
        with MODULE.app.test_client() as client:
            html = client.get("/").get_data(as_text=True)

        for field_name in (
            "public_record_type",
            "social_media_site",
            "country",
            "state",
            "county",
            "city",
            "sort_by",
        ):
            self.assertIn(f'name="{field_name}"', html)
        self.assertNotIn("Open source", html)
        self.assertIn("record.fields", html)
        self.assertIn('name="max_results" type="number" min="5" max="100" value="25"', html)


if __name__ == "__main__":
    unittest.main()