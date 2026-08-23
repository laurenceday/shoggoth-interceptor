"""Checks the Interceptor's installed Shoggoth identity contract."""

from pathlib import Path
import hashlib
import unittest


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "SHOGGOTH.md"
EXPECTED_SHA256 = "d74ddcf9082b8ff3bcdd14a8a17b3ef4632696edd348d21500cd892cab632740"


class CollectiveIdentityTests(unittest.TestCase):
    def identity_text(self):
        return " ".join(IDENTITY.read_text(encoding="utf-8").split())

    def test_installed_copy_matches_the_source_bound_bytes(self):
        self.assertEqual(
            hashlib.sha256(IDENTITY.read_bytes()).hexdigest(), EXPECTED_SHA256
        )

    def test_host_and_human_entries_load_the_identity_contract(self):
        for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
            with self.subTest(name=name):
                self.assertIn("SHOGGOTH.md", (ROOT / name).read_text(encoding="utf-8"))

    def test_identity_does_not_widen_interceptor_authority(self):
        text = self.identity_text()
        self.assertIn("The Interceptor name does not widen authority", text)
        self.assertIn("override an instruction from a target repository", text)

    def test_creator_reference_stays_role_bounded(self):
        text = self.identity_text()
        self.assertIn("Use `the Creator` only when the role matters", text)
        self.assertIn("by personal name", text)

    def test_governed_agent_work_belongs_to_shoggoth(self):
        text = self.identity_text()
        self.assertIn("Repository work produced by an agent after invoking a Wildcat domain or phase skill", text)
        self.assertIn("Every piece of work produced through the Shoggoth Interceptor", text)
        self.assertIn("host or model identities must not appear as the Git author", text)
        self.assertIn("A human contributor keeps authorship of their own work", text)


if __name__ == "__main__":
    unittest.main()
