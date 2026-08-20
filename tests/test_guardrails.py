import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "bin" / "repository-gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("repository_gate", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RepositoryGateTest(unittest.TestCase):
    def setUp(self):
        self.gate = load_gate()
        self.policy = self.gate.validate_policy({
            "version": 1,
            "organizations": {
                "wildcat-finance": {
                    "mode": "sandbox-only",
                    "sandbox": "wildcat-finance/shoggoth-sandbox",
                    "github_login": "shoggoth-wildcat",
                }
            },
        })

    def test_unknown_organization_is_denied(self):
        allowed, reason = self.gate.decide(
            "laurenceday/shoggoth-interceptor", self.policy, "shoggoth-wildcat"
        )
        self.assertFalse(allowed)
        self.assertIn("no write policy", reason)

    def test_every_non_sandbox_repository_is_denied(self):
        for target in (
            "wildcat-finance/product",
            "git@github.com:wildcat-finance/v2-protocol.git",
            "https://github.com/Wildcat-Finance/WILDCAT-APP-V2.git",
        ):
            allowed, reason = self.gate.decide(target, self.policy, "shoggoth-wildcat")
            self.assertFalse(allowed, target)
            self.assertIn("only sandbox", reason)

    def test_sandbox_requires_the_recorded_login(self):
        target = "wildcat-finance/shoggoth-sandbox"
        self.assertFalse(self.gate.decide(target, self.policy, "someone-else")[0])
        self.assertTrue(self.gate.decide(target, self.policy, "shoggoth-wildcat")[0])

    def test_malformed_policy_fails_closed(self):
        bad = (
            {},
            {"version": 1, "organizations": []},
            {"version": 1, "organizations": {"x": {"mode": "allow-all"}}},
            {"version": 1, "organizations": {
                "x": {"mode": "sandbox-only", "sandbox": "y/repo", "github_login": "user"}
            }},
        )
        for policy in bad:
            with self.assertRaises(ValueError):
                self.gate.validate_policy(policy)

    def test_target_normalisation_rejects_options_and_extra_path(self):
        for target in ("--repo", "https://evil.test/x/y", "owner/repo/extra", "../x"):
            with self.assertRaises(ValueError, msg=target):
                self.gate.normalize_repo(target)


class FirstRunSetupTest(unittest.TestCase):
    def setUp(self):
        self.gate = load_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.gate.LOCAL_POLICY = Path(self.tmp.name) / ".loops" / "guardrails.json"
        self.gate.DEFAULT_POLICY = Path(self.tmp.name) / "state" / "guardrails.json"
        self.gate.DEFAULT_POLICY.parent.mkdir()
        self.gate.DEFAULT_POLICY.write_text('{"version": 1, "organizations": {}}\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_aborts_without_writing(self):
        with mock.patch("builtins.input", return_value="no"), self.assertRaisesRegex(
            ValueError, "no write access was granted"
        ):
            self.gate.init_policy("wildcat-finance", "wildcat-finance/sandbox")
        self.assertFalse(self.gate.LOCAL_POLICY.exists())

    def test_yes_records_one_sandbox_and_active_login(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="laurenceday"
        ), mock.patch("sys.stdout", new=io.StringIO()):
            self.gate.init_policy("wildcat-finance", "wildcat-finance/sandbox")
        policy = json.loads(self.gate.LOCAL_POLICY.read_text())
        entry = policy["organizations"]["wildcat-finance"]
        self.assertEqual(entry["sandbox"], "wildcat-finance/sandbox")
        self.assertEqual(entry["github_login"], "laurenceday")


if __name__ == "__main__":
    unittest.main()
