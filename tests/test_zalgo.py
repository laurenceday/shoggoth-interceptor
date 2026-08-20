import importlib.util
import unittest
import unicodedata
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def load_zalgo():
    spec = importlib.util.spec_from_file_location("zalgo", REPO / "bin" / "zalgo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ZalgoTest(unittest.TestCase):
    def setUp(self):
        self.zalgo = load_zalgo()

    @staticmethod
    def combining_count(text):
        return sum(bool(unicodedata.combining(character)) for character in text)

    @staticmethod
    def without_marks(text):
        return "".join(
            character for character in text if not unicodedata.combining(character)
        )

    def test_seed_makes_output_repeatable(self):
        first = self.zalgo.zalgo("The Shoggoth stirs.", 50, seed=42)
        second = self.zalgo.zalgo("The Shoggoth stirs.", 50, seed=42)
        self.assertEqual(first, second)

    def test_higher_scale_adds_more_marks(self):
        text = "the shoggoth interceptor watches the board"
        low = self.zalgo.zalgo(text, 1, seed=7)
        high = self.zalgo.zalgo(text, 100, seed=7)
        self.assertGreater(self.combining_count(high), self.combining_count(low))

    def test_base_text_and_whitespace_survive(self):
        text = "line one\nline two\tend"
        transformed = self.zalgo.zalgo(text, 75, seed=9)
        self.assertEqual(self.without_marks(transformed), text)

    def test_short_text_always_gets_at_least_one_mark(self):
        transformed = self.zalgo.zalgo("boo", 1, seed=3)
        self.assertGreaterEqual(self.combining_count(transformed), 1)

    def test_scale_must_be_between_one_and_one_hundred(self):
        for scale in (0, 101, True):
            with self.subTest(scale=scale):
                with self.assertRaises(self.zalgo.ZalgoError):
                    self.zalgo.zalgo("text", scale)

    def test_control_and_format_characters_are_rejected(self):
        for character in ("\x1b", "\u202e"):
            with self.subTest(character=ord(character)):
                with self.assertRaises(self.zalgo.ZalgoError):
                    self.zalgo.zalgo(f"before{character}after", 10)

    def test_input_size_is_bounded(self):
        text = "a" * (self.zalgo.MAX_INPUT_CHARS + 1)
        with self.assertRaises(self.zalgo.ZalgoError):
            self.zalgo.zalgo(text, 10)


if __name__ == "__main__":
    unittest.main()
