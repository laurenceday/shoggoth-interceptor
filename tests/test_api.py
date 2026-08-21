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

    def test_launch_list_reports_enough_log_to_watch_a_run(self):
        """The console polls this while a loop runs.

        A 2,000-character window truncated the first real run at 3,861, so a
        reader watching live saw its last gasp rather than its progress. The
        list also says how big the log really is and whether it was cut, so a
        tail cannot be mistaken for the whole thing.
        """
        root = Path(self.tmp.name)
        runs = root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "loop-1.log").write_text("x" * 5000)
        launches = self.console.Launcher(root).list()
        self.assertEqual(len(launches), 1)
        entry = launches[0]
        self.assertEqual(entry["size"], 5000)
        self.assertFalse(entry["truncated"])
        self.assertEqual(len(entry["log_tail"]), 5000)

    def test_launch_list_marks_a_log_it_had_to_cut(self):
        root = Path(self.tmp.name)
        runs = root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        oversized = self.console.LOG_TAIL_CHARS + 500
        (runs / "loop-2.log").write_text("y" * oversized)
        entry = self.console.Launcher(root).list()[0]
        self.assertEqual(entry["size"], oversized)
        self.assertTrue(entry["truncated"])
        self.assertEqual(len(entry["log_tail"]), self.console.LOG_TAIL_CHARS)

    def _run(self, name, argv):
        """Spawn through the real detached path and wait for its status."""
        import time
        root = Path(self.tmp.name)
        runs = root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        launcher = self.console.Launcher(root)
        log = runs / (name + ".log")
        (runs / (name + ".pid")).write_text(str(launcher._spawn_detached(argv, log)))
        for _ in range(100):
            if log.with_suffix(".status").exists():
                break
            time.sleep(0.05)
        return launcher

    def test_a_failing_run_is_recorded_as_failed_with_its_exit_code(self):
        """The console never waits on the child, so the run records itself."""
        launcher = self._run("boom", ["/bin/sh", "-c", "echo it broke >&2; exit 3"])
        entry = next(e for e in launcher.list() if e["name"] == "boom")
        self.assertEqual(entry["outcome"], "failed")
        self.assertEqual(entry["exit_code"], 3)
        self.assertIn("it broke", entry["log_tail"])

    def test_a_recorded_status_outranks_a_live_looking_pid(self):
        """A finished child is a zombie the console never reaps, so its pid
        still answers `kill -0`. Without this the run reads as running for as
        long as the console stays up."""
        launcher = self._run("fine", ["/bin/sh", "-c", "echo done"])
        entry = next(e for e in launcher.list() if e["name"] == "fine")
        self.assertEqual(entry["outcome"], "succeeded")
        self.assertEqual(entry["exit_code"], 0)
        self.assertFalse(entry["running"])

    def test_a_run_with_no_status_is_unknown_rather_than_passed(self):
        root = Path(self.tmp.name)
        runs = root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "orphan.log").write_text("started and vanished")
        entry = next(e for e in self.console.Launcher(root).list()
                     if e["name"] == "orphan")
        self.assertEqual(entry["outcome"], "unknown")
        self.assertIsNone(entry["exit_code"])

    def test_rankings_shows_only_the_latest_ranking(self):
        """One ranking, not a stack of dropdowns for loops long finished.

        Earlier rankings and any loop notes stay in `deliverables/` as the
        archive of what each loop decided. The panel answers what the current
        loop ranked, so a brief or a superseded ranking listed beside it reads
        as though it were that.
        """
        import os
        older = Path(self.api.deliverables) / "loop-1-ranking.md"
        newer = Path(self.api.deliverables) / "loop-2-ranking.md"
        note = Path(self.api.deliverables) / "gate-widening-brief.md"
        newer.write_text("# second")
        note.write_text("# a note")
        os.utime(older, (1, 1))
        os.utime(note, (10 ** 9, 10 ** 9))
        docs = self.api.rankings()
        self.assertEqual([doc["name"] for doc in docs], ["loop-2-ranking.md"])
        self.assertEqual(docs[0]["text"], "# second")

    def test_rankings_is_empty_when_no_loop_has_ranked(self):
        for path in Path(self.api.deliverables).glob("*.md"):
            path.unlink()
        self.assertEqual(self.api.rankings(), [])

    def test_roster_attributes_exclusions_to_their_repository(self):
        """A filtered console needs the count for the repository on screen."""
        roster = self.api.roster()
        by_repo = roster["excluded_by_repository"]
        self.assertEqual(sum(by_repo.values()), roster["excluded_count"])
        for repo in by_repo:
            self.assertEqual(repo, repo.lower())
            self.assertIn("/", repo)

    def test_default_order_follows_the_board_then_the_number(self):
        """Sorting by title read as random to anyone who had ordered the issues.

        Five playground tickets filed one to five came back 5, 2, 3, 1, 4,
        because their titles happened to sort that way.
        """
        rows = self.api.roster()["candidates"]
        by_repo = {}
        for row in rows:
            by_repo.setdefault(row["repository"], []).append(row)
        for repo, group in by_repo.items():
            ranked = [r for r in group if r["position"] is not None]
            unranked = [r for r in group if r["position"] is None]
            with self.subTest(repository=repo):
                # Ranked ones come first, in board order.
                self.assertEqual(group[:len(ranked)], ranked)
                self.assertEqual([r["position"] for r in ranked],
                                 sorted(r["position"] for r in ranked))
                # Then the rest, by number.
                self.assertEqual([r["number"] for r in unranked],
                                 sorted(r["number"] for r in unranked))

    def test_roster_carries_the_board_category_and_position(self):
        """The console shows both as columns and filters on the category."""
        roster = self.api.roster()
        rows = {row["key"]: row for row in roster["candidates"]}
        self.assertTrue(rows)
        for row in rows.values():
            self.assertIn("pipeline", row)
            self.assertIn("position", row)
        self.assertEqual(roster["pipelines"],
                         sorted({row["pipeline"] for row in rows.values() if row["pipeline"]}))

    def test_an_unranked_issue_has_no_position_rather_than_zero(self):
        """Absent is not zero.

        An issue outside the ZenHub workspace, or in a repository that is not a
        configured source, has no rank at all. Writing it as 0 would sort it
        above the issue the board actually ranked first.
        """
        path = Path(self.tmp.name) / ".loops" / "board.json"
        board = json.loads(path.read_text())
        issues = board["issues"] if isinstance(board, dict) else board
        # The fixture is the older single-repository shape, so `repository` and
        # `key` are added by normalisation rather than carried on the issue.
        unknown = dict(issues[0])
        unknown["number"] = 999999
        unknown["assignees"] = []
        unknown["labels"] = []
        issues.append(unknown)
        path.write_text(json.dumps(board))
        row = next(r for r in self.api.roster()["candidates"] if r["number"] == 999999)
        self.assertIsNone(row["position"])
        self.assertIsNone(row["pipeline"])

    def test_an_issue_with_an_open_pull_request_trail_is_not_a_candidate(self):
        """CLAUDE.md rule (c), the half that was only ever prose.

        Assignment was mechanised and "its branch or pull request trail shows
        that someone is already working on it" was not, so a Fiat run in
        flight kept being offered its own issue: the branch is slugged from the
        title and carries no number, and the operator had not assigned it.
        """
        path = Path(self.tmp.name) / ".loops" / "board.json"
        board = json.loads(path.read_text())
        issues = board["issues"] if isinstance(board, dict) else board
        target = issues[0]
        key = f"{board.get('repo')}#{target['number']}".lower()
        before = [r["number"] for r in self.api.roster()["candidates"]]
        self.assertIn(target["number"], before)
        board["in_flight"] = {key: [4321]}
        path.write_text(json.dumps(board))
        roster = self.api.roster()
        self.assertNotIn(target["number"], [r["number"] for r in roster["candidates"]])
        self.assertEqual(roster["in_flight_count"], 1)

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
