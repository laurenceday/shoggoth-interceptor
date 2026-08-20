# Study: general GitHub issue resolver

## Assumptions

1. Version one remains a local, single-operator tool.
2. Resolution means a Fiat delivery ending in receipts, a local patch, or a
   policy-permitted pull request. It does not merge, close, assign, or comment.
3. GitHub issues are canonical. ZenHub may add metadata but is not required.
4. An organisation is write-protected except for one sandbox repository named
   during first-run setup.

## Problem and proof

Replace the Wildcat Product Planning reader with configured GitHub sources,
repository-qualified issue identity, explicit selection and target routing, and
a generic write gate. The proof is:

```bash
python3 -m unittest discover -s tests
python3 bin/verify-gate.py
python3 bin/repository-gate.py init OWNER OWNER/SANDBOX
```

The suite must cover duplicate issue numbers across repositories, incomplete
fetches, malformed GitHub input, unknown organisations, non-sandbox writes,
and mismatched GitHub identities.

## Present shape and choice

The original reader held one source repository and one ZenHub workspace in
constants. Numeric exclusions and deliverable paths assumed issue numbers were
globally unique. The console repeated the repository, pipeline, and ranking
rules. The write gate special-cased `wildcat-finance/*`.

Two options were considered: parameterise those constants, or introduce a
small configured core. Parameterisation leaves identity and write authority
implicit. The configured core is chosen: `config/resolver.json` owns sources,
selectors, and routes; snapshots use `owner/repo#number`; the gate owns only
organisation and sandbox write policy. This keeps the existing local loop and
trades away hosted operation.

## Constraints and non-goals

- Python standard library only; no new dependency or service.
- Read and write credentials stay separate.
- Issue bodies and comments remain untrusted data.
- Fetches are bounded and atomically replace only complete state.
- Repository targets come from configuration, never issue prose.
- No webhook queue, tenancy, automatic GitHub issue mutation, merge, or close.

## Risk seed

- Duplicate numbers: key all state and receipts by repository-qualified ref.
- Partial fetch: retain the last complete snapshot when any source fails.
- Prompt injection: issue text cannot supply commands, paths, or authority.
- Wrong target: same-repository default or explicit configured route.
- Policy widening: unknown organisations and non-sandbox repositories deny.
- Credential confusion: reads use `GITHUB_READ_PAT`; writes use the active `gh`
  login after policy verification.
- Drift: pin gate and installer digests and check their required call order.

## Five disciplines

- `hexaemeron:ephoros`: fetch, gate, and completion output answer what happened.
- `hexaemeron:phylax`: HTTP, issue text, credentials, paths, and subprocesses
  cross off-chain boundaries.
- `hexaemeron:metron`: no performance claim; correctness dominates this local
  one-issue loop.
- `hexaemeron:elenchus`: each observed failure earns a focused guard test.
- `hexaemeron:hypomnema`: issue identity, target routing, and write policy live
  in this study and the operating contract.

## Build boundaries

- Always: full tests, gate verification, prose check, atomic local state.
- Ask first: dependency, CI change, issue mutation, additional write-enabled
  repository, or hosted deployment.
- Never: expose a credential, execute issue text, infer a target from prose,
  bypass the hook or pull-request wrapper, or widen policy to finish a loop.
