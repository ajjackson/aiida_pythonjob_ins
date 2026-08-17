## MODIFIED Requirements

### Requirement: Imaginary frequencies are preserved and reported honestly

A dynamical matrix can yield negative eigenvalues, whose frequencies are imaginary
and are conventionally represented as negative values. These arise both from
genuine dynamical instability and, near the zone centre, from numerical noise in
the acoustic branches. Both cases are scientifically meaningful and must reach the
user. Operations SHALL propagate imaginary frequencies unaltered: they SHALL NOT
be clipped to zero, discarded, or replaced by their magnitude.

#### Scenario: Imaginary modes reach the caller unchanged

- **WHEN** interpolation yields one or more imaginary frequencies, represented as
  negative values
- **THEN** they appear in the returned modes with their sign intact, and no mode is
  removed, reordered or rescaled

#### Scenario: Instability is not disguised as a stable result

- **WHEN** a structure is dynamically unstable, so a substantial number of modes
  are imaginary
- **THEN** the returned modes represent that honestly, rather than presenting a
  spectrum that appears stable

### Requirement: A phonon density of states is computed on a sampling grid

The operations SHALL compute a phonon density of states by sampling a
Monkhorst-Pack grid derived from a target spacing, binning frequencies onto an
energy axis of configurable width and unit. Adaptive broadening based on mode
gradients SHALL be available and SHALL be the default.

#### Scenario: A density of states is returned as a spectrum

- **WHEN** a DOS is requested for a set of force constants at a given grid spacing
  and energy bin width
- **THEN** a non-empty `Spectrum1D` is returned whose bin centres and values have
  equal length, whose values are non-negative and not uniformly zero, and whose
  energy axis uses the requested bin width and covers the full phonon frequency range
  including imaginary/negative frequencies
- **AND** the spectrum integrates to three modes per atom of the crystal within
  the tolerance broadening allows

#### Scenario: The energy axis is generated from the computed frequencies with asymmetric padding

- **WHEN** a DOS is computed and the energy range is generated automatically
- **THEN** the axis uses the requested bin width, applies 5% padding above the maximum computed frequency, and:
  - if the minimum computed frequency is negative (imaginary modes present), applies 5% padding below that minimum frequency;
  - if the minimum computed frequency is non-negative, clamps the lower bound cleanly at zero without bottom padding
- **AND** all computed modes fall within the binned energy range, contributing their full weight to the integrated spectrum

#### Scenario: Adaptive broadening can be disabled

- **WHEN** a DOS is requested with adaptive broadening disabled
- **THEN** a valid spectrum is still returned, computed without mode gradients, and
  it satisfies the same sum rule at least as closely as the adaptive result, which
  loses slightly more weight to broadening beyond the binned range
