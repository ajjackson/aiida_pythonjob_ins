## 1. Demonstrate plugin factories in documentation and examples

- [x] 1.1 Update `README.md` example snippets to demonstrate `DataFactory` and `WorkflowFactory` loading, with a brief note on direct import compatibility.
- [x] 1.2 Update tutorial scripts in `docs/source/tutorials/` (`plot_dispersion.py`, `plot_dos.py`, `plot_phonopy_bands_and_dos.py`) to load classes via `DataFactory` / `WorkflowFactory`.

## 2. Document WorkChain exit codes and update workflows prose

- [x] 2.1 Update `ForceConstantsWorkChain`, `DispersionWorkChain`, and `DosWorkChain` class docstrings in `src/aiida_pythonjob_ins/workflows/` to document exit code 400 (`ERROR_SUB_PROCESS_FAILED`).
- [x] 2.2 Update `docs/source/workflows.rst` prose to accurately describe rendered workflow documentation.

## 3. Clean up pickle-by-value docstring advice

- [x] 3.1 Edit `src/aiida_pythonjob_ins/pythonjobs.py` docstrings to remove the `register_pickle_by_value=True` suggestion and document by-reference pickling as required.

## 4. Verification and Closeout

- [x] 4.1 Build Sphinx documentation locally (`uv run --group doc make -C docs html`) and verify zero warnings.
- [x] 4.2 Run `uv run pytest` and `uv run ruff check` to ensure clean test suite and formatting.
- [x] 4.3 Mark items 1, 8, and 9 in `openspec/changes/archive/2026-08-12-document-poc-baseline/design.md` as addressed.
