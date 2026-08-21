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
            for pidfile in (self.root / ".loops" / "runs").glob("*.pid"):
                pidfile.unlink()
            result = self.launcher.start(mode)
            self.assertTrue(result["ok"], result)
            argv = self.spawn.calls[-1][0]
            self.assertEqual(argv, [
                "claude", "-p", prompt, "--permission-mode", "acceptEdits",
            ])

    def test_stop_refuses_when_nothing_is_running(self):
        self.assertEqual(self.launcher.stop()["ok"], False)

    def test_stop_terminates_the_run_it_launched(self):
        """End to end through the real spawn path.

        The whole process group goes: `start_new_session` puts the run in its
        own session, and signalling only the shell wrapper would leave whatever
        it spawned running with nothing watching it.
        """
        import time
        runs = self.root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        launcher = self.console.Launcher(self.root)
        log = runs / "victim.log"
        pid = launcher._spawn_detached(["/bin/sh", "-c", "sleep 60"], log)
        (runs / "victim.pid").write_text(str(pid))
        self.assertEqual(launcher._running()["pid"], pid)

        result = launcher.stop()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["pid"], pid)

        for _ in range(100):
            if log.with_suffix(".status").exists():
                break
            time.sleep(0.05)
        # The wrapper records its status on the way out, so a terminated run is
        # `failed` with a signal code rather than vanishing into `unknown`.
        entry = next(e for e in launcher.list() if e["name"] == "victim")
        self.assertEqual(entry["outcome"], "failed")
        self.assertNotEqual(entry["exit_code"], 0)
        self.assertIsNone(launcher._running())

    def test_stop_kills_what_the_run_spawned(self):
        """The reason it signals the group and not the leader.

        A loop's whole point is the agent it starts. Signalling only the shell
        wrapper would leave that agent running with nothing watching it, so the
        grandchild dying is the behaviour worth pinning.
        """
        import os
        import time
        runs = self.root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        launcher = self.console.Launcher(self.root)
        log = runs / "victim.log"
        child_pid_file = self.root / "child.pid"
        pid = launcher._spawn_detached(
            ["/bin/sh", "-c", f"sleep 60 & echo $! > {child_pid_file}; wait"], log)
        (runs / "victim.pid").write_text(str(pid))
        for _ in range(100):
            if child_pid_file.exists():
                break
            time.sleep(0.05)
        grandchild = int(child_pid_file.read_text().strip())

        self.assertTrue(launcher.stop()["ok"])

        for _ in range(100):
            try:
                os.kill(grandchild, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        with self.assertRaises(ProcessLookupError):
            os.kill(grandchild, 0)

    def test_stop_records_a_status_when_the_kill_beats_the_trap(self):
        """A kill landing before the wrapper's trap installs still reports.

        The trap is the wrapper's first line but is not installed instantly,
        and a signal arriving in that gap takes SIGTERM's default action: the
        shell dies with nothing written. Without the console recording it, a
        deliberate kill would read as `unknown` -- indistinguishable from a run
        whose console died under it.
        """
        runs = self.root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        launcher = self.console.Launcher(self.root)
        log = runs / "victim.log"
        # No settling time at all: stop as fast as the spawn returns.
        pid = launcher._spawn_detached(["/bin/sh", "-c", "sleep 60"], log)
        (runs / "victim.pid").write_text(str(pid))

        self.assertTrue(launcher.stop()["ok"])

        entry = next(e for e in launcher.list() if e["name"] == "victim")
        self.assertEqual(entry["outcome"], "failed")
        self.assertEqual(entry["exit_code"], 143)

    def test_stop_refuses_a_group_the_run_does_not_lead(self):
        """It must never widen to a group it cannot vouch for.

        `getpgid` reports the console's own group for a moment after a spawn.
        Signalling that would kill the console and everything beside it, so
        leadership is required before any signal is sent.
        """
        import os
        runs = self.root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        launcher = self.console.Launcher(self.root)
        # A pid that is alive but leads no group of its own: this process.
        (runs / "victim.pid").write_text(str(os.getpid()))

        result = launcher.stop()

        self.assertFalse(result["ok"], result)
        self.assertIn("process group", result["error"])

    def test_a_finished_run_does_not_block_the_next_launch(self):
        """The console never reaps its children, so a completed run leaves a
        zombie whose pid still answers `kill -0`. Reading only the pid jammed
        `start()` on "still running" for as long as the console stayed up."""
        import time
        runs = self.root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        launcher = self.console.Launcher(self.root)
        log = runs / "done.log"
        pid = launcher._spawn_detached(["/bin/sh", "-c", "true"], log)
        (runs / "done.pid").write_text(str(pid))
        for _ in range(100):
            if log.with_suffix(".status").exists():
                break
            time.sleep(0.05)
        self.assertIsNone(launcher._running())

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
