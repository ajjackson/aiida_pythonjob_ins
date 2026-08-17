## 1. Implement reusable energy/frequency bins helper and update calculate_dos

- [x] 1.1 Add a unit-safe pure helper function `default_energy_bins(frequencies: pint.Quantity, energy_spacing: pint.Quantity, *, padding_fraction: float = 0.05) -> pint.Quantity` in `src/aiida_pythonjob_ins/operations.py` that operates strictly on Pint Quantities.
- [x] 1.2 Update `calculate_dos` in `src/aiida_pythonjob_ins/operations.py` to construct `energy_spacing * ureg(energy_unit)` and delegate to `default_energy_bins`.

## 2. Add test coverage for imaginary modes and sum rules

- [x] 2.1 Add unit tests in `tests/test_operations.py` asserting that `calculate_dos` with negative frequencies (soft modes) generates bins starting below zero and includes negative frequencies in the output spectrum.
- [x] 2.2 Add unit tests verifying that stable systems start their DOS energy axis cleanly at 0.0 without bottom padding.
- [x] 2.3 Assert that integrating the DOS spectrum across the padded axis recovers 3 modes per atom within broadening tolerance.

## 3. Verification and Closeout

- [x] 3.1 Run full test suite (`uv run pytest`) and linting (`uv run ruff check` / `uv run ruff format --check`).
- [x] 3.2 Mark item 7 in `openspec/changes/archive/2026-08-12-document-poc-baseline/design.md` as addressed.
