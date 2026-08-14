## Why

Reviewing the baseline documentation identified three small documentation gaps where the published prose and code examples drift from the package's design and public contracts:

1. **AiiDA plugin factory usage vs. direct imports**: Tutorials and `README.md` examples demonstrate direct class imports (`from aiida_pythonjob_ins.data import ...`), but do not highlight loading types via AiiDA's standard plugin factories (`DataFactory` / `WorkflowFactory`), which is the primary pattern for plugin discovery.
2. **WorkChain exit codes missing in documentation**: `docs/source/workflows.rst` claims the workflow pages render exit codes, but the generated Sphinx pages omit them because AiiDA's `aiida-workchain` autodoc extension does not render `spec.exit_codes`.
3. **Misleading `register_pickle_by_value` advice**: Docstrings in `src/aiida_pythonjob_ins/pythonjobs.py` suggest callers can pass `register_pickle_by_value=True` to avoid installing the package remotely, contradicting `docs/source/design_notes.rst` (which mandates by-reference pickling because scientific dependencies with C-extensions cannot be pickled by value).

Reconciling these three items ensures the documentation and docstrings accurately reflect the package's actual architecture, AiiDA best practices, and runtime behavior.

## What Changes

- Update tutorial code examples and `README.md` to demonstrate loading custom nodes and WorkChains through `DataFactory` and `WorkflowFactory` as the primary pattern, with a brief note or aside stating that direct imports are also supported.
- Document exit codes (such as exit code 400 `ERROR_SUB_PROCESS_FAILED`) directly in `DispersionWorkChain` and `DosWorkChain` class docstrings so Sphinx/AutoAPI renders them, and align `docs/source/workflows.rst` prose.
- Remove the untested `register_pickle_by_value=True` recommendation from `src/aiida_pythonjob_ins/pythonjobs.py` docstrings, clarifying that by-reference pickling is required.

## Non-Goals

- Modifying upstream AiiDA's `aiida-workchain` Sphinx directive implementation.
- Changing production runtime execution in `pythonjobs.py` or `operations.py`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `documentation`: updates requirements to state that worked examples demonstrate plugin factory loading (`DataFactory`/`WorkflowFactory`), and that workflow documentation explicitly documents `WorkChain` exit codes.

## Impact

- `README.md` & `docs/source/tutorials/`: updated code snippets demonstrating `DataFactory` / `WorkflowFactory`.
- `src/aiida_pythonjob_ins/workflows/`: docstrings updated to document exit code 400 (`ERROR_SUB_PROCESS_FAILED`).
- `docs/source/workflows.rst`: prose updated to accurately reflect rendered workflow documentation.
- `src/aiida_pythonjob_ins/pythonjobs.py`: docstrings cleaned up regarding pickling strategy.
- `openspec/specs/documentation/spec.md`: delta spec created.
