# Proposal: Compose `ForceConstantsWorkChain` into the force-constants workflows

## Why

Turning an input into a `ForceConstantsData` will grow more formats and multi-step imports, but today that logic is an abstract base whose steps every subclass lists in its own outline, so each added step changes every consumer. A standalone `ForceConstantsWorkChain`, composed as a sub-workflow, keeps that logic in one unit that consumers don't need to know the inside of, and that can also be launched alone.

Prerequisite: `migrate-castep-reader-to-calcfunction`, which provides the in-process CASTEP read calcfunction that returns an `ExitCode` on unreadable input.

## What Changes

- `ForceConstantsWorkChain` becomes a public, standalone workflow: exactly one of `castep_file` (`SinglefileData`) or `node` (`ForceConstantsData`) in, one `force_constants` output out. It takes no `code` or `options`. It is registered as the `pythonjob_ins.force_constants` workflow entry point and documented.
- `DispersionWorkChain`, `DosWorkChain` and `ToscaFromForceConstantsWorkChain` always run `ForceConstantsWorkChain` as a sub-workflow, with its inputs exposed under a `force_constants` namespace.
- **BREAKING**: source inputs move into the namespace: `castep_file=f` becomes `force_constants={"castep_file": f}`, and `force_constants=node` becomes `force_constants={"node": node}`.
- **BREAKING**: when the source cannot be resolved, these workflows now exit with a new code, `ERROR_SUB_PROCESS_FAILED_FORCE_CONSTANTS`. The specific reason is recorded on the sub-workflow.
- **BREAKING**: these workflows no longer subclass `ForceConstantsWorkChain`. They combine two independent abstract bases, one for the force-constants source and one for `code`/`options` handling. `ToscaFromModesWorkChain` uses only the second, which removes its duplicate definitions.
- A `CHANGELOG.md` entry records the breaking changes.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `phonon-workflows`: the force-constants source becomes a standalone workflow. Consuming workflows group its inputs under one namespace, delegate to it, and report its failure with a distinct exit code.
- `plugin-packaging`: `ForceConstantsWorkChain` is added to the registered workflows.

## Non-goals

- New force-constants formats (Phonopy, Euphonic JSON, VASP). These are later work, and so is the command-line import tool that needs format detection.
- Changing how CASTEP files are read (see the prerequisite change).
- Changing `ToscaFromForceConstantsWorkChain`'s `spectrum` namespace, including its existing `spectrum.options` overlap.
- Cleaning up the read builders (`prepare_read_force_constants_inputs`, `prepare_read_phonopy_inputs`). After this change no workflow uses the CASTEP one, and the Phonopy one becomes unnecessary once `ForceConstantsWorkChain` accepts Phonopy input. That change should decide whether to remove them or turn them into builders that read force constants already on the remote computer (`RemoteData`). Either way, `pythonjob-execution` (the builder list and the staging requirement), the operations-without-AiiDA tests and the containerized SSH test, which only runs in the containerized suite, need revisiting. Until then the CASTEP builder stays, as the spec requires.

## Impact

- `src/aiida_pythonjob_ins/workflows/`: new `force_constants.py`; `base.py` becomes two independent abstract bases; `dispersion.py`, `dos.py` and `tosca.py` are rewired; `__init__.py` exports the new workflow.
- `pyproject.toml`: one new `aiida.workflows` entry point.
- Tests: `test_workflows.py`, `test_remote_ssh.py`, `test_entry_points.py`, plus a new `test_force_constants_workchain.py`.
- Docs: `workflows.rst`, the tutorials (`plot_dispersion.py`, `plot_dos.py`, `plot_phonopy_bands_and_dos.py`, `plot_tosca_from_force_constants.py`), `README.md`, `CHANGELOG.md`.
