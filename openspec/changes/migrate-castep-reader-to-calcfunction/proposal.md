# Proposal: Migrate CASTEP File Reading to In-Process Calcfunction and Refactor Workflow Mixins

## Why

Every workflow that starts from a CASTEP file (`DispersionWorkChain`, `DosWorkChain`, and `ToscaFromForceConstantsWorkChain`) currently executes `read_force_constants` as an out-of-process `PythonJob` CalcJob. 

While this was originally introduced to demonstrate file staging via `PythonJob`, reading force constants from a binary file (`ForceConstants.from_castep`) takes only ~0.1 seconds of actual CPU time. Launching it as a `PythonJob` forces the AiiDA engine to write staging scripts, invoke background shell subprocesses, spawn a fresh Python interpreter, and load scientific libraries (a ~2.8-second base penalty). 

Migrating CASTEP file reading to an in-process `calcfunction` retains complete provenance tracking on the workflow graph and eliminates nearly 3 seconds of unnecessary process orchestration. Furthermore, because reading force constants no longer requires a remote `Code` or scheduler `options`, keeping `code` on `ForceConstantsWorkChain` would result in an unused input port. Decoupling the force constants source concern from the job dispatch concern via capability mixins cleans up the object-oriented structure, allows `ForceConstantsWorkChain` to run standalone without an unused `code` argument, streamlines the outline into a single synchronous step, and eliminates duplicated `code`/`options` declarations across workflows.

## What Changes

- Add a parent-side `calcfunction` `read_castep_force_constants` in `src/aiida_pythonjob_ins/workflows/base.py` that reads a `SinglefileData` CASTEP binary into a `ForceConstantsData` node in-process.
- Add `_compose_validators` helper to safely combine AiiDA `PortNamespace.validator` callables without clobbering existing namespace validators.
- Introduce `ForceConstantsMixin` for workflows that obtain force constants from either a CASTEP file or a pre-built node, consolidating the source validation and synchronous resolution into a single `resolve_force_constants` step.
- Introduce `JobDispatchMixin` for workflows that dispatch compute jobs to an AiiDA `Code`, centralizing the `code` input, optional `options` input, `get_job_metadata()` helper, and exit code 400.
- Update `ForceConstantsWorkChain` to use `ForceConstantsMixin` as a standalone WorkChain without unused `code` or `options` ports, exposing `force_constants` as its output.
- Update `DispersionWorkChain`, `DosWorkChain`, and `ToscaFromForceConstantsWorkChain` to inherit `ForceConstantsMixin` and `JobDispatchMixin`, streamlining their outlines to call `resolve_force_constants`.
- Update `ToscaFromModesWorkChain` to inherit `JobDispatchMixin`, eliminating duplicated `code`, `options`, and `get_job_metadata()` definitions.
- Update `tests/test_workflows.py` to reflect that reading force constants creates a `CalcFunctionNode` rather than a `CalcJobNode`.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `phonon-workflows`: Clarify that force constants reading from a CASTEP file during workflow execution is performed as an in-process `calcfunction` step rather than a dispatched `PythonJob`. A workflow that does not dispatch any remote jobs SHALL NOT require a `Code` or `options` input port.

## Non-goals

- Changing the compute-heavy steps (`interpolate_phonon_modes`, `calculate_dos`, `calculate_tosca_spectrum`), which remain `PythonJob` CalcJobs.
- Changing Phonopy reading workflows (Phonopy inputs are read upfront by callers into a `ForceConstantsData` node).
- Removing the public Euphonic `read_force_constants_from_castep` function from `operations.py` or the `prepare_read_force_constants_inputs` builder from `pythonjobs.py`.

## Impact

- `src/aiida_pythonjob_ins/workflows/base.py`: Introduces `read_castep_force_constants`, `_compose_validators`, `ForceConstantsMixin`, and `JobDispatchMixin`.
- `src/aiida_pythonjob_ins/workflows/`: Simplifies outlines in `dispersion.py`, `dos.py`, and `tosca.py`.
- `tests/test_workflows.py`: Simplifies test assertions checking child process node types.
