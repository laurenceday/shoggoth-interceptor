import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_console():
    spec = importlib.util.spec_from_file_location("console", REPO / "bin" / "console.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.console = load_console()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "state").mkdir()
        for name in ("board.json", "pipelines.json", "excluded.json"):
            (root / "state" / name).write_text((FIXTURES / name).read_text())
        (root / "deliverables" / "issue-789").mkdir(parents=True)
        (root / "deliverables" / "issue-789" / "SUMMARY.md").write_text("done")
        (root / "deliverables" / "loop-1-ranking.md").write_text("# ranking")
        self.api = self.console.Api(root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_roster_defaults_to_scope_pipelines(self):
        roster = self.api.roster()
        pipes = {row["pipeline"] for row in roster["candidates"]}
        self.assertEqual(pipes, {"Icebox", "Product Backlog"})

    def test_roster_masks_excluded(self):
        numbers = [row["number"] for row in self.api.roster()["candidates"]]
        self.assertNotIn(606, numbers)   # excluded in fixture
        self.assertIn(789, numbers)

    def test_roster_omits_out_of_scope_pipeline(self):
        numbers = [row["number"] for row in self.api.roster()["candidates"]]
        self.assertNotIn(858, numbers)   # New Issues in fixture

    def test_issue_detail_carries_pipeline_and_deliverables(self):
        issue = self.api.issue(789)
        self.assertEqual(issue["pipeline"], "Product Backlog")
        self.assertEqual(issue["deliverables"], ["SUMMARY.md"])
        self.assertEqual(issue["comments"][0]["author"], "andfletcher")

    def test_unknown_issue_is_none(self):
        self.assertIsNone(self.api.issue(999999))

    def test_rankings_lists_top_level_docs_only(self):
        names = [d["name"] for d in self.api.rankings()]
        self.assertEqual(names, ["loop-1-ranking.md"])

    def test_health_reports_state_ages(self):
        ages = self.api.health()["state_age_seconds"]
        self.assertIsNotNone(ages["board.json"])

    def test_no_secret_material_in_responses(self):
        blob = json.dumps([self.api.roster(), self.api.issue(789), self.api.health()])
        for marker in ("WILDCAT_ZENHUB_READ_ONLY_PAT", "ZENHUB_API_KEY", "github_pat"):
            self.assertNotIn(marker, blob)

    def test_deliverables_path_is_number_bound(self):
        self.assertEqual(self.api.deliverable_files(123), [])
        with self.assertRaises(ValueError):
            self.api.deliverable_files("../../etc")


if __name__ == "__main__":
    unittest.main()
