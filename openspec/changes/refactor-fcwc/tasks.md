# Tasks

Prerequisite: `migrate-castep-reader-to-calcfunction` is completed and archived, so the CASTEP read calcfunction exists and returns an `ExitCode` on unreadable input.

## 1. Standalone `ForceConstantsWorkChain`

- [x] 1.1 Create `src/aiida_pythonjob_ins/workflows/force_constants.py`: move the CASTEP read calcfunction there from `base.py`, and implement `ForceConstantsWorkChain` per design Decision 4. Update the import of `read_castep_force_constants` in `tests/test_workflows.py` to point to `force_constants.py`. Verify with a new `tests/test_force_constants_workchain.py` covering:
  - `castep_file` gives a `ForceConstantsData` equivalent to `ForceConstants.from_castep` on the same file, created by a `CalcFunctionNode` called by the workflow;
  - `node` gives an output with the input node's UUID and no called processes;
  - both inputs, or neither, raise `ValueError` matching "exactly one";
  - the spec has no `code` or `options` input;
  - a `SinglefileData` of junk bytes ends with `ERROR_READ_FAILED` (410) and no outputs (the outline aborts before `finalize`);
  - no test fixture provides a `Code`.
- [x] 1.2 Register `pythonjob_ins.force_constants = "aiida_pythonjob_ins.workflows.force_constants:ForceConstantsWorkChain"` under `aiida.workflows` in `pyproject.toml`, export it from `workflows/__init__.py`, and add its case to `test_workflow_plugin_registration` in `tests/test_entry_points.py`. Verify that test passes after `uv sync`.
- [x] 1.3 Add an `aiida-workchain` directive for `ForceConstantsWorkChain` to `docs/source/workflows.rst`, with a sentence on standalone use. Verify that the docs build renders its inputs, output, outline and exit code.

## 2. Abstract bases

- [x] 2.1 In `workflows/base.py`, replace the old base with the independent bases `JobDispatchWorkChain` and `FromForceConstantsWorkChain` per design Decision 5. Verify with spec-only tests (no process run):
  - `FromForceConstantsWorkChain.spec()` has a required `force_constants` namespace containing `castep_file` and `node`, declares 402, and has no `code` or `options` input;
  - `JobDispatchWorkChain.spec()` has `code` and `options`, declares 400, and has no `force_constants` input.
- [x] 2.2 Make `ToscaFromModesWorkChain` subclass `JobDispatchWorkChain`, removing its own `code`/`options`/`get_job_metadata()` and re-declaring 400 with its existing message. Verify that `ToscaFromModesWorkChain.exit_codes.ERROR_SUB_PROCESS_FAILED.message` is unchanged and the existing `ToscaFromModesWorkChain` tests pass.

## 3. Rewire the consuming workflows

- [x] 3.1 Make `DispersionWorkChain`, `DosWorkChain` and `ToscaFromForceConstantsWorkChain` subclass `(FromForceConstantsWorkChain, JobDispatchWorkChain)`, with outlines starting `cls.run_force_constants, cls.inspect_force_constants`. Update their module and class docstrings and "Exit Codes" sections: 400 now covers only their own PythonJobs, and 402 is added. Also update the `spectrum` namespace help in `tosca.py`, which says `code` is "shared with the force-constants step". Verify by reading the rendered `workflows.rst` pages.
- [x] 3.2 Update `tests/test_workflows.py` and `tests/test_remote_ssh.py` (`test_dos_workchain_remote_ssh`) to the `force_constants={...}` input form. Then assert in `test_workflows.py`:
  - for both source kinds, exactly one `ForceConstantsWorkChain` is called and its output feeds the next step;
  - the read `CalcFunctionNode` is called by the `ForceConstantsWorkChain` child, not by the consumer;
  - an unreadable file makes a consumer exit with 402 and emit no outputs;
  - in `test_tosca_from_force_constants_workchain`, sub-workchain assertions account for both `ForceConstantsWorkChain` and `ToscaFromModesWorkChain` being called sub-workchains;
  - `test_workchain_requires_exactly_one_source` still raises a `ValueError` matching "exactly one".

  Verify with `uv run pytest tests/test_workflows.py`.
- [x] 3.3 Update the input form in the tutorials (`plot_dispersion.py`, `plot_dos.py`, `plot_phonopy_bands_and_dos.py`, `plot_tosca_from_force_constants.py`), in `README.md` (feature list and example), and in the `workflows.rst` introduction. Don't hand-edit `docs/source/auto_examples/`, which is generated. Verify that the docs build executes all examples.

## 4. Release notes and integration

- [x] 4.1 Add **BREAKING** entries to `CHANGELOG.md` (Unreleased): the namespace input rename with a before/after example, the new 402 exit code, and the class-hierarchy change. Verify the entries against the proposal's What Changes.
- [x] 4.2 Run `uv run ruff check`, `uv run ruff format --check` and `uv run pytest -m "not containerized"`; all pass.

## Workflow follow-up

- The maintainer runs the containerized tests before merge.
- Archive change when implementation is complete.
