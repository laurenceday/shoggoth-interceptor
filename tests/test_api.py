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
        (root / ".loops").mkdir()
        for name in ("board.json", "pipelines.json", "excluded.json"):
            (root / ".loops" / name).write_text((FIXTURES / name).read_text())
        (root / ".loops" / "deliverables" / "issue-789").mkdir(parents=True)
        (root / ".loops" / "deliverables" / "issue-789" / "SUMMARY.md").write_text("done")
        (root / ".loops" / "deliverables" / "loop-1-ranking.md").write_text("# ranking")
        self.api = self.console.Api(root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_roster_keeps_optional_pipeline_metadata_without_filtering(self):
        roster = self.api.roster()
        pipes = {row["pipeline"] for row in roster["candidates"]}
        self.assertEqual(pipes, {"Icebox", "Product Backlog", "New Issues"})

    def test_roster_reports_the_repositories_present_among_candidates(self):
        """The console's repository filter is built from this list.

        It reports what the candidates actually contain rather than every
        configured source, because a source whose issues are all excluded or
        assigned would otherwise offer a filter option that selects nothing.
        """
        roster = self.api.roster()
        repositories = roster["repositories"]
        self.assertEqual(repositories, sorted(set(repositories)))
        self.assertEqual(
            set(repositories),
            {row["repository"] for row in roster["candidates"]},
        )

    def test_rankings_shows_ranking_documents_and_not_loop_notes(self):
        """`deliverables/` also holds briefs and notes.

        Those stay on disk as the archive of what a loop decided; the panel
        answers what was ranked, and a brief listed beside a ranking reads as
        though it were one.
        """
        (Path(self.api.deliverables) / "loop-2-ranking.md").write_text("# second")
        (Path(self.api.deliverables) / "gate-widening-brief.md").write_text("# a note")
        names = [doc["name"] for doc in self.api.rankings()]
        self.assertIn("loop-1-ranking.md", names)
        self.assertIn("loop-2-ranking.md", names)
        self.assertNotIn("gate-widening-brief.md", names)

    def test_roster_attributes_exclusions_to_their_repository(self):
        """A filtered console needs the count for the repository on screen."""
        roster = self.api.roster()
        by_repo = roster["excluded_by_repository"]
        self.assertEqual(sum(by_repo.values()), roster["excluded_count"])
        for repo in by_repo:
            self.assertEqual(repo, repo.lower())
            self.assertIn("/", repo)

    def test_roster_masks_excluded(self):
        numbers = [row["number"] for row in self.api.roster()["candidates"]]
        self.assertNotIn(606, numbers)   # excluded in fixture
        self.assertIn(789, numbers)

    def test_roster_does_not_require_zenhub_scope(self):
        numbers = [row["number"] for row in self.api.roster()["candidates"]]
        self.assertIn(858, numbers)

    def test_roster_applies_configured_label_selection(self):
        config = Path(self.tmp.name) / "config"
        config.mkdir()
        (config / "resolver.json").write_text(json.dumps({
            "selection": {
                "unassigned_only": True,
                "include_labels": [],
                "exclude_labels": ["Improvement"],
            }
        }))
        numbers = [row["number"] for row in self.api.roster()["candidates"]]
        self.assertNotIn(608, numbers)

    def test_issue_detail_carries_pipeline_and_deliverables(self):
        issue = self.api.issue("wildcat-finance/product#789")
        self.assertEqual(issue["pipeline"], "Product Backlog")
        self.assertEqual(issue["deliverables"], ["SUMMARY.md"])
        self.assertEqual(issue["comments"][0]["author"], "andfletcher")

    def test_unknown_issue_is_none(self):
        self.assertIsNone(self.api.issue("wildcat-finance/product#999999"))

    def test_rankings_lists_top_level_docs_only(self):
        names = [d["name"] for d in self.api.rankings()]
        self.assertEqual(names, ["loop-1-ranking.md"])

    def test_health_reports_state_ages(self):
        ages = self.api.health()["state_age_seconds"]
        self.assertIsNotNone(ages["board.json"])

    def test_no_secret_material_in_responses(self):
        blob = json.dumps([
            self.api.roster(), self.api.issue("wildcat-finance/product#789"), self.api.health()
        ])
        for marker in (
            "GITHUB_READ_PAT",
            "GITHUB_ISSUE_REPLY_PAT",
            "WILDCAT_ZENHUB_READ_ONLY_PAT",
            "ZENHUB_API_KEY",
            "github_pat",
        ):
            self.assertNotIn(marker, blob)

    def test_deliverables_path_is_number_bound(self):
        self.assertEqual(self.api.deliverable_files("wildcat-finance/product#123"), [])
        with self.assertRaises(ValueError):
            self.api.deliverable_files("../../etc")

    def test_repository_identity_distinguishes_duplicate_numbers(self):
        board_path = Path(self.tmp.name) / ".loops" / "board.json"
        board = json.loads(board_path.read_text())
        duplicate = dict(board["issues"][0])
        duplicate["title"] = "same number, another repository"
        duplicate["html_url"] = "https://github.com/example/other/issues/789"
        board["version"] = 2
        board["complete"] = True
        board["repositories"] = ["wildcat-finance/product", "example/other"]
        for issue in board["issues"]:
            issue["repository"] = "wildcat-finance/product"
            issue["key"] = f"wildcat-finance/product#{issue['number']}"
        duplicate["repository"] = "example/other"
        duplicate["key"] = "example/other#789"
        board["issues"].append(duplicate)
        board_path.write_text(json.dumps(board))

        self.assertEqual(self.api.issue("example/other#789")["repository"], "example/other")
        keys = {row["key"] for row in self.api.roster()["candidates"]}
        self.assertIn("example/other#789", keys)
        self.assertIn("wildcat-finance/product#789", keys)


if __name__ == "__main__":
    unittest.main()
