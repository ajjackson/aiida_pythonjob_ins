# Design: Migrate CASTEP File Reading to In-Process Calcfunction and Refactor Workflow Mixins

## Context

In `ForceConstantsWorkChain` (`src/aiida_pythonjob_ins/workflows/base.py`), the outline historically executed:
```python
if_(cls.should_read_castep)(cls.read_force_constants),
cls.assign_force_constants,
...
```
`read_force_constants` submitted an out-of-process `PythonJob` CalcJob. Because `PythonJob` runs via the transport/scheduler system, it triggers file staging, background process submission, Python interpreter launch, dynamic library loading, and output retrieval—incurring ~2.8 seconds of overhead for ~0.1 seconds of actual parsing work (`ForceConstants.from_castep`).

Migrating file reading to an in-process `@calcfunction` makes the operation synchronous and eliminates this overhead. However, it also changes the object-oriented structure:
- `ForceConstantsWorkChain` currently declares `code` (`AbstractCode`) and `options` (`Dict`), which it never uses once reading is an in-process calcfunction.
- Subclasses (`DispersionWorkChain`, `DosWorkChain`, `ToscaFromForceConstantsWorkChain`) still require `code` and `options` for their downstream compute jobs (`interpolate_phonon_modes`, `calculate_dos`, `interpolate_modes`).
- `ToscaFromModesWorkChain` currently duplicates the `code`, `options`, and `get_job_metadata()` definitions because it does not inherit `ForceConstantsWorkChain`.

## Goals / Non-Goals

**Goals:**
- Replace the out-of-process `PythonJob` submission in `read_force_constants` with an in-process AiiDA `@calcfunction` (`read_castep_force_constants`).
- Decouple the Force Constants Source concern (`castep_file` vs `force_constants`) from the Job Dispatch concern (`code`, `options`, `get_job_metadata()`, exit code 400) using reusable capability mixins.
- Ensure no class or mixin declares input ports it does not use: `ForceConstantsWorkChain` becomes a clean standalone WorkChain taking only files/nodes and zero unused `code`/`options` ports.
- Safely chain AiiDA namespace validators via `_compose_validators` to prevent accidental clobbering of `spec.inputs.validator`.
- Streamline workchain outlines from the asynchronous 2-step pattern (`if_(should_read)(read) + assign`) into a single synchronous `resolve_force_constants` step.
- Eliminate duplicated `code` and `options` port definitions in `ToscaFromModesWorkChain`.

**Non-Goals:**
- Modifying compute-heavy operations (`interpolate_phonon_modes`, `calculate_dos`, `calculate_tosca_spectrum`), which remain `PythonJob` CalcJobs.
- Removing `prepare_read_force_constants_inputs` from `src/aiida_pythonjob_ins/pythonjobs.py` (it remains available for standalone remote staging if callers require it).

## Decisions

### Decision 1: Native `@calcfunction` for `read_castep_force_constants`
- **Choice**: Use a standard AiiDA `@calcfunction` implemented in `src/aiida_pythonjob_ins/workflows/base.py`:
  ```python
  @calcfunction
  def read_castep_force_constants(castep_file: SinglefileData) -> ForceConstantsData:
      """Read CASTEP binary force constants into a ForceConstantsData node."""
      with castep_file.as_path() as filepath:
          fc = ForceConstants.from_castep(str(filepath))
      return ForceConstantsData(fc)
  ```
- **Rationale**: AiiDA's `@calcfunction` is the idiomatic mechanism for in-process operations that construct AiiDA nodes (as used in `extract_structure` and `generate_band_path` in `dispersion.py`, and `group_spectra` in `tosca.py`). It requires no cloudpickling, does not spawn an asyncio task runner, and executes synchronously in under 100ms while generating a first-class `CalcFunctionNode` in the provenance graph. `SinglefileData.as_path()` reliably yields a `pathlib.Path` across all AiiDA storage backends.
- **Scope & Visibility**: Kept internal to `src/aiida_pythonjob_ins/workflows/base.py` rather than actively promoted or exported in `aiida_pythonjob_ins.workflows.__all__`. Format-specific data conversion routines may evolve as additional force-constant sources are introduced.

### Decision 2: Decoupled Capability Mixins (`ForceConstantsMixin` and `JobDispatchMixin`)
- **Choice**: Separate the two orthogonal concerns into mixins:
  1. `ForceConstantsMixin`: Defines inputs `castep_file` (`SinglefileData`, optional) and `force_constants` (`ForceConstantsData`, optional), registers the mutual-exclusion validator, and implements synchronous `resolve_force_constants()`. Does **not** declare output ports, ensuring subclasses do not inherit an unfulfilled `force_constants` output.
  2. `JobDispatchMixin`: Defines inputs `code` (`AbstractCode`) and `options` (`Dict`, optional), implements `get_job_metadata()`, and registers exit code `400 (ERROR_SUB_PROCESS_FAILED)`.
- **Cooperative MRO**: Every mixin's `define(cls, spec)` must call `super().define(spec)` so that AiiDA's `Process` metaclass cooperatively collects input and output ports across all classes in the MRO.
- **Class composition**:
  - `ForceConstantsWorkChain(ForceConstantsMixin, WorkChain)`: A standalone workflow that resolves force constants and exposes `force_constants` as an output port in its own `define()` and `finalize()`. Takes **no `code`** and **no `options`**.
  - `DispersionWorkChain(ForceConstantsMixin, JobDispatchMixin, WorkChain)`: Inherits both. Exposes its own outputs (`phonon_modes`, `structure`, `band_path`, `band_structure`).
  - `DosWorkChain(ForceConstantsMixin, JobDispatchMixin, WorkChain)`: Inherits both. Exposes `dos`.
  - `ToscaFromForceConstantsWorkChain(ForceConstantsMixin, JobDispatchMixin, WorkChain)`: Inherits both.
  - `ToscaFromModesWorkChain(JobDispatchMixin, WorkChain)`: Inherits `JobDispatchMixin` directly, eliminating its duplicated `code`, `options`, and `get_job_metadata()` declarations.

### Decision 3: Safe Cooperative Validator Composition (`_compose_validators`)
- **Problem**: In AiiDA / Plumpy, `PortNamespace.validator` is a plain setter (`self._validator = validator`). Setting `spec.inputs.validator = ...` in multiple mixins or subclasses silently overwrites previous validators rather than chaining them.
- **Contract & Signature**: AiiDA namespace validators adhere to `(inputs: Mapping[str, Any], port: PortNamespace) -> str | None`. A validator returns `None` if validation passes, or an error string if invalid.
- **Choice**: Introduce a helper in `src/aiida_pythonjob_ins/workflows/base.py`:
  ```python
  def _compose_validators(v_existing, v_new):
      """Compose two AiiDA PortNamespace validator callables.

      In Plumpy, assigning to ``spec.inputs.validator`` overwrites any existing
      validator on that namespace. This helper chains an existing validator with
      a new one so that cooperative mixins do not clobber each other.

      Parameters
      ----------
      v_existing, v_new : callable or None
          Validators accepting ``(inputs, port)`` and returning ``None`` on
          success or an error message string on failure.
      """
      if v_existing is None:
          return v_new
      if v_new is None:
          return v_existing
      return lambda inputs, port: v_existing(inputs, port) or v_new(inputs, port)
  ```
  In `ForceConstantsMixin.define(spec)`:
  ```python
  spec.inputs.validator = _compose_validators(
      spec.inputs.validator, cls._validate_force_constants_source
  )
  ```

### Decision 4: Single-Step Synchronous `resolve_force_constants`
- **Choice**: Replace the asynchronous 2-step outline (`if_(cls.should_read_castep)(cls.read_force_constants)`, `cls.assign_force_constants`) with a single synchronous outline step:
  ```python
  def resolve_force_constants(self):
      """Resolve force constants from supplied node or read from CASTEP file."""
      if "force_constants" in self.inputs:
          self.ctx.force_constants = self.inputs.force_constants
      else:
          try:
              self.ctx.force_constants = read_castep_force_constants(
                  self.inputs.castep_file
              )
          except Exception as exc:
              self.report(f"Failed to read CASTEP force constants: {exc}")
              return self.exit_codes.ERROR_READ_FAILED
      return None
  ```
- **Rationale**: The 2-step outline was an artifact of `PythonJob`'s asynchronous dispatch. With an in-process calcfunction, resolution happens synchronously in one step, simplifying the outline across all workchains.

### Decision 5: Error Handling and Exit Codes
- **Choice**: Add a dedicated exit code `ERROR_READ_FAILED = 410` on `ForceConstantsMixin`:
  ```python
  spec.exit_code(
      410,
      "ERROR_READ_FAILED",
      message="Failed to read force constants from the CASTEP file.",
  )
  ```
- **Exit Code Taxonomy**:
  - `ERROR_READ_FAILED = 410`: specifically identifies local CASTEP file parsing or format failure in `read_castep_force_constants`.
  - `ERROR_SUB_PROCESS_FAILED = 400`: reserved for child `PythonJob` CalcJob execution failures, provided by `JobDispatchMixin`.
  - `ERROR_SPECTRUM_WORKCHAIN_FAILED = 401`: defined on `ToscaFromForceConstantsWorkChain` specifically to indicate delegated `ToscaFromModesWorkChain` failure (as verified in `test_tosca_from_force_constants_failure_is_distinguishable`). These failure modes remain distinct and unambiguous.

## Risks / Trade-offs

- **[Risk]** Test suites asserting that `read_force_constants` creates a `CalcJobNode` will fail until updated.  
  $\rightarrow$ **Mitigation**: Update assertions in `tests/test_workflows.py` to assert `CalcFunctionNode` for the read step and `CalcJobNode` for compute steps.
- **[Risk]** Multiple inheritance with AiiDA metaclasses requires strict cooperative `super().define(spec)` calls.  
  $\rightarrow$ **Mitigation**: Verified via unit test that `super().define(spec)` across `ForceConstantsMixin`, `JobDispatchMixin`, and `WorkChain` resolves cleanly in MRO order.
