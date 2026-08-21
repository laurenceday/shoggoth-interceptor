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
            # stream-json is what makes a run watchable while it runs;
            # --verbose is required alongside it.
            self.assertEqual(argv, [
                "claude", "-p", prompt, "--permission-mode", "acceptEdits",
                "--output-format", "stream-json", "--verbose",
            ])

    # --- streamed run logs -------------------------------------------------

    def _stream(self, *events):
        import json
        return "\n".join(json.dumps(e) for e in events) + "\n"

    def test_a_streamed_log_becomes_events(self):
        log = self._stream(
            {"type": "system", "subtype": "init", "model": "claude-opus-5",
             "cwd": "/repo"},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash",
                 "input": {"command": "git status", "description": "check"}}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "ranking the candidates"}]}},
            {"type": "result", "subtype": "success", "result": "done",
             "num_turns": 3, "duration_ms": 9000, "total_cost_usd": 1.5},
        )
        events = self.console.summarise_stream(log)
        kinds = [e["kind"] for e in events]
        self.assertEqual(kinds, ["init", "tool", "text", "result"])
        # The subject is the point of the call: which command, not that some
        # tool ran.
        self.assertEqual(events[1]["text"], "Bash")
        self.assertEqual(events[1]["detail"], "git status")
        self.assertIn("3 turns", events[3]["detail"])
        self.assertIn("$1.50", events[3]["detail"])

    def test_a_plain_text_log_is_not_read_as_a_stream(self):
        """Logs written before runs streamed still have to render.

        `summarise_stream` returning None is what routes them back to the raw
        tail they always had, rather than showing an empty event list.
        """
        self.assertIsNone(self.console.summarise_stream(
            "Loop complete. Delivered issue #12.\nArchive cut.\n"))

    def test_stderr_in_a_streamed_log_is_surfaced(self):
        """The run's stderr shares this file, and it is where crashes land.

        A traceback or a missing binary is not JSON, so a parser that kept
        only JSON would drop exactly the output worth reading.
        """
        log = ("claude: command not found\n"
               + self._stream({"type": "result", "subtype": "error_during_execution",
                               "is_error": True, "result": "boom"}))
        events = self.console.summarise_stream(log)
        self.assertEqual(events[0]["kind"], "stderr")
        self.assertIn("command not found", events[0]["text"])
        # A non-success result is an error, not a quiet finish.
        self.assertEqual(events[-1]["kind"], "error")

    def test_a_failed_tool_result_is_surfaced_but_a_successful_one_is_not(self):
        """Every call gets a result; only the failures say anything new."""
        log = self._stream(
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "is_error": False, "content": "ok"}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "is_error": True, "content": "no such file"}]}},
        )
        events = self.console.summarise_stream(log)
        self.assertEqual([e["kind"] for e in events], ["error"])
        self.assertIn("no such file", events[0]["text"])

    def test_a_line_cut_by_the_tail_read_is_not_reported_as_an_error(self):
        """Reading only the tail of a long log cuts its first line in half.

        That is an artefact of how the file is read, not something the run
        emitted, so it must not surface as stderr.
        """
        log = ('ent": "half an object"}}\n'
               + self._stream({"type": "assistant", "message": {"content": [
                   {"type": "text", "text": "still going"}]}}))
        events = self.console.summarise_stream(log, first_line_cut=True)
        self.assertEqual([e["kind"] for e in events], ["text"])
        # Without the cut flag the same line is real output and is kept: the
        # run's own stderr is prose too, and cannot be told apart by looking.
        self.assertEqual(
            [e["kind"] for e in self.console.summarise_stream(log)],
            ["stderr", "text"])

    def test_read_tail_returns_the_end_and_the_true_size(self):
        path = self.root / "big.log"
        path.write_text("a" * 100 + "TAIL")
        text, size, cut = self.console.read_tail(path, 4)
        self.assertEqual(text, "TAIL")
        self.assertEqual(size, 104)
        self.assertTrue(cut)
        self.assertFalse(self.console.read_tail(path, 10_000)[2])

    def test_a_streamed_run_reports_events_and_hides_no_output(self):
        """End to end through `list()`: the payload the console renders."""
        runs = self.root / ".loops" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "loop-1.log").write_text(self._stream(
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "CLAUDE.md"}}]}}))
        entry = self.console.Launcher(self.root).list()[0]
        self.assertTrue(entry["streaming"])
        self.assertEqual(entry["log_tail"], "")
        self.assertEqual(entry["events"][0]["detail"], "CLAUDE.md")

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
