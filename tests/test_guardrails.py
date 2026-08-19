import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "bin" / "wildcat-gate.sh"


def gate(target, wildcat_gh_login=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"wildcat_gh_login": wildcat_gh_login}, fh)
        guardrails = fh.name
    try:
        return subprocess.run(
            [str(GATE), target],
            env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
                 "HOME": str(Path.home()),
                 "SHOGGOTH_GUARDRAILS_FILE": guardrails},
            capture_output=True, text=True, timeout=30,
        )
    finally:
        Path(guardrails).unlink()


class WildcatGateTest(unittest.TestCase):
    def test_denies_wildcat_finance_without_credential(self):
        for target in (
            "wildcat-finance/wildcat-app-v2",
            "git@github.com:wildcat-finance/v2-protocol.git",
            "https://github.com/wildcat-finance/product",
            "https://github.com/Wildcat-Finance/WILDCAT-APP-V2.git",
        ):
            result = gate(target)
            self.assertEqual(result.returncode, 1, target)
            self.assertIn("DENIED", result.stderr)

    def test_allows_the_skills_repo(self):
        for target in (
            "wildcat-finance/skills",
            "https://github.com/wildcat-finance/skills.git",
        ):
            self.assertEqual(gate(target).returncode, 0, target)

    def test_allows_every_other_owner(self):
        for target in (
            "laurenceday/shoggoth-interceptor",
            "https://github.com/someoneelse/thing",
            "git@github.com:another-org/repo.git",
        ):
            self.assertEqual(gate(target).returncode, 0, target)

    def test_denies_wildcat_finance_when_active_login_differs(self):
        # The active gh login on this host is not "shoggoth-wildcat", so a
        # configured credential that does not match must still deny.
        result = gate("wildcat-finance/wildcat-app-v2",
                      wildcat_gh_login="shoggoth-wildcat")
        self.assertEqual(result.returncode, 1)
        self.assertIn("is not the shoggoth", result.stderr)

    def test_allows_wildcat_finance_when_active_login_matches(self):
        active = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        if not active:
            self.skipTest("no active gh login available")
        result = gate("wildcat-finance/wildcat-app-v2", wildcat_gh_login=active)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
