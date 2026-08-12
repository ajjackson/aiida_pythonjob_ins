## Context

See `proposal.md` - Why, for the gap and the evidence behind it. The relevant
constraints for the approach:

- The registered set is declared in `pyproject.toml` under
  `[project.entry-points."aiida.data"]` and `[project.entry-points."aiida.workflows"]`.
- Entry points are resolved from installed distribution metadata, so a check is
  meaningful only against an installed (including editable) environment. An
  editable install picks up edits to Python sources immediately, but *not* changes
  to entry-point declarations, which require reinstalling.
- The plugin factories need AiiDA configuration but not a loaded profile. The
  existing `conftest.py` already establishes an ephemeral configuration before
  AiiDA is imported, so no new fixture is needed and the checks add no measurable
  runtime.

## Goals / Non-Goals

**Goals:** verify each documented entry-point name resolves to its class, in a
form that stays honest as classes are added.

**Non-Goals:** the other three test gaps in `document-poc-baseline` design item 6;
any change to the registrations themselves, which are correct today; and testing
AiiDA's own plugin machinery, which is upstream's responsibility.

## Decisions

### One explicit case per registered class, not a loop over declared entry points

Two shapes were considered.

*Enumerate at runtime*: read this distribution's entry points from
`importlib.metadata` and assert each loads. Self-maintaining - a sixth class is
covered the moment it is declared.

*Explicit per-class cases*: a parametrised list pairing each documented name with
its expected class.

**Chosen: explicit per-class cases.** The enumeration approach verifies internal
consistency - that whatever is declared resolves - but the contract is the
documented *name*. Renaming `pythonjob_ins.force_constants` in `pyproject.toml`
keeps an enumeration test green while breaking every user who follows the
documentation, and silently changing the `node_type` written into stored data.
An explicit list is a second, independent statement of the names, so the two must
be changed together for the suite to pass.

The cost is that a class registered with no test case is not caught
automatically. That is accepted: the spec requires per-class coverage, the
parametrised list makes the omission visible in review, and the alternative
protects the weaker property. Nothing prevents adding an enumeration check later
as a complement.

### Assert the class object, not just successful resolution

The factory returning *something* proves the entry point exists; comparing against
the imported class proves it points at the intended target. This catches a
declaration whose module path drifts to a different class after a refactor - the
failure mode the entry-point strings in `pyproject.toml` are most prone to, since
they are strings no import checker validates.

## Risks / Trade-offs

- **The test passes against a stale editable install.** Entry-point metadata is
  written at install time, so editing `pyproject.toml` without reinstalling leaves
  the old registrations in place, and the suite can pass or fail for reasons that
  do not match the working tree. → CI installs from scratch, so the authoritative
  run is unaffected; note the reinstall requirement in the test module so a
  developer chasing a confusing local result finds the explanation.
- **A newly registered class silently lacks a case.** → Accepted, with the
  reasoning above; the spec states the obligation per class.

## Migration Plan

Not applicable - additive test coverage, no production behaviour changes, nothing
to roll back beyond removing the test.

Ordering: `document-poc-baseline` must be archived before this change is archived,
because the `testing-and-ci` main spec that this delta adds to does not exist
until then. Implementation itself has no such dependency.
