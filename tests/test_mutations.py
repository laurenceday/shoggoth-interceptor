import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "bin" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StubRunner:
    def __init__(self, exit_code=0):
        self.calls = []
        self.exit_code = exit_code

    def __call__(self, argv):
        self.calls.append(argv)
        return self.exit_code, "stub output"


class MutationTest(unittest.TestCase):
    def setUp(self):
        self.console = load_module("console")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()
        (self.root / "bin").mkdir()
        self.runner = StubRunner()
        self.api = self.console.Api(self.root, runner=self.runner)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refresh_uses_fixed_argv(self):
        result = self.api.refresh()
        self.assertTrue(result["ok"])
        commands = [call[2] for call in self.runner.calls]
        self.assertEqual(commands, ["fetch", "fetch-pipelines"])
        for call in self.runner.calls:
            self.assertEqual(call[1], str(self.root / "bin" / "shoggoth.py"))

    def test_exclude_valid(self):
        result = self.api.exclude(789, "loop 1 complete")
        self.assertTrue(result["ok"])
        self.assertEqual(self.runner.calls[0][2:], ["exclude", "789", "loop 1 complete"])

    def test_exclude_rejects_non_integer(self):
        for bad in ("789", 0, -4, 10_000_000, None, 7.5):
            result = self.api.exclude(bad, "reason")
            self.assertFalse(result["ok"], bad)
        self.assertEqual(self.runner.calls, [])

    def test_exclude_bounds_reason(self):
        self.assertFalse(self.api.exclude(789, "x" * 301)["ok"])
        self.assertFalse(self.api.exclude(789, "")["ok"])
        self.assertFalse(self.api.exclude(789, None)["ok"])
        self.assertEqual(self.runner.calls, [])

    def test_archive_uses_fixed_argv(self):
        self.api.archive()
        self.assertEqual(self.runner.calls, [[str(self.root / "bin" / "archive.sh")]])

    def test_failed_subprocess_reported_truthfully(self):
        api = self.console.Api(self.root, runner=StubRunner(exit_code=1))
        self.assertFalse(api.refresh()["ok"])
        self.assertFalse(api.exclude(789, "reason")["ok"])
        self.assertFalse(api.archive()["ok"])


class AtomicExcludeTest(unittest.TestCase):
    def test_shoggoth_exclude_writes_temp_then_rename(self):
        source = (REPO / "bin" / "shoggoth.py").read_text()
        write_block = source[source.index("def exclude("):source.index("def main(")]
        self.assertIn(".replace(EXCLUDED)", write_block)
        self.assertNotIn("EXCLUDED.write_text", write_block)


class ClientHygieneTest(unittest.TestCase):
    def test_client_never_uses_innerhtml_on_board_data(self):
        js = (REPO / "bin" / "console.js").read_text()
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("insertAdjacentHTML", js)
        self.assertNotIn("document.write", js)

    def test_page_pins_csp_and_local_script_only(self):
        console = load_module("console")
        html = (REPO / "bin" / "console.html").read_text()
        self.assertIn('src="/console.js"', html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)


if __name__ == "__main__":
    unittest.main()
