import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "bin" / "repository-gate.py"

POLICY = {
    "version": 2,
    "mode": "protected-orgs",
    "github_login": "shoggoth-wildcat",
    "protected": {
        "wildcat-finance": {"exempt": ["wildcat-finance/skills"]},
    },
}

UNINITIALIZED = {
    "version": 2,
    "mode": "protected-orgs",
    "github_login": None,
    "protected": {},
}


def load_gate():
    spec = importlib.util.spec_from_file_location("repository_gate", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RepositoryGateTest(unittest.TestCase):
    def setUp(self):
        self.gate = load_gate()
        self.policy = self.gate.validate_policy(POLICY)

    def test_protected_organization_is_denied(self):
        for target in (
            "wildcat-finance/v2-protocol",
            "git@github.com:wildcat-finance/product.git",
            "https://github.com/Wildcat-Finance/WILDCAT-APP-V2.git",
        ):
            allowed, reason = self.gate.decide(target, self.policy, "shoggoth-wildcat")
            self.assertFalse(allowed, target)
            self.assertIn("write-protected", reason)

    def test_exempt_repository_inside_protection_is_allowed(self):
        for target in (
            "wildcat-finance/skills",
            "https://github.com/Wildcat-Finance/skills.git",
        ):
            allowed, reason = self.gate.decide(target, self.policy, "shoggoth-wildcat")
            self.assertTrue(allowed, target)
            self.assertIn("exempt", reason)

    def test_unprotected_organization_is_allowed(self):
        allowed, reason = self.gate.decide(
            "laurenceday/shoggoth-interceptor", self.policy, "shoggoth-wildcat"
        )
        self.assertTrue(allowed)
        self.assertIn("not protected", reason)

    def test_login_mismatch_is_denied_everywhere(self):
        for target in ("wildcat-finance/skills", "laurenceday/shoggoth-interceptor"):
            allowed, reason = self.gate.decide(target, self.policy, "someone-else")
            self.assertFalse(allowed, target)
            self.assertIn("does not match", reason)

    def test_merge_is_denied_on_every_target(self):
        for target in (
            "wildcat-finance/skills",
            "wildcat-finance/v2-protocol",
            "laurenceday/shoggoth-interceptor",
        ):
            allowed, reason = self.gate.decide(
                target, self.policy, "shoggoth-wildcat", operation="merge"
            )
            self.assertFalse(allowed, target)
            self.assertIn("merge", reason)

    def test_unrecorded_consent_denies_everything(self):
        policy = self.gate.validate_policy(UNINITIALIZED)
        for target in ("laurenceday/shoggoth-interceptor", "wildcat-finance/skills"):
            allowed, reason = self.gate.decide(target, policy, "shoggoth-wildcat")
            self.assertFalse(allowed, target)
            self.assertIn("no consent", reason)

    def test_hand_widened_policy_fails_validation(self):
        bad = (
            # empty object
            {},
            # the retired sandbox-only shape
            {"version": 1, "organizations": {
                "wildcat-finance": {
                    "mode": "sandbox-only",
                    "sandbox": "wildcat-finance/sandbox",
                    "github_login": "user",
                },
            }},
            # an invented permissive mode
            {"version": 2, "mode": "allow-all", "github_login": "user", "protected": {}},
            # a login hand-added to the shipped default: allow-everything with
            # no protected organization is not a state init ever writes
            {"version": 2, "mode": "protected-orgs", "github_login": "user", "protected": {}},
            # protection without a recorded login records no consent
            {"version": 2, "mode": "protected-orgs", "github_login": None, "protected": {
                "wildcat-finance": {"exempt": []},
            }},
            # a wildcard exemption
            {"version": 2, "mode": "protected-orgs", "github_login": "user", "protected": {
                "wildcat-finance": {"exempt": ["wildcat-finance/*"]},
            }},
            # an exemption outside its organization
            {"version": 2, "mode": "protected-orgs", "github_login": "user", "protected": {
                "wildcat-finance": {"exempt": ["laurenceday/skills"]},
            }},
            # unknown top-level fields
            {"version": 2, "mode": "protected-orgs", "github_login": "user", "protected": {
                "wildcat-finance": {"exempt": []},
            }, "allow": ["anything"]},
            # unknown per-organization fields
            {"version": 2, "mode": "protected-orgs", "github_login": "user", "protected": {
                "wildcat-finance": {"exempt": [], "sandbox": "wildcat-finance/anything"},
            }},
        )
        for policy in bad:
            with self.assertRaises(ValueError, msg=json.dumps(policy)):
                self.gate.validate_policy(policy)

    def test_target_normalisation_rejects_options_and_extra_path(self):
        for target in ("--repo", "https://evil.test/x/y", "owner/repo/extra", "../x"):
            with self.assertRaises(ValueError, msg=target):
                self.gate.normalize_repo(target)

    def test_merge_cli_is_denied_before_policy_or_login_is_read(self):
        result = subprocess.run(
            [sys.executable, str(GATE), "merge", "wildcat-finance/skills"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("never gate-approved", result.stderr)

    def test_guardrails_file_override_is_gone(self):
        self.assertNotIn("SHOGGOTH_GUARDRAILS_FILE", GATE.read_text(encoding="utf-8"))


class ConsentSetupTest(unittest.TestCase):
    def setUp(self):
        self.gate = load_gate()
        self.tmp = tempfile.TemporaryDirectory()
        self.gate.LOCAL_POLICY = Path(self.tmp.name) / ".loops" / "guardrails.json"
        self.gate.DEFAULT_POLICY = Path(self.tmp.name) / "state" / "guardrails.json"
        self.gate.DEFAULT_POLICY.parent.mkdir()
        self.gate.DEFAULT_POLICY.write_text(
            json.dumps(UNINITIALIZED, indent=2, sort_keys=True) + "\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def read_local(self):
        return json.loads(self.gate.LOCAL_POLICY.read_text())

    def test_no_aborts_protect_without_writing(self):
        with mock.patch("builtins.input", return_value="no"), self.assertRaisesRegex(
            ValueError, "nothing was recorded"
        ):
            self.gate.init_protect("wildcat-finance")
        self.assertFalse(self.gate.LOCAL_POLICY.exists())

    def test_yes_records_protection_and_active_login(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="laurenceday"
        ), mock.patch("sys.stdout", new=io.StringIO()):
            self.gate.init_protect("Wildcat-Finance")
        policy = self.read_local()
        self.assertEqual(policy["github_login"], "laurenceday")
        self.assertEqual(policy["protected"], {"wildcat-finance": {"exempt": []}})

    def test_exempt_requires_the_organization_to_be_protected(self):
        with mock.patch("builtins.input", return_value="yes"), self.assertRaisesRegex(
            ValueError, "not protected"
        ):
            self.gate.init_exempt("wildcat-finance/skills")
        self.assertFalse(self.gate.LOCAL_POLICY.exists())

    def test_no_aborts_exempt_without_writing(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="laurenceday"
        ), mock.patch("sys.stdout", new=io.StringIO()):
            self.gate.init_protect("wildcat-finance")
        with mock.patch("builtins.input", return_value="no"), self.assertRaisesRegex(
            ValueError, "no exemption was recorded"
        ):
            self.gate.init_exempt("wildcat-finance/skills")
        self.assertEqual(self.read_local()["protected"], {"wildcat-finance": {"exempt": []}})

    def test_yes_records_one_exemption(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="laurenceday"
        ), mock.patch("sys.stdout", new=io.StringIO()):
            self.gate.init_protect("wildcat-finance")
            self.gate.init_exempt("wildcat-finance/skills")
            self.gate.init_exempt("wildcat-finance/skills")
        policy = self.read_local()
        self.assertEqual(
            policy["protected"], {"wildcat-finance": {"exempt": ["wildcat-finance/skills"]}}
        )

    def test_consent_is_refused_for_a_different_active_login(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="laurenceday"
        ), mock.patch("sys.stdout", new=io.StringIO()):
            self.gate.init_protect("wildcat-finance")
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="someone-else"
        ), self.assertRaisesRegex(ValueError, "bound to"):
            self.gate.init_exempt("wildcat-finance/skills")
        self.assertEqual(self.read_local()["github_login"], "laurenceday")

    def test_reprotecting_keeps_recorded_exemptions(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch.object(
            self.gate, "active_login", return_value="laurenceday"
        ), mock.patch("sys.stdout", new=io.StringIO()):
            self.gate.init_protect("wildcat-finance")
            self.gate.init_exempt("wildcat-finance/skills")
            self.gate.init_protect("wildcat-finance")
        policy = self.read_local()
        self.assertEqual(
            policy["protected"], {"wildcat-finance": {"exempt": ["wildcat-finance/skills"]}}
        )


if __name__ == "__main__":
    unittest.main()
