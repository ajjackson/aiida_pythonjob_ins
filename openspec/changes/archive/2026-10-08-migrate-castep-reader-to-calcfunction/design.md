# Design: Read CASTEP force constants in-process

## Context

`ForceConstantsWorkChain` (`workflows/base.py`) is an abstract base with no outline. It declares `castep_file`, `force_constants`, `code`, `options`, the "exactly one source" validator, exit code 400 and `get_job_metadata()`. Its subclasses start their outlines with `if_(cls.should_read_castep)(cls.read_force_constants), cls.assign_force_constants`. `read_force_constants` submits a `PythonJob` built by `prepare_read_force_constants_inputs`. When that job fails, `assign_force_constants` returns 400.

## Goals / Non-Goals

**Goals:** an in-process, provenance-recorded CASTEP read; a failure mode that callers can query; no change to the class structure.

**Non-Goals:** see proposal.md. `refactor-fcwc` later moves the read into a standalone `ForceConstantsWorkChain`. This design keeps the read in a form that moves without change.

## Decisions

### 1. An in-process calcfunction that reuses `ForceConstantsData.from_castep`

```python
@calcfunction
def read_castep_force_constants(castep_file: SinglefileData) -> ForceConstantsData:
    with castep_file.as_path() as path:
        return ForceConstantsData.from_castep(path)   # plus Decision 2's error handling
```

- A calcfunction is AiiDA's mechanism for cheap, in-process steps that create nodes ([calculation functions](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/calculations/concepts.html#calculation-functions)). It records a `CalcFunctionNode` linking the file to its output, and it can be cached. This package already uses calcfunctions for `extract_structure`, `generate_band_path`, `assemble_bands`, `group_spectra` and `broaden_spectra`.
- `ForceConstantsData.from_castep` is the existing, specified constructor ("Force-constants nodes can be built directly from calculator output"). Reusing it avoids a second CASTEP-reading code path.
- `SinglefileData.as_path()` exists in aiida-core 2.6.0 (it is absent in 2.5.0), which matches the `aiida-core>=2.6` pin.
- It goes in `workflows/base.py`, is not exported and has no entry point. `refactor-fcwc` makes `ForceConstantsWorkChain` the public way to resolve force constants, so per-format calcfunctions stay internal.

*Rejected: keeping the `PythonJob`.* It costs about 2.8 s of job machinery for about 0.1 s of work, and the read needs neither a remote machine nor a lean environment.

### 2. An unreadable file returns an `ExitCode`

Inside the calcfunction, the exceptions Euphonic's reader raises on unreadable input are caught, and it returns `ExitCode(300, "Could not read CASTEP force constants: <reason>")`. Any other exception propagates.

- The AiiDA docs reserve the Excepted state for processes that "incurred an exception during execution". For a problem that "is easily foreseeable and classifiable", they recommend returning an `ExitCode`, which "makes it easier for a workflow calling the function to respond … and … to query for these specific failure modes" ([process functions: exit codes](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/processes/functions.html#exit-codes)).
- 300 follows the convention that 300–399 is "suggested for critical process errors" ([exit code conventions](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/processes/usage.html#exit-code-conventions)).
- The exception types to catch are not yet known. Task 1.1 determines them by passing junk and truncated bytes to `ForceConstants.from_castep`.

*Rejected: letting it raise and wrapping the call in `try/except Exception` in the workflow.* That leaves an Excepted node for a foreseeable failure, and it also catches unrelated bugs.

### 3. One source-resolution step

The two outline entries `if_(cls.should_read_castep)(cls.read_force_constants), cls.assign_force_constants` become one, `cls.resolve_force_constants`:

- if `force_constants` was supplied, set `self.ctx.force_constants` to it;
- otherwise, `result, node = read_castep_force_constants.run_get_node(self.inputs.castep_file)`. If `node.is_finished_ok`, store `result` in `self.ctx.force_constants`; if not, call `self.report(node.exit_message)` and return `ERROR_READ_FAILED`.

`should_read_castep`, `read_force_constants` and `assign_force_constants` are removed. Calcfunctions run synchronously in the step, so the split that existed only to wait on a submitted job is no longer needed.

### 4. Exit code `410 ERROR_READ_FAILED` on the base

| Code | Meaning |
|---|---|
| 400 `ERROR_SUB_PROCESS_FAILED` | a PythonJob failed (unchanged message) |
| 410 `ERROR_READ_FAILED` | the force constants could not be read |
| 401 `ERROR_SPECTRUM_WORKCHAIN_FAILED` | unchanged (`ToscaFromForceConstantsWorkChain`) |

`code` and `options` stay on the base, because every concrete subclass still dispatches jobs. `refactor-fcwc` moves 410, together with the read step, into the standalone `ForceConstantsWorkChain`, and gives consumers their own sub-process code. The spec therefore states that the read-failure code is distinct, not its number.

## Risks / Trade-offs

- [Catching too few exception types leaves some bad files as Excepted rather than 410.] → Task 1.1 derives the types from Euphonic's actual behaviour, and the test passes a junk file.
- [Catching too broadly hides bugs.] → Only the types from task 1.1 are caught, never bare `Exception`.
- [Workflows lose their in-workflow example of PythonJob file staging.] → `prepare_read_force_constants_inputs` and `tests/test_remote_ssh.py` keep that example; the docstrings point to them.
