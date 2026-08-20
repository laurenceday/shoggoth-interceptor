# Launcher demo: smoke launch from the page

Performed 2026-08-19 ~03:40 UTC, on the rebuilt console with the loop
launcher.

- Clicked "Smoke launch" in the dashboard header. The status bar reported
  "launched smoke-20260819-034048 (pid 49963)" and the new Loop launches
  panel showed the session as running.
- The spawned process was a real detached headless Claude Code session
  (`claude -p <smoke prompt> --permission-mode acceptEdits`). Its log,
  `.loops/runs/smoke-20260819-034048.log`, ended with exactly the expected
  marker: `SHOGGOTH-SMOKE-OK`.
- After the session exited (and the console server was restarted in
  between), GET /api/loops still reported the launch, now as finished, with
  the marker in its log tail: the record lives on disk, not in the process.
- The "Start loop" button uses the same pipeline with the full one-ticket
  loop prompt from CLAUDE.md; it was deliberately not pressed in this demo,
  since a full loop is the operator's call to make and this session had
  already run loop 1 by hand.
