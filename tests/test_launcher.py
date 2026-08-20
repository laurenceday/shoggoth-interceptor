import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_console():
    spec = importlib.util.spec_from_file_location("console", REPO / "bin" / "console.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StubSpawn:
    def __init__(self, pid=99999999):
        self.calls = []
        self.pid = pid

    def __call__(self, argv, log_path):
        self.calls.append((argv, log_path))
        log_path.write_text("stub session output\n")
        return self.pid


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.console = load_console()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.spawn = StubSpawn()
        self.launcher = self.console.Launcher(self.root, spawn=self.spawn)

    def tearDown(self):
        self.tmp.cleanup()

    def test_smoke_and_loop_use_fixed_argv(self):
        for mode, prompt in (
            ("smoke", self.console.SMOKE_PROMPT),
            ("loop", self.console.LOOP_PROMPT),
        ):
            for pidfile in (self.root / "loops" / "runs").glob("*.pid"):
                pidfile.unlink()
            result = self.launcher.start(mode)
            self.assertTrue(result["ok"], result)
            argv = self.spawn.calls[-1][0]
            self.assertEqual(argv, [
                "claude", "-p", prompt, "--permission-mode", "acceptEdits",
            ])

    def test_request_data_never_reaches_argv(self):
        result = self.launcher.start("loop; rm -rf /")
        self.assertFalse(result["ok"])
        self.assertEqual(self.spawn.calls, [])

    def test_refuses_while_a_launch_is_alive(self):
        alive = self.console.Launcher(self.root, spawn=StubSpawn(pid=os.getpid()))
        first = alive.start("smoke")
        self.assertTrue(first["ok"])
        second = alive.start("smoke")
        self.assertFalse(second["ok"])
        self.assertIn("still running", second["error"])

    def test_allows_next_launch_after_previous_finished(self):
        first = self.launcher.start("smoke")  # stub pid 99999999 is dead
        self.assertTrue(first["ok"])
        second = self.launcher.start("smoke")
        self.assertTrue(second["ok"], second)

    def test_list_reports_running_state_and_log_tail(self):
        alive = self.console.Launcher(self.root, spawn=StubSpawn(pid=os.getpid()))
        started = alive.start("smoke")
        launches = alive.list()
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0]["name"], started["name"])
        self.assertTrue(launches[0]["running"])
        self.assertIn("stub session output", launches[0]["log_tail"])


if __name__ == "__main__":
    unittest.main()
