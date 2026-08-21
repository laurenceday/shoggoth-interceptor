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

        def failing_get(url, token=None):
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


class PipelinePositionTests(unittest.TestCase):
    """Board rank is recorded as data, not left to dict insertion order.

    The rank existed before this: `json.dump` wrote keys in the order the
    pipeline pages were walked, so the order survived by accident and nothing
    read it. Anything that reloaded, merged or re-sorted that mapping lost it
    silently. These cases hold the explicit field instead.
    """

    WORKSPACE = "ws-1"

    def run_fetch(self, sources, nodes_by_pipeline):
        mod = load_shoggoth()
        config = {
            "sources": [{"repo": r, "default_target": r} for r in sources],
            "selection": {"unassigned_only": True, "include_labels": [], "exclude_labels": []},
            "routes": [],
            "zenhub": {"workspace_id": self.WORKSPACE},
        }

        def fake_zenhub(query, variables):
            if "pipelinesConnection" in query:
                return {"workspace": {"pipelinesConnection": {"nodes": [
                    {"id": f"p-{name}", "name": name} for name in nodes_by_pipeline
                ]}}}
            name = variables["pid"][2:]
            return {"searchIssuesByPipeline": {
                "nodes": nodes_by_pipeline[name],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }}

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pipelines.json"
            with mock.patch.object(mod, "load_config", return_value=config), \
                 mock.patch.object(mod, "zenhub", side_effect=fake_zenhub), \
                 mock.patch.object(mod, "PIPELINES", out):
                mod.fetch_pipelines()
            return json.loads(out.read_text())

    @staticmethod
    def node(owner, repo, number):
        return {"number": number, "repository": {"name": repo, "ownerName": owner}}

    def test_position_follows_board_order_not_issue_number(self):
        written = self.run_fetch(
            ["wildcat-finance/product"],
            {"Product Backlog": [
                self.node("wildcat-finance", "product", 789),
                self.node("wildcat-finance", "product", 637),
                self.node("wildcat-finance", "product", 695),
            ]},
        )
        self.assertEqual(written["positions"], {
            "product#789": 0, "product#637": 1, "product#695": 2,
        })

    def test_each_pipeline_ranks_from_zero(self):
        written = self.run_fetch(
            ["wildcat-finance/product"],
            {
                "Icebox": [self.node("wildcat-finance", "product", 10)],
                "Product Backlog": [self.node("wildcat-finance", "product", 20),
                                    self.node("wildcat-finance", "product", 21)],
            },
        )
        self.assertEqual(written["positions"]["product#10"], 0)
        self.assertEqual(written["positions"]["product#20"], 0)
        self.assertEqual(written["positions"]["product#21"], 1)

    def test_a_repo_that_is_not_a_configured_source_gets_no_position(self):
        written = self.run_fetch(
            ["wildcat-finance/product"],
            {"Product Backlog": [
                self.node("wildcat-finance", "product", 1),
                self.node("someone-else", "other", 2),
                self.node("wildcat-finance", "product", 3),
            ]},
        )
        self.assertEqual(written["positions"], {"product#1": 0, "product#3": 1})
        self.assertIn("other#2", written["issues"])
        self.assertNotIn("other#2", written["positions"])

    def test_the_gate_reads_the_owner_and_not_the_bare_name(self):
        """A repository whose name matches a source but whose owner does not."""
        written = self.run_fetch(
            ["wildcat-finance/product"],
            {"Product Backlog": [self.node("laurenceday", "product", 9)]},
        )
        self.assertEqual(written["positions"], {})
        self.assertEqual(written["issues"], {"product#9": "Product Backlog"})

    def test_the_pipeline_name_map_keeps_its_string_values(self):
        """Both readers index issues[key] expecting a name, so the shape holds
        and the rank arrives as a sibling map."""
        written = self.run_fetch(
            ["wildcat-finance/product"],
            {"Product Backlog": [self.node("wildcat-finance", "product", 5)]},
        )
        self.assertEqual(written["issues"]["product#5"], "Product Backlog")
        self.assertEqual(written["positions"]["product#5"], 0)


class PerSourceTokenTests(unittest.TestCase):
    """A fine-grained PAT is scoped to one resource owner, so a private
    repository under a different owner cannot be reached by widening the
    default token. The source names the variable holding its own."""

    def test_a_source_may_name_its_own_token_variable(self):
        mod = load_shoggoth()
        raw = {
            "version": 1,
            "sources": [
                {"repo": "wildcat-finance/product"},
                {"repo": "laurenceday/shoggoth-playground",
                 "token_env": "GITHUB_READ_PAT_PLAYGROUND"},
            ],
            "selection": {"unassigned_only": True, "include_labels": [], "exclude_labels": []},
            "routes": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resolver.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with mock.patch.object(mod, "CONFIG", path):
                config = mod.load_config()
        self.assertIsNone(config["sources"][0]["token_env"])
        self.assertEqual(config["sources"][1]["token_env"], "GITHUB_READ_PAT_PLAYGROUND")

    def test_a_malformed_token_variable_name_is_refused(self):
        mod = load_shoggoth()
        for bad in ("lower_case", "HAS-DASH", "1LEADING", "", "A" * 80):
            raw = {
                "version": 1,
                "sources": [{"repo": "a/b", "token_env": bad}],
                "selection": {"unassigned_only": True, "include_labels": [], "exclude_labels": []},
                "routes": [],
            }
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "resolver.json"
                path.write_text(json.dumps(raw), encoding="utf-8")
                with mock.patch.object(mod, "CONFIG", path), self.subTest(value=bad):
                    with self.assertRaises(ValueError):
                        mod.load_config()

    def test_each_source_reads_with_its_own_token(self):
        mod = load_shoggoth()
        config = {
            "sources": [
                {"repo": "wildcat-finance/product", "default_target": "x/y", "token_env": None},
                {"repo": "laurenceday/shoggoth-playground",
                 "default_target": "laurenceday/shoggoth-playground",
                 "token_env": "GITHUB_READ_PAT_PLAYGROUND"},
            ],
            "selection": {"unassigned_only": True, "include_labels": [], "exclude_labels": []},
            "routes": [],
            "zenhub": None,
        }
        seen = []

        def fake_get(url, token=None):
            seen.append((url.split("/repos/")[1].split("/issues")[0], token))
            return []

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(mod, "load_config", return_value=config), \
                 mock.patch.object(mod, "get", side_effect=fake_get), \
                 mock.patch.object(mod, "env_var", side_effect=lambda n: f"token-for-{n}"), \
                 mock.patch.object(mod, "github_read_pat", return_value="default-token"), \
                 mock.patch.object(mod, "BOARD", Path(tmp) / "board.json"):
                mod.fetch()

        self.assertEqual(seen, [
            ("wildcat-finance/product", None),
            ("laurenceday/shoggoth-playground", "token-for-GITHUB_READ_PAT_PLAYGROUND"),
        ])

    def test_the_default_token_still_signs_a_source_without_one(self):
        """`None` reaches get(), which falls back to the default PAT rather
        than sending an empty Authorization header."""
        mod = load_shoggoth()
        captured = {}

        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/json"}
            def read(self, *a): return b"[]"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_urlopen(req, timeout=None):
            captured["auth"] = req.headers.get("Authorization")
            return FakeResponse()

        with mock.patch.object(mod, "github_read_pat", return_value="default-token"), \
             mock.patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen):
            mod.get(f"{mod.API}/repos/a/b/issues", None)
        self.assertEqual(captured["auth"], "Bearer default-token")
