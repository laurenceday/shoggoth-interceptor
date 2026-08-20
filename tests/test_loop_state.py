import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
import unicodedata
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def load_shoggoth():
    spec = importlib.util.spec_from_file_location(
        "shoggoth_loop_state", REPO / "bin" / "shoggoth.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LoopStateTest(unittest.TestCase):
    def setUp(self):
        self.shoggoth = load_shoggoth()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        state = root / "state"
        state.mkdir()
        self.readme = root / "README.md"
        self.readme.write_text(
            "# Shoggoth Interceptor\n\nquote\n\n"
            f"{self.shoggoth.README_VIDEO_URL}\n\n"
            "old intro\n\n## Pieces\n\nbody\n"
        )
        self.loop_state = state / "loop.json"
        self.loop_state.write_text('{"completed_loops": 4}\n')

        self.shoggoth.ROOT = root
        self.shoggoth.STATE = state
        self.shoggoth.LOOP_STATE = self.loop_state
        self.shoggoth.README = self.readme

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def without_marks(text):
        return "".join(
            character for character in text if not unicodedata.combining(character)
        )

    def test_completion_advances_state_and_replaces_intro_silently(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.shoggoth.complete_loop(5)

        state = json.loads(self.loop_state.read_text())
        plain_readme = self.without_marks(self.readme.read_text())
        self.assertEqual(state["completed_loops"], 5)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(self.shoggoth.README_INTRO, plain_readme)
        self.assertIn(self.shoggoth.README_VIDEO_URL, plain_readme)
        self.assertIn("\n## Pieces\n", plain_readme)

    def test_repeated_completion_is_idempotent_and_silent(self):
        original = self.readme.read_text()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.shoggoth.complete_loop(4)

        self.assertEqual(self.readme.read_text(), original)
        self.assertEqual(output.getvalue(), "")

    def test_completion_cannot_skip_a_number(self):
        with self.assertRaisesRegex(SystemExit, "completion out of sequence"):
            self.shoggoth.complete_loop(6)

    def test_malformed_state_fails_closed(self):
        self.loop_state.write_text('{"completed_loops": "four"}\n')
        with self.assertRaisesRegex(SystemExit, "invalid completion state"):
            self.shoggoth.complete_loop(5)

    def test_invalid_json_fails_closed(self):
        self.loop_state.write_text("not json\n")
        with self.assertRaisesRegex(SystemExit, "invalid completion state"):
            self.shoggoth.complete_loop(5)

    def test_non_object_state_fails_closed(self):
        self.loop_state.write_text("[]\n")
        with self.assertRaisesRegex(SystemExit, "invalid completion state"):
            self.shoggoth.complete_loop(5)

    def test_completion_number_must_be_positive(self):
        with self.assertRaisesRegex(SystemExit, "invalid completion number"):
            self.shoggoth.complete_loop(0)

    def test_missing_renderer_fails_closed(self):
        self.shoggoth.ZALGO_SCRIPT = Path(self.tmp.name) / "missing.py"
        with self.assertRaisesRegex(SystemExit, "text renderer unavailable"):
            self.shoggoth.complete_loop(5)


if __name__ == "__main__":
    unittest.main()
