# Tasks

## 1. Implement In-Process CASTEP Reader & Validator Helper

- [ ] 1.1 Implement `@calcfunction def read_castep_force_constants(castep_file: SinglefileData) -> ForceConstantsData` in `src/aiida_pythonjob_ins/workflows/base.py` and verify it loads force constants in-process.
- [ ] 1.2 Implement `_compose_validators(v_existing, v_new)` in `src/aiida_pythonjob_ins/workflows/base.py` with comprehensive docstring and unit test verifying cooperative validator chaining.

## 2. Decouple WorkChain Mixins (`ForceConstantsMixin` & `JobDispatchMixin`)

- [ ] 2.1 Implement `ForceConstantsMixin` in `src/aiida_pythonjob_ins/workflows/base.py` declaring `castep_file`, `force_constants`, chained validator, and synchronous `resolve_force_constants()` outline step.
- [ ] 2.2 Implement `JobDispatchMixin` in `src/aiida_pythonjob_ins/workflows/base.py` declaring `code`, `options`, `get_job_metadata()`, and exit code `ERROR_SUB_PROCESS_FAILED (400)`.
- [ ] 2.3 Refactor `ForceConstantsWorkChain` to inherit `(ForceConstantsMixin, WorkChain)` without `code` or `options`, exposing `force_constants` as an output port.

## 3. WorkChain Outlines & Subclass Refactoring

- [ ] 3.1 Update `DispersionWorkChain` in `src/aiida_pythonjob_ins/workflows/dispersion.py` to inherit `(ForceConstantsMixin, JobDispatchMixin, WorkChain)` and streamline outline to use `cls.resolve_force_constants`.
- [ ] 3.2 Update `DosWorkChain` in `src/aiida_pythonjob_ins/workflows/dos.py` to inherit `(ForceConstantsMixin, JobDispatchMixin, WorkChain)` and streamline outline to use `cls.resolve_force_constants`.
- [ ] 3.3 Update `ToscaFromForceConstantsWorkChain` in `src/aiida_pythonjob_ins/workflows/tosca.py` to inherit `(ForceConstantsMixin, JobDispatchMixin, WorkChain)` and streamline outline to use `cls.resolve_force_constants`.
- [ ] 3.4 Update `ToscaFromModesWorkChain` in `src/aiida_pythonjob_ins/workflows/tosca.py` to inherit `(JobDispatchMixin, WorkChain)`, removing duplicated `code`/`options`/metadata helper definitions.

## 4. Test Alignment & Verification

- [ ] 4.1 Update `tests/test_workflows.py` to assert that `read_castep_force_constants` produces a `CalcFunctionNode` and only compute steps produce `CalcJobNode`s.
- [ ] 4.2 Add unit test verifying that `ForceConstantsWorkChain` can be executed standalone from a CASTEP file without requiring a `code` input.
- [ ] 4.3 Run `uv run ruff check` and `uv run ruff format --check` across `src/` and `tests/` to verify lint and code style compliance.
- [ ] 4.4 Run `uv run pytest -m "not containerized"` to verify the entire test suite passes cleanly with reduced workflow runtimes.
