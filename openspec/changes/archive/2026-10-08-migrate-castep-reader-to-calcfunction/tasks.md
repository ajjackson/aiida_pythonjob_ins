# Tasks

## 1. In-process CASTEP read calcfunction

- [x] 1.1 Spike: pass `ForceConstants.from_castep` a file of junk bytes, a truncated copy of a valid `.castep_bin`, and an empty file. Record the exception types raised in the calcfunction's docstring. Verify that the recorded types match what a short script reproduces.
- [x] 1.2 Implement `read_castep_force_constants` in `workflows/base.py` per design Decisions 1–2, catching only the types from 1.1. Verify with unit tests that run without any `Code` or `Computer` fixture:
  - a valid file gives a `ForceConstantsData` equivalent to `ForceConstants.from_castep` on the same file, with the `CalcFunctionNode` linked to the input file;
  - a junk file gives a node that is finished with exit status 300, has a message naming the cause, and has no outputs.

## 2. Single source-resolution step

- [x] 2.1 Replace `should_read_castep`, `read_force_constants` and `assign_force_constants` with `resolve_force_constants`, and add `410 ERROR_READ_FAILED` (design Decisions 3–4). Switch the outlines of `DispersionWorkChain`, `DosWorkChain` and `ToscaFromForceConstantsWorkChain` to start with `cls.resolve_force_constants`. Update docstrings:
  - module docstrings of `base.py`, `dispersion.py` and `dos.py`: no PythonJob read, and point to `prepare_read_force_constants_inputs` as the file-staging example;
  - "Exit Codes" sections: 400 covers PythonJobs only, and 410 is added;
  - the `castep_file` port help.

  Verify that `uv run ruff check` passes and that the rendered `workflows.rst` pages show the new outline and exit codes.
- [x] 2.2 Update `tests/test_workflows.py`:
  - CASTEP-sourced runs call exactly one `CalcFunctionNode` from the read calcfunction, and their `CalcJobNode` counts drop by one (dispersion 2→1, DOS 2→1; adjust the options-propagation loop accordingly);
  - a junk `SinglefileData` makes `DispersionWorkChain` exit with 410 and emit no outputs, without any job being run;
  - `test_tosca_from_force_constants_failure_is_distinguishable` still asserts 401 ≠ 400.

  Verify with `uv run pytest tests/test_workflows.py`.

## 3. Release notes and integration

- [x] 3.1 Create `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, with an `Unreleased` section recording the in-process read and the **BREAKING** change to the read-failure exit code (400 → 410). Verify the entries against the proposal's What Changes.
- [x] 3.2 Run `uv run ruff check`, `uv run ruff format --check` and `uv run pytest -m "not containerized"`; all pass.

## Workflow follow-up

- The maintainer runs the containerized tests before merge.
- Archive before `refactor-fcwc`, which modifies the same `phonon-workflows` spec and moves the read step.
