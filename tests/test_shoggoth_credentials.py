import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def load_shoggoth():
    spec = importlib.util.spec_from_file_location(
        "shoggoth", REPO / "bin" / "shoggoth.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ShoggothCredentialTest(unittest.TestCase):
    def setUp(self):
        self.shoggoth = load_shoggoth()
        self.tmp = tempfile.TemporaryDirectory()
        self.shoggoth.ROOT = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_board_reader_uses_dedicated_read_token(self):
        (self.shoggoth.ROOT / ".env").write_text(
            "GITHUB_READ_PAT=test-read-value\n"
            "GITHUB_ISSUE_REPLY_PAT=test-reply-value\n"
            "ZENHUB_API_KEY=test-zenhub-value\n"
        )

        self.assertEqual(self.shoggoth.github_read_pat(), "test-read-value")

    def test_legacy_token_name_is_rejected(self):
        (self.shoggoth.ROOT / ".env").write_text(
            "WILDCAT_ZENHUB_READ_ONLY_PAT=test-legacy-value\n"
        )

        with self.assertRaisesRegex(SystemExit, "GITHUB_READ_PAT not found"):
            self.shoggoth.github_read_pat()


if __name__ == "__main__":
    unittest.main()
