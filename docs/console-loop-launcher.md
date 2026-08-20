# Study: console loop launcher

Assuming, unless corrected:

1. "Starting the Shoggoth loop" means spawning a detached headless Claude
   Code session (`claude -p`) in this repo, primed with the loop protocol
   from CLAUDE.md. The console launches and observes it; it does not manage
   the agent's conversation.
2. The launched session runs with `--permission-mode acceptEdits` so it can
   work unattended in this repo; anything needing broader permissions stops
   and waits, which is acceptable for the prototype. The operator's local
   Claude Code settings remain the real permission boundary.
3. Two launch modes exist: `smoke` (a trivial prompt proving the pipeline,
   cheap enough to run in the demo) and `loop` (the real one-ticket
   interceptor loop). The demo runs smoke; the operator runs loop.
4. One loop at a time: launching while a launched session is still running
   is refused. Loops the agent (this session) runs by hand do not register
   here.

## 1. Problem statement

The operator's feedback on the console prototype, verbatim: "Doesn't have
the ability to actually start the Shoggoth loop." The console can show the
board, record exclusions, and cut archives, but the loop itself still needs
someone to drive a Claude session by hand. The build adds a Start-loop
action: POST `/api/start-loop` spawns a detached headless Claude Code
session with the loop prompt, logs land in `.loops/runs/`, GET `/api/loops`
lists past and running launches, and the dashboard grows a Start button plus
a launch list. A working prototype means the smoke mode launched from the
page reaches its expected marker in the log. Proof:
`python3 -m unittest discover -s tests` plus the smoke launch in the demo.

## 2. Prior art

- `bin/console.py`: the runner seam (`Api.runner`, fixed argv, tested with a
  stub) that the launcher reuses; the mutation POST pattern with the
  `X-Shoggoth` header and Host pinning.
- `CLAUDE.md`: the loop protocol the `loop` prompt points the spawned
  session at.
- `claude` CLI 2.1.234 on this host: `claude -p <prompt> --permission-mode
  acceptEdits` runs headless; stdout is the transcript text.
- The console fiat run's demo evidence layout in `.loops/deliverables/console-demo/`.

## 3. Constraints and non-goals

- Base `main` of laurenceday/shoggoth-interceptor after the console run
  landed; run branch `fiat/console-loop-launcher`.
- Python stdlib only, one HTML/JS page, same as the console.
- Non-goals: streaming the session's output live into the page (the log
  file is the record), managing or killing running sessions from the page,
  multiple concurrent loops, and any change to loop semantics themselves.

## 4. Design options

1. **Spawn `claude -p` detached from the console process.** Chosen. One
   subprocess.Popen with fixed argv, stdout and stderr to a log file under
   `.loops/runs/`, a pidfile beside it. Trade named: the console process
   owns nothing after spawn, so status is inferred from the pid and log
   rather than managed; a crashed console leaves the loop running, which is
   wanted.
2. **Queue a job file for an external runner.** Honest about permissions but
   does not actually start anything, which is the exact complaint. Rejected.
3. **Claude Agent SDK integration.** Richer control, but adds a dependency
   and a long-lived supervisor to a stdlib-only tool. Rejected for the
   prototype.

## 5. Risk register seed

- **Command injection.** The launch argv is fixed; the only variable is
  which of two hard-coded prompts is used. No request data reaches argv.
- **Runaway spawning.** Refuse to launch while a pidfile's process is
  alive; the smoke prompt instructs the session to exit immediately.
- **Secrets.** The spawned session inherits the operator's environment by
  design (it needs gh and the .env keys to work the loop); the console
  still never reads or serialises them, and log files live in gitignored
  `.loops/runs/`. Log filenames are timestamped, content is the session
  transcript.
- **Unattended permissions.** acceptEdits is deliberate and documented;
  the launched session cannot approve its own dangerous actions.
- **Observability.** Each launch logs argv (minus nothing, it is fixed),
  pid, and log path to stderr; /api/loops reports running status from the
  pid check.

## 6. Glossary seeds

- Launch: one spawned headless Claude Code session with a loop prompt.
- Smoke mode: launch that only proves the spawn pipeline, then exits.
- Loop mode: launch that runs one full interceptor loop per CLAUDE.md.
- Pidfile: `.loops/runs/<name>.pid` beside `<name>.log`.

## 7. Sources

- Operator message in this session (the feature request, quoted above).
- CLAUDE.md loop protocol; docs/console-study.md; Claude Code CLI help.

## Boundaries

- **Always.** `python3 -m unittest discover -s tests` before every commit;
  imprimatur on shipped documents; 127.0.0.1 bind unchanged.
- **Ask first.** Any third launch mode; exposing kill/manage controls; any
  new dependency.
- **Never.** Put request data into the launch argv; auto-launch anything on
  server start; read or serialise credentials in the console.

## Success criteria

1. `python3 -m unittest discover -s tests` green, with new tests covering:
   fixed argv for both modes, refusal while a launch is alive, launch
   listing with running status, and no request data reaching argv.
2. POST `/api/start-loop` with `{"mode":"smoke"}` from the dashboard spawns
   a session whose log ends with the smoke marker; `/api/loops` shows it
   running and then finished.
3. The dashboard shows the Start-loop control and the launch list.
