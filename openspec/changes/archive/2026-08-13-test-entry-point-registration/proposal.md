## Why

The `plugin-packaging` capability requires each data type and workflow to load
through AiiDA's standard plugin factories under a documented entry-point name, but
nothing verifies it: every test imports the classes directly. The gap is not
uniform, and its shape was established by experiment rather than assumption.

AiiDA refuses to store a `Data` subclass that has no registered entry point
(`StoringNotAllowed`), so the existing tests do prove that *some* registration
exists for the three data types. Two holes remain:

- Current tests pass imported class objects directly to workflows, relying on
  `Process.build_process_type` falling back to fully qualified import paths when
  no entry point is found. Both workflow entry points could be deleted from
  `pyproject.toml` without breaking any test.
- Neither path checks the *name*. Renaming an entry point would keep every test
  passing while breaking `DataFactory` for users and changing the `node_type`
  recorded in stored data, since `node_type` is derived from the entry-point
  string.

This is the smallest and most self-contained of the four test gaps recorded in
`document-poc-baseline` design item 6, and unlike the others it needs no new
fixture data.

## What Changes

- Add a test asserting that each registered class is returned by its factory
  (`DataFactory` or `WorkflowFactory`) for its documented entry-point name, one
  case per class, so the check is visible and extends naturally as classes are
  added.
- Add a requirement to `testing-and-ci` making that coverage a stated obligation
  rather than an incidental test, so a future class without a factory test is a
  spec violation and not merely an omission.
- No production code changes. All five entry points are correctly registered
  today; this change closes the verification gap, it does not fix a defect.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `testing-and-ci`: adds a requirement that plugin registration is verified
  through the factories, covering every registered class rather than a fixed list.

## Impact

- `tests/` gains one small module (or one class in an existing module); no
  fixtures, no test data, no new dependencies.
- Runtime cost is negligible: the factories resolve entry points without a
  profile, a database or a job submission.
- Depends on `document-poc-baseline` being archived first, since the
  `testing-and-ci` main spec this delta modifies does not exist until then.
- Closes the fourth sub-item of `document-poc-baseline` design item 6; the other
  three (round-trip fidelity, scientific validity, imaginary-mode handling) remain
  deferred and are deliberately out of scope here.
