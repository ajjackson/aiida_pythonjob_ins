## Why

This project was built to completion as a proof-of-concept before OpenSpec was
adopted, using an ad-hoc `PLAN.md` as its only planning document. The behaviour
that resulted is real and tested, but it is not described anywhere as
requirements: `PLAN.md` interleaves original intent, architecture rationale,
progress checkboxes and open questions in a single narrative, so there is no
baseline for future changes to be proposed *against*.

This change captures the already-implemented behaviour as OpenSpec capabilities.
**It documents existing behaviour rather than proposing new work** - no source
code changes, no behavioural change. Its purpose is to give the remaining
roadmap items (abinslib/resins wrappers, the entry-point audit, the docs
generation items, ruff in CI) real specs to attach their deltas to.

## What Changes

- Establish eight baseline capabilities describing the plugin as it exists today,
  derived from the source and its test suite.
- Record the architecture and the decisions taken during implementation in
  `design.md`, sourced from `PLAN.md` §3, §6 and its "Implementation notes /
  decisions made" log.
- Retire `PLAN.md` in favour of the specs, folding its goals, out-of-scope list
  and reference links into `README.md` and deleting the file, so it stops being a
  second source of truth. It remains in git history.
- No changes to runtime behaviour, dependencies or CI. The only edits to `src/`,
  `pyproject.toml` and `README.md` are comments and links repointed away from the
  deleted file.

## Capabilities

### New Capabilities

- `euphonic-data-nodes`: AiiDA `Data` nodes wrapping Euphonic objects -
  repository-backed JSON storage, type validation, and the
  `ForceConstantsData` / `QpointPhononModesData` / `EuphonicCrystalData`
  classes with their reader constructors.
- `aiida-native-conversions`: mapping Euphonic objects onto AiiDA's native
  materials-science types - `Crystal` to and from `StructureData`, q-points to
  `KpointsData`, `QpointPhononModes` to `BandsData` (including consistency
  validation), and `Spectrum1D` to `XyData`.
- `phonon-operations`: the AiiDA-free Euphonic operations - CASTEP and Phonopy
  force-constants readers, seekpath band-path construction, Fourier
  interpolation of phonon modes, dispersion, and adaptively broadened density
  of states.
- `pythonjob-execution`: running those operations as AiiDA `PythonJob`
  processes - the `prepare_*_inputs` builders, the serializer/deserializer
  bridge between custom Data nodes and Euphonic objects, input-file staging,
  by-reference function pickling, and the standard Computer/Code hooks.
- `phonon-workflows`: the WorkChains - a shared force-constants base accepting
  exactly one of a CASTEP file or a prepared node, plus the dispersion and DOS
  workflows, their outputs, exit codes and provenance shape.
- `plugin-packaging`: distribution and discoverability - the `aiida.data` and
  `aiida.workflows` entry points, naming, the dependency-pinning policy, the
  Python version pin, the build backend, and the aarch64 Euphonic wheel
  workaround.
- `testing-and-ci`: the hermetic test session (ephemeral `AIIDA_PATH` config and
  SQLite-backed fixtures, requiring no PostgreSQL), the equivalence-testing
  approach, and the GitHub Actions workflows.
- `documentation`: the Sphinx site - AutoAPI reference, the runnable
  sphinx-gallery tutorials, WorkChain specifications rendered via the
  `aiida-workchain` directive, and the Pages build.

### Modified Capabilities

None - `openspec/specs/` is currently empty, so every capability here is new.

## Non-goals

- Implementing anything new. Twelve follow-up items are deliberately left out and
  recorded together in `design.md` under "Deferred work"; each should become its
  own change proposed against these baseline specs.
- Re-litigating decisions already taken. Where the implementation settled a
  question, the spec records the resulting behaviour and `design.md` records the
  reasoning; neither reopens it.
- Specifying behaviour that does not exist yet. Requirements describe implemented
  behaviour, though not all of it is covered by tests: several invariants were
  verified by hand while writing these specs, and closing that gap is a recorded
  follow-up.
- Improving test coverage or docs content, even where gaps are visible while
  writing the specs. Those become follow-up changes.

## Impact

- **Added**: `openspec/specs/` gains eight capability specs once this change is
  archived; `openspec/config.yaml` carries the project context and artifact
  rules.
- **Removed**: `PLAN.md`, after its surviving content moved to `README.md`,
  `design.md` and the specs.
- **Modified, comments and prose only**: `README.md` gains the goals and
  references sections and loses its two `PLAN.md` links; `pyproject.toml`,
  `src/aiida_pythonjob_ins/pythonjobs.py` and
  `src/aiida_pythonjob_ins/serialization.py` have comments repointed at named
  sections of `docs/source/design_notes.rst`.
- **Unaffected**: `tests/`, `docs/` content, `uv.lock` and
  `.github/workflows/`. No dependency, API or runtime behaviour changes.
- **Verification**: the baseline is derived from the source and its test
  assertions, and was then checked against a full run of the suite on x86-64
  Linux, where Euphonic resolves from PyPI and no local wheel is needed. All 26
  tests pass and `ruff check` is clean. One pre-existing finding is recorded and
  deliberately left unfixed: `ruff format` would reflow hand-aligned comments in
  a README example block, which CI does not currently detect because it runs no
  ruff step.
