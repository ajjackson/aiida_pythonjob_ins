## 1. Implementation already completed before OpenSpec adoption

Recorded for provenance. These were delivered against `PLAN.md` §9 and §10 and are
the source of the behaviour captured in `specs/`. No further work.

- [x] 1.1 Scaffold the package: metadata, dependencies, entry points, src layout, Python 3.12 pin, local wheel handling
- [x] 1.2 Implement the Euphonic-wrapping Data nodes with repository-backed JSON storage and round-trip tests
- [x] 1.3 Implement the AiiDA-free operations: CASTEP reader, seekpath band path, mode interpolation
- [x] 1.4 Implement the PythonJob input builders and the serializer/deserializer bridge
- [x] 1.5 Implement the native-type conversions: `StructureData`, `KpointsData`, `BandsData`
- [x] 1.6 Implement `DispersionWorkChain` with end-to-end and conversion tests
- [x] 1.7 Add the minimal CI workflow running the suite with uv on x86-64
- [x] 1.8 Write the README, including the local-wheel setup note
- [x] 1.9 Add the phonon DOS path: operation, `Spectrum1D` to `XyData` conversion, input builder, `DosWorkChain`
- [x] 1.10 Add Phonopy input support and the shared `ForceConstantsWorkChain` base with exclusive-or validation
- [x] 1.11 Build the Sphinx docs stack: AutoAPI, gallery, furo, the `aiida-workchain` directive and the Pages workflow
- [x] 1.12 Write the three gallery tutorials, each rendering results and a provenance graph

## 2. Baseline capture (this change)

- [x] 2.1 Initialise OpenSpec in the project repository and record project context and artifact rules in `openspec/config.yaml`
- [x] 2.2 Write the proposal identifying the eight baseline capabilities
- [x] 2.3 Write the eight delta specs from the source and its test assertions
- [x] 2.4 Write `design.md` recording the as-built decisions, cross-referencing `docs/source/design_notes.rst` rather than duplicating it

## 3. Verify the baseline before freezing it

- [x] 3.1 Install the project with `uv sync` (x86-64, so Euphonic resolves from PyPI and no local wheel is needed)
- [x] 3.2 Run `uv run pytest` and confirm the suite passes, so the specs describe verified behaviour - 26 passed on Python 3.12.13 with euphonic 2.0.0 (from PyPI), aiida-core 2.8.1, aiida-pythonjob 0.5.2, seekpath 2.2.1, numpy 2.5.1, cloudpickle 3.1.2
- [x] 3.3 Run ruff and record pre-existing findings without fixing them - `ruff check` clean; `ruff format --check` would reflow hand-aligned comments in a README example block. CI runs no ruff today, so enabling `format --check` later will fail until that block is reflowed or Markdown is excluded
- [x] 3.4 Reconcile any spec statement contradicted by an actual test result, amending the spec rather than the code - no spec was contradicted by a test. Review did find one over-specification: the workflow spec pinned the exact number of calculation jobs per run, copied from a test assertion. Relaxed to require that heavy steps are dispatchable, that a prepared node is not re-read, and that outputs are provenance-linked; the tests keep their stricter counts as regression guards

## 4. Retire the superseded planning document

- [ ] 4.1 Replace the body of `PLAN.md` with a short historical note pointing to `openspec/specs/`, the archived change, and `docs/source/design_notes.rst`
- [ ] 4.2 Repoint the two `PLAN.md` links in `README.md` (lines 12 and 139) at `openspec/specs/` and the design notes
- [ ] 4.3 Repoint the `PLAN.md` comments in `pyproject.toml` (line 2), `src/aiida_pythonjob_ins/pythonjobs.py` (§3.5) and `src/aiida_pythonjob_ins/serialization.py` (§3.6-§3.7) at `docs/source/design_notes.rst` or the relevant spec
- [ ] 4.4 Confirm no remaining source or documentation file cites a `PLAN.md` section number

## 5. Close out

- [ ] 5.1 Review the specs as a set for gaps or overlaps between capabilities
- [ ] 5.2 Confirm the consolidated "Deferred work" list in `design.md` is complete and accurate before archiving, since it is the durable record of what this baseline deliberately left undone
- [ ] 5.3 Archive the change so the deltas become the main specs in `openspec/specs/`
- [ ] 5.4 Commit from the host, since the container has no push credentials
