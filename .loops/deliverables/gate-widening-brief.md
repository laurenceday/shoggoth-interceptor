# Brief: widen the repository gate, and raise the rigour floor

For an agent working in `laurenceday/shoggoth-interceptor` **outside** a Shoggoth
loop, with the operator's explicit consent recorded below. Do not hand this to
the Shoggoth: it changes files the Shoggoth may not touch, and an agent that can
widen its own gate has no gate.

## Operator consent

Laurence Day, 2026-08-20, in session: the gate is to permit writes everywhere
**except** the `wildcat-finance` organisation, with `wildcat-finance/skills`
exempt from that protection. Pull requests are permitted on anything the gate
allows. The team's concern is core protocol code and frontend code, not the
skills substrate the Shoggoth runs on.

That consent covers the intent. It does not pre-approve any particular
implementation, and it does not cover the two items under "Raise before
building" below, which need answers before code.

## What the gate does today

`bin/repository-gate.py` is fail-closed and allow-nothing-by-default.
`validate_policy` accepts one entry per organisation, `mode` must be the literal
`sandbox-only`, `sandbox` is a single repository string that must belong to that
organisation, and `github_login` must match the active `gh` login. `decide`
denies three ways: no policy for the organisation, target is not the sandbox,
login mismatch. Adding a policy goes through `init`, which asks for consent at a
prompt and records the login only after a yes.

`bin/install-guardrails.sh` installs the gate as a pre-push hook on every clone.
`bin/verify-gate.py` and `.github/workflows/gate-integrity.yml` pin the digests
of both files. `CLAUDE.md` puts both outside the Shoggoth's authority.

## What to build

Invert the default, and keep every other property.

1. **Default allow, named protection.** A new mode, `protected-orgs`, where the
   policy names organisations that are protected and, per organisation, the
   repositories exempt from that protection. `wildcat-finance` protected,
   `wildcat-finance/skills` exempt. Any organisation not named is permitted.
2. **Keep the login binding.** The active `gh` login must still match the login
   recorded at consent time. Losing that turns a policy file into an
   authorisation, and a policy file is not a credential.
3. **Keep `init` as the only writer of policy**, and keep its prompt. Adding a
   protected organisation, or exempting a repository inside one, is a consent
   event. Widening by hand-editing JSON must still fail `validate_policy`.
4. **Update the pins and the tests in the same change.** `verify-gate.py`, the
   `gate-integrity` workflow and `tests/test_guardrails.py` all move with the
   gate. A digest left stale is a gate that no longer proves anything.
5. **Fixtures for the new refusals**, each seen failing before the fix: a
   protected organisation denied, an exempt repository inside it allowed, an
   unprotected organisation allowed, a login mismatch denied, and a
   hand-widened policy refused by validation.

## Raise before building

**`SHOGGOTH_GUARDRAILS_FILE` repoints the gate at any file**, with no digest
check and no consent prompt. It is tolerable beside an allow-nothing default. It
is not tolerable beside an allow-by-default gate, because the same variable now
switches protection off rather than on. Remove it, or constrain it to a path
inside the repository that `verify-gate.py` pins.

## One consequence worth stating out loud

`wildcat-finance/skills` holds Fiat, the phase skills, the Promise Machine
contract and the guardrail prose. Exempting it means the Shoggoth may open pull
requests against its own instructions. The digest pins cover the gate itself,
but the exemption should be recorded as deliberate rather than discovered
later by someone reading the policy file.

## Raise the rigour floor

Add to `CLAUDE.md`, in the loop protocol, and apply it from the next loop:

> Apply maximum rigour to every ticket, in every repository, sandbox or not. A
> ticket reaches the backlog and stays there because it is tricky, and it is
> often tricky for exactly the reasons rigour uncovers: an envelope nobody
> sized, a semantic nobody settled, a test that passes while measuring the
> wrong thing. A sandbox lowers the cost of being wrong. It does not lower the
> standard of evidence, and treating it as though it does produces work that
> looks finished and answers nothing.
>
> In practice that means: establish the baseline before changing anything, so
> breakage can be attributed. Apply each candidate to the code instead of
> arguing it on paper. Classify every failure rather than counting them. Pin
> boundaries
> deterministically rather than quoting a fuzz counterexample. State what a
> measurement does not establish. And when a test passes, check that it passed
> for the reason claimed.

The 853 loop is the worked example. Two candidate mitigations both looked sound
as arithmetic; applying them to `src/` showed that each overflows the debt
index's `uint120` storage at a rate an operator can configure, one after 97 days
and the other after 161. No amount of reading found that. Three of that loop's
own tests were also wrong on the first pass in ways that still produced passing
suites, and each was caught by asking what the number actually measured.
