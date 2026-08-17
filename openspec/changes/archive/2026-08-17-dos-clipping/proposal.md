## Why

The phonon density of states calculation (`calculate_dos` in `operations.py`) builds its energy axis automatically as `np.arange(0.0, emax + energy_spacing, energy_spacing)`. Because the lower bound is hardcoded to `0.0`, any negative/imaginary frequencies—which represent dynamical instability or soft modes—fall below the energy axis and are completely omitted from the resulting DOS spectrum.

This defect creates a discrepancy: band structures generated for an unstable crystal clearly show negative branches, whereas the density of states for the same crystal silently drops those modes and truncates the integrated spectral weight.

Extending the automatically generated energy axis to span from `emin` (the minimum frequency, whether negative or zero) up to `emax` ensures all computed modes are included in the DOS, restoring physical consistency with Euphonic and the band structure calculations.

## What Changes

- Implement a reusable, unit-safe helper function `default_energy_bins(frequencies: pint.Quantity, energy_spacing: pint.Quantity, *, padding_fraction: float = 0.05) -> pint.Quantity` in `src/aiida_pythonjob_ins/operations.py` that operates strictly on Pint Quantities, computing bin edges with asymmetric 5% range padding.
- Use this helper function in `calculate_dos`, passing `energy_spacing * ureg(energy_unit)`.
- Update `phonon-operations` and `phonon-workflows` requirements to mandate that generated DOS energy axes span the full computed frequency range (including imaginary frequencies with adaptive padding), and that the spectrum integrates to three modes per atom across all computed frequencies.
- Add test coverage asserting that soft/imaginary modes (negative frequencies) are preserved in DOS calculations and integrated in the density of states.

## Non-Goals

- Replacing Euphonic's underlying `calculate_dos` implementation or broadening algorithms.
- Changing `operations.py` import architecture (remains strictly AiiDA-free).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `phonon-operations`: updates the DOS energy axis generation requirement so the axis spans the full computed dataset (from `emin` to `emax`) rather than clipping at zero, and updates the imaginary frequency preservation requirement.
- `phonon-workflows`: updates `DosWorkChain` requirements to reflect energy range handling and propagation of negative/imaginary frequencies into the resulting `XyData`.

## Impact

- `src/aiida_pythonjob_ins/operations.py`: `calculate_dos` energy axis generation logic updated.
- `src/aiida_pythonjob_ins/pythonjobs.py` & `src/aiida_pythonjob_ins/workflows/dos.py`: pass-through support for energy bounds if added.
- `openspec/specs/phonon-operations/spec.md` & `openspec/specs/phonon-workflows/spec.md`: delta specs created.
- `tests/test_operations.py` & `tests/test_workflows.py`: added/updated assertions for negative frequency DOS coverage.
