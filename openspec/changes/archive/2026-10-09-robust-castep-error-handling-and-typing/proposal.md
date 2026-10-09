# Proposal: Robust CASTEP reader error handling and ExitCode type annotations

## Why

The in-process CASTEP reader calcfunction (`read_castep_force_constants`) introduced in `migrate-castep-reader-to-calcfunction` catches only `EOFError`. However, Euphonic's CASTEP binary reader also raises `struct.error` (e.g. on truncated inputs under 4 bytes), `OSError` (mismatched Fortran record markers), `ValueError` (unsupported CASTEP version), and `RuntimeError` (valid CASTEP binary lacking force constants). When these errors occur, the calcfunction currently raises an unhandled exception and excepts rather than returning an `ExitCode(300, ...)`, causing calling WorkChains to crash rather than exiting cleanly with `410 ERROR_READ_FAILED`.

Furthermore, functions and workflow outline methods that return `ExitCode` instances (such as `read_castep_force_constants` and workflow step methods like `resolve_force_constants` and `finalize`) lack explicit or accurate return type annotations, obscuring their error-handling contracts from static type analysis and developers.

## What Changes

- Broaden exception handling in `read_castep_force_constants` to catch `EOFError`, `struct.error`, `OSError`, `ValueError`, and `RuntimeError` (with message inspection for missing force constants / invalid file format), returning `ExitCode(300, ...)` instead of excepting. Unrelated `RuntimeError`s continue to propagate.
- Update return type annotations of `read_castep_force_constants` to `ForceConstantsData | ExitCode`.
- Annotate return types of WorkChain outline step methods that can return failure exit codes (`resolve_force_constants`, `finalize`, `compute_spectrum`) with `ExitCode | None` (or `ToContext | ExitCode | None`).
- Add comprehensive unit and workflow test coverage for diverse invalid CASTEP file inputs (sub-4-byte files, corrupt Fortran record markers, CASTEP outputs lacking force constants, and unsupported versions).

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `phonon-workflows`: reading force constants robustly returns dedicated failure exit code `410` for all foreseeable invalid or unreadable CASTEP inputs, not just unexpected EOFs.

## Non-goals

- Refactoring the workflow class hierarchy or moving the force-constants reader into a standalone workchain (`refactor-fcwc` handles that).
- Changing Euphonic's upstream reader behavior or error formatting.
- Altering the exit status code numbers (exit code 300 on the calcfunction and 410 on the workflows remain unchanged).

## Impact

- `src/aiida_pythonjob_ins/workflows/base.py`: exception handling in `read_castep_force_constants`, and type annotations on the calcfunction and `resolve_force_constants`.
- `src/aiida_pythonjob_ins/workflows/dispersion.py`, `src/aiida_pythonjob_ins/workflows/dos.py`, `src/aiida_pythonjob_ins/workflows/tosca.py`: type annotations on outline step methods returning exit codes.
- `tests/test_workflows.py`: new test cases covering sub-4-byte inputs, mismatched record markers, and CASTEP outputs without force constants.
