## Context

See `proposal.md` - Why. The baseline review identified three documentation gaps:

1. **Factory usage**: README and tutorial examples rely on direct imports (`from aiida_pythonjob_ins.data import ...`) rather than standard AiiDA plugin factories (`DataFactory`/`WorkflowFactory`).
2. **WorkChain exit codes**: `docs/source/workflows.rst` claims pages display exit codes, but AiiDA's `aiida-workchain` directive does not render `spec.exit_codes`.
3. **Pickle-by-value docstring**: `pythonjobs.py` docstrings suggest `register_pickle_by_value=True`, which contradicts `design_notes.rst` and is untested for C-extension dependencies like Euphonic.

## Goals / Non-Goals

**Goals:**
- Update `README.md` and tutorial scripts in `docs/source/tutorials/` to load plugins via `DataFactory` and `WorkflowFactory`, adding a brief note that direct imports work as well.
- Document exit code 400 (`ERROR_SUB_PROCESS_FAILED`) in `ForceConstantsWorkChain` / `DispersionWorkChain` / `DosWorkChain` class docstrings so AutoAPI renders them, and align `docs/source/workflows.rst` prose.
- Clean up docstrings in `src/aiida_pythonjob_ins/pythonjobs.py` to remove the `register_pickle_by_value=True` suggestion and state that by-reference pickling is required.

**Non-Goals:**
- Hacking upstream `aiida-core` Sphinx directives.
- Modifying production runtime logic in `pythonjobs.py` or `operations.py`.

## Decisions

### 1. Document exit codes in class docstrings rather than modifying Sphinx extension

**Chosen: Add exit code descriptions to `ForceConstantsWorkChain` docstring.**
*Rationale:* `aiida-workchain` autodoc does not render `spec.exit_codes`. Adding exit code documentation to the class docstrings allows AutoAPI/Sphinx to render them cleanly on workflow pages without hacking upstream directives.

### 2. Demonstrate factories prominently with direct import notes

**Chosen: Use `DataFactory("pythonjob_ins.crystal")` and `WorkflowFactory("pythonjob_ins.dispersion")` in examples, with an inline comment or aside noting direct import compatibility.**
*Rationale:* Demonstrates idiomatic AiiDA plugin discovery while reassuring users that pythonic direct imports remain valid.

### 3. Remove `register_pickle_by_value` docstring advice

**Chosen: Remove `register_pickle_by_value=True` from `pythonjobs.py` docstrings.**
*Rationale:* Aligning docstrings with `design_notes.rst` avoids advertising an untested, unsupported mode for C-extension scientific packages like Euphonic.

## Risks / Trade-offs

- [Docstring exit codes could drift if `spec.exit_code` numbers change] → Low risk: exit codes are fixed public contracts (e.g. `400`).

## Migration Plan

No runtime data or migration steps required; documentation and docstring updates build cleanly with Sphinx.
