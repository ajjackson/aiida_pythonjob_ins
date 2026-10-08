# Tasks

## 1. Robust CASTEP reader exception handling

- [ ] 1.1 Broaden exception handling in `read_castep_force_constants` (`workflows/base.py`) to catch `(EOFError, struct.error, OSError, ValueError)` and `RuntimeError` (matching `"Force constants matrix could not be found"` or `"Invalid file"` in error message). Ensure unexpected `RuntimeError`s re-raise. Verify with unit tests in `tests/test_workflows.py`:
  - 1-byte and 3-byte truncated files return `ExitCode(300, ...)`
  - mismatched record markers return `ExitCode(300, ...)`
  - `RuntimeError` with missing force constants message returns `ExitCode(300, ...)`
  - unrelated `RuntimeError` propagates as an unhandled exception

## 2. ExitCode type annotations

- [ ] 2.1 Update the return type annotation of `read_castep_force_constants` in `workflows/base.py` to `ForceConstantsData | ExitCode`. Verify that `uv run ruff check` passes.
- [ ] 2.2 Annotate return types of outline step methods across workflows:
  - `ForceConstantsWorkChain.resolve_force_constants` -> `ExitCode | None`
  - `DispersionWorkChain.finalize` -> `ExitCode | None`
  - `DosWorkChain.finalize` -> `ExitCode | None`
  - `ToscaFromModesWorkChain.finalize` -> `ExitCode | None`
  - `ToscaFromForceConstantsWorkChain.compute_spectrum` -> `ToContext | ExitCode | None`
  - `ToscaFromForceConstantsWorkChain.finalize` -> `ExitCode | None`
  Verify that `uv run ruff check` passes and documentation builds without warnings.

## 3. Workflow integration and changelog

- [ ] 3.1 Add integration tests in `tests/test_workflows.py` verifying that `DispersionWorkChain` and `DosWorkChain` launched with a sub-4-byte file or corrupt record markers terminate with `410 ERROR_READ_FAILED`, emit no outputs, and dispatch no `CalcJobNode`s. Verify with `uv run pytest tests/test_workflows.py`.
- [ ] 3.2 Add an entry to `CHANGELOG.md` under `[Unreleased]` recording the robust reader error handling and type annotations. Verify that `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest -m "not containerized"` pass.
