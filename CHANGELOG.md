# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The `read_castep_force_constants` calcfunction, which reads a CASTEP
  `SinglefileData` into a `ForceConstantsData` in-process and returns an
  `ExitCode` (status 300) when the file is unreadable instead of raising.
- `ForceConstantsWorkChain` as a public, standalone workflow (registered as the
  `pythonjob_ins.force_constants` entry point) that resolves a force-constants
  source -- a `castep_file` (`SinglefileData`) or a `node` (`ForceConstantsData`)
  -- into a `force_constants` output. It dispatches no jobs and takes no `Code`.
- The `402 ERROR_SUB_PROCESS_FAILED_FORCE_CONSTANTS` exit code on the workflows
  that start from force constants.
- The `410 ERROR_READ_FAILED` exit code on `ForceConstantsWorkChain`.

### Changed

- The `read_castep_force_constants` calcfunction now catches all foreseeable
  Euphonic reader errors (truncated, corrupt, or non-phonon CASTEP inputs),
  returning `ExitCode(300, ...)` instead of excepting. Unrelated `RuntimeError`s
  continue to propagate as Excepted processes.
- Return type annotations added to `read_castep_force_constants` and WorkChain
  outline step methods that can return failure exit codes.
- **BREAKING**: A failed force-constants read now exits with `410 ERROR_READ_FAILED`
  instead of `400 ERROR_SUB_PROCESS_FAILED`. Exit code `400` now means only that a
  `PythonJob` step did not finish successfully.
- Workflows that start from a CASTEP file (`DispersionWorkChain`,
  `DosWorkChain`, `ToscaFromForceConstantsWorkChain`) now read it in-process
  through the `read_castep_force_constants` calcfunction, rather than a
  dispatched `PythonJob` plus a separate assignment step. The read is recorded
  as its own `CalcFunctionNode` in the provenance graph (it can be cached) but
  no longer incurs the ~2.8 s of job machinery for ~0.1 s of work.
- **BREAKING**: The force-constants source inputs moved into a `force_constants`
  namespace. The CASTEP file and the prepared node are now grouped under the
  ports of `ForceConstantsWorkChain`: `castep_file` becomes
  `force_constants={"castep_file": f}` and `force_constants=node` becomes
  `force_constants={"node": node}`.
- **BREAKING**: When the force-constants source cannot be resolved,
  `DispersionWorkChain`, `DosWorkChain` and `ToscaFromForceConstantsWorkChain`
  now exit with `402 ERROR_SUB_PROCESS_FAILED_FORCE_CONSTANTS` (the
  `ForceConstantsWorkChain` sub-workflow failed), distinct from `400` (a
  `PythonJob` step failed). The read-failure code `410 ERROR_READ_FAILED` now
  lives only on `ForceConstantsWorkChain`.
- **BREAKING**: The workflows that start from force constants no longer subclass
  `ForceConstantsWorkChain`. They combine two independent abstract bases --
  `FromForceConstantsWorkChain` (the `force_constants` source) and
  `JobDispatchWorkChain` (`code`/`options` dispatch) -- and run
  `ForceConstantsWorkChain` as a sub-workflow. `ToscaFromModesWorkChain` now
  subclasses only `JobDispatchWorkChain`, removing its duplicate `code`,
  `options` and `get_job_metadata()` definitions.

### Removed

- The `should_read_castep`, `read_force_constants` and `assign_force_constants`
  outline steps of `ForceConstantsWorkChain` are replaced by a single
  `resolve_force_constants` step.
- The `resolve_force_constants` step (and the `ForceConstantsWorkChain` base
  that held it) is replaced by the `run_force_constants` / `inspect_force_constants`
  steps on `FromForceConstantsWorkChain`, which delegate to the standalone
  `ForceConstantsWorkChain`. The duplicated `code`, `options` and
  `get_job_metadata()` definitions on `ToscaFromModesWorkChain` are removed.

[Unreleased]: https://github.com/ajjackson/aiida_pythonjob_ins/tree/HEAD
