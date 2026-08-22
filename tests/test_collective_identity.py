"""Checks the Interceptor's installed Shoggoth identity contract."""

from pathlib import Path
import hashlib
import unittest


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "SHOGGOTH.md"
EXPECTED_SHA256 = "00d516fdd46f5cbfbed8a3f49b8299641a396531467319b5b042e8eb28c1f4fa"


class CollectiveIdentityTests(unittest.TestCase):
    def test_installed_copy_matches_the_source_bound_bytes(self):
        self.assertEqual(
            hashlib.sha256(IDENTITY.read_bytes()).hexdigest(), EXPECTED_SHA256
        )

    def test_host_and_human_entries_load_the_identity_contract(self):
        for name in ("AGENTS.md", "CLAUDE.md", "README.md"):
            with self.subTest(name=name):
                self.assertIn("SHOGGOTH.md", (ROOT / name).read_text(encoding="utf-8"))

    def test_identity_does_not_widen_interceptor_authority(self):
        text = IDENTITY.read_text(encoding="utf-8")
        self.assertIn("The Interceptor name does not widen authority", text)
        self.assertIn("override an instruction from a target repository", text)

    def test_creator_reference_stays_role_bounded(self):
        text = IDENTITY.read_text(encoding="utf-8")
        self.assertIn("Use `the Creator` only when the role matters", text)
        self.assertIn("by\npersonal name", text)


if __name__ == "__main__":
    unittest.main()
