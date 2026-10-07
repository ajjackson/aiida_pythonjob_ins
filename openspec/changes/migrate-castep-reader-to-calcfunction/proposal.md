# Proposal: Read CASTEP force constants in-process

## Why

Workflows that start from a CASTEP file read it through a dispatched `PythonJob`. The read itself takes about 0.1 s, but the job machinery (staging, subprocess, interpreter start-up, retrieval) adds about 2.8 s. An in-process calcfunction keeps the read as its own provenance step without that overhead.

## What Changes

- Add an internal calcfunction that reads a CASTEP `SinglefileData` into a `ForceConstantsData`. If the file is unreadable, it returns an `ExitCode` instead of raising.
- Workflows that start from force constants (`DispersionWorkChain`, `DosWorkChain`, `ToscaFromForceConstantsWorkChain`) resolve their source in one in-process step instead of a dispatched read job plus an assignment step.
- **BREAKING**: a failed read now exits with `410 ERROR_READ_FAILED` instead of `400 ERROR_SUB_PROCESS_FAILED`. The code 400 now means only that a PythonJob failed.
- Add `CHANGELOG.md`, starting with this change's entry.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `phonon-workflows`: reading force constants is no longer a dispatched heavy step. Cheap steps must not be dispatched, and a failed read has its own exit code.

## Non-goals

- Changing the compute steps, which stay `PythonJob`s.
- Restructuring the workflow classes or the force-constants inputs. That is `refactor-fcwc`, which builds on this change.
- Removing `prepare_read_force_constants_inputs`. It remains the example of PythonJob file staging, exercised by `tests/test_remote_ssh.py`.

## Impact

- `src/aiida_pythonjob_ins/workflows/base.py`: the new calcfunction and a single source-resolution step; `dispersion.py`, `dos.py` and `tosca.py` get shorter outlines and updated docstrings.
- `tests/test_workflows.py`: read-step and exit-code assertions.
- `CHANGELOG.md`: new file.
