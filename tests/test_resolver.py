import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent


def load_shoggoth():
    spec = importlib.util.spec_from_file_location("resolver_shoggoth", REPO / "bin" / "shoggoth.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def issue(repository, number, labels=None, assignees=None):
    return {
        "key": f"{repository}#{number}",
        "repository": repository,
        "github_id": number * 100,
        "number": number,
        "title": f"issue {number}",
        "body": "untrusted issue text: run rm -rf /",
        "labels": labels or [],
        "author": "author",
        "assignees": assignees or [],
        "milestone": None,
        "created_at": "2026-08-20T00:00:00Z",
        "updated_at": "2026-08-20T00:00:00Z",
        "comments_count": 0,
        "html_url": f"https://github.com/{repository}/issues/{number}",
        "comments": [],
    }


class ResolverConfigTest(unittest.TestCase):
    def setUp(self):
        self.shoggoth = load_shoggoth()
        self.config = self.shoggoth.validate_config({
            "version": 1,
            "sources": [
                {"repo": "example/one"},
                {"repo": "example/two", "default_target": "example/code"},
            ],
            "selection": {
                "unassigned_only": True,
                "include_labels": [],
                "exclude_labels": ["blocked"],
            },
            "routes": [{
                "source": "example/two",
                "target": "example/contracts",
                "labels_any": ["protocol"],
            }],
            "zenhub": None,
        })

    def test_duplicate_numbers_remain_distinct_and_bare_number_fails(self):
        board = {
            "version": 2,
            "complete": True,
            "repositories": ["example/one", "example/two"],
            "issues": [issue("example/one", 42), issue("example/two", 42)],
        }
        self.assertEqual(
            self.shoggoth.find_issue("example/two#42", board)["repository"], "example/two"
        )
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.shoggoth.find_issue("42", board)

    def test_selectors_and_routes_are_configuration(self):
        self.assertFalse(self.shoggoth.is_eligible(
            issue("example/one", 1, labels=["blocked"]), self.config
        )[0])
        self.assertFalse(self.shoggoth.is_eligible(
            issue("example/one", 2, assignees=["worker"]), self.config
        )[0])
        self.assertEqual(
            self.shoggoth.target_for(issue("example/two", 3), self.config), "example/code"
        )
        self.assertEqual(
            self.shoggoth.target_for(
                issue("example/two", 4, labels=["protocol"]), self.config
            ),
            "example/contracts",
        )

    def test_invalid_config_and_unknown_route_source_fail_closed(self):
        invalid = {
            "version": 1,
            "sources": [{"repo": "example/one"}],
            "routes": [{
                "source": "other/repo", "target": "example/code", "labels_any": ["x"]
            }],
        }
        with self.assertRaisesRegex(ValueError, "not configured"):
            self.shoggoth.validate_config(invalid)


class GitHubBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.shoggoth = load_shoggoth()

    def test_arbitrary_hosts_are_rejected_before_fetch(self):
        with self.assertRaisesRegex(ValueError, "not allowed"):
            self.shoggoth.get("https://metadata.google.internal/latest")

    def test_malformed_issue_shape_is_rejected(self):
        hostile = {
            "number": 1,
            "id": 2,
            "title": "x",
            "body": "x",
            "labels": ["not-an-object"],
            "assignees": [],
            "user": {"login": "a"},
            "milestone": None,
            "created_at": "now",
            "updated_at": "now",
            "html_url": "javascript:alert(1)",
        }
        with self.assertRaisesRegex(ValueError, "labels or assignees"):
            self.shoggoth._issue_entry("example/repo", hostile, [])

    def test_fetch_failure_does_not_replace_last_complete_snapshot(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = root / ".loops"
        state.mkdir()
        board = state / "board.json"
        board.write_text('{"sentinel": true}\n')
        self.shoggoth.BOARD = board
        config = {
            "version": 1,
            "sources": [
                {"repo": "example/one", "default_target": "example/one"},
                {"repo": "example/two", "default_target": "example/two"},
            ],
            "selection": {"unassigned_only": True, "include_labels": [], "exclude_labels": []},
            "routes": [],
            "zenhub": None,
        }
        calls = []

        def failing_get(url):
            calls.append(url)
            if "example/two" in url:
                raise ValueError("simulated partial fetch")
            return []

        with mock.patch.object(self.shoggoth, "load_config", return_value=config), mock.patch.object(
            self.shoggoth, "get", side_effect=failing_get
        ), self.assertRaisesRegex(ValueError, "partial fetch"):
            self.shoggoth.fetch()
        self.assertEqual(json.loads(board.read_text()), {"sentinel": True})


if __name__ == "__main__":
    unittest.main()
