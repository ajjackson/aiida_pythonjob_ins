# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The `read_castep_force_constants` calcfunction, which reads a CASTEP
  `SinglefileData` into a `ForceConstantsData` in-process and returns an
  `ExitCode` (status 300) when the file is unreadable instead of raising.
- The `410 ERROR_READ_FAILED` exit code on `ForceConstantsWorkChain`.

### Changed

- The `read_castep_force_constants` calcfunction now catches all foreseeable
  Euphonic reader errors -- `EOFError`, `struct.error` (truncated files under 4
  bytes), `OSError` (mismatched Fortran record markers), `ValueError`
  (unsupported CASTEP versions), and `RuntimeError` (valid CASTEP output lacking
  force constants) -- returning `ExitCode(300, ...)` instead of excepting.
  Unrelated `RuntimeError`s continue to propagate as Excepted processes.
- Return type annotations added to `read_castep_force_constants` (`ForceConstantsData
  | ExitCode`) and to WorkChain outline step methods (`ExitCode | None`,
  `ToContext | ExitCode | None`) that can return failure exit codes.
- **BREAKING**: A failed force-constants read now exits with `410 ERROR_READ_FAILED`
  instead of `400 ERROR_SUB_PROCESS_FAILED`. Exit code `400` now means only that a
  `PythonJob` step did not finish successfully.
- Workflows that start from a CASTEP file (`DispersionWorkChain`,
  `DosWorkChain`, `ToscaFromForceConstantsWorkChain`) now read it in-process
  through the `read_castep_force_constants` calcfunction, rather than a
  dispatched `PythonJob` plus a separate assignment step. The read is recorded
  as its own `CalcFunctionNode` in the provenance graph (it can be cached) but
  no longer incurs the ~2.8 s of job machinery for ~0.1 s of work.

### Removed

- The `should_read_castep`, `read_force_constants` and `assign_force_constants`
  outline steps of `ForceConstantsWorkChain` are replaced by a single
  `resolve_force_constants` step.

[Unreleased]: https://github.com/ajjackson/aiida_pythonjob_ins/tree/HEAD
