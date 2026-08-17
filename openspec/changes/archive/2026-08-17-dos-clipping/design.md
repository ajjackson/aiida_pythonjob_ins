## Context

See `proposal.md` - Why.

Currently, `calculate_dos` in `src/aiida_pythonjob_ins/operations.py` determines its energy bin grid using:
```python
emax = modes.frequencies.max().to(energy_unit).magnitude
dos_bins = np.arange(0.0, emax + energy_spacing, energy_spacing) * ureg(energy_unit)
```
When `modes.frequencies` contains negative values (imaginary modes from acoustic sum-rule noise or genuine structural instability), starting the grid at `0.0` drops all negative frequency modes.

## Goals / Non-Goals

**Goals:**
- Construct an automatic DOS energy bin axis that captures the full computed frequency range from `emin` to `emax`.
- Implement asymmetric visual padding: 5% above `emax`, 5% below `emin` only when `emin < 0.0`, and strictly clamp the lower bound to `0.0` when `emin >= 0.0`.
- Align padded bounds to exact multiples of `energy_spacing` to preserve regular bin intervals.
- Add test coverage asserting that imaginary modes (negative frequencies) are preserved in DOS calculations and that the spectrum integrates to 3 modes per atom across the full data range.

**Non-Goals:**
- Modifying Euphonic's internal broadening or calculation algorithms.
- Modifying the AiiDA-free design of `operations.py`.

## Decisions

### 1. Pure Pint Quantity Helper (`default_energy_bins`) & Asymmetric 5% Range Padding

**Chosen:**
Define `default_energy_bins(frequencies: pint.Quantity, energy_spacing: pint.Quantity, *, padding_fraction: float = 0.05) -> pint.Quantity`:
1. Require both `frequencies` and `energy_spacing` to be dimensional Pint Quantities.
2. Convert `frequencies` to the unit of `energy_spacing`: `freqs_in_unit = frequencies.to(energy_spacing.units).magnitude`.
3. Extract `emin = np.min(freqs_in_unit)` and `emax = np.max(freqs_in_unit)`.
4. Frequency span is `span = max(emax - emin, spacing_val)`.
5. Padding is `pad = padding_fraction * span`.
6. Upper bound: `upper = emax + pad`.
7. Lower bound:
   - If `emin < 0.0`: `lower = emin - pad` (padded negative bound).
   - If `emin >= 0.0`: `lower = 0.0` (clean, unpadded zero baseline).
8. Bin alignment:
   - `start = np.floor(lower / spacing_val) * spacing_val`
   - `stop = np.ceil(upper / spacing_val) * spacing_val + spacing_val`
   - `return np.arange(start, stop, spacing_val) * energy_spacing.units`

`calculate_dos` constructs `spacing_qty = energy_spacing * ureg(energy_unit)` and delegates to `default_energy_bins(modes.frequencies, spacing_qty)`.

*Rationale:* Operating strictly on Pint Quantities in the helper eliminates unit conversion errors (e.g. comparing THz against meV), while keeping `calculate_dos` compatible with AiiDA's primitive `orm.Float` inputs.

*Alternatives considered:*
- *Mixed float/Quantity typing:* Allows implicit unit assumptions and type branching. (Rejected in favor of strict Quantity interface at helper level).

### 2. Testing Soft Modes and Sum Rules

**Chosen:**
- Create unit tests in `test_operations.py` that construct a mock / fixture `QpointPhononModes` object containing negative frequencies (or use synthetic force constants) to explicitly verify that `calculate_dos` generates bins starting below zero and that negative modes are binned.
- Assert that numerical integration (`np.trapezoid` or Euphonic integral) over the DOS spectrum equals 3 modes per atom (within broadening limits).

## Risks / Trade-offs

- [Broadening near edge could extend slightly past 5% pad] → 5% padding is sufficient for standard adaptive broadening widths; callers can use smaller `energy_spacing` for finer resolution.

## Migration Plan

Additive/bugfix logic change within `calculate_dos`. No database migration or profile modification required.
