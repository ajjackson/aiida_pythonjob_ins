## MODIFIED Requirements

### Requirement: The DOS workflow produces a plottable density of states

The density-of-states workflow SHALL sample a Monkhorst-Pack grid from the force
constants and output the resulting density of states as a native `XyData`.

#### Scenario: A density of states is output

- **WHEN** the DOS workflow completes successfully
- **THEN** it outputs an `XyData` holding a physically valid density of states:
  non-empty, with energy and value arrays of equal length, values non-negative and
  not uniformly zero, whose energy axis covers all computed modes (including any negative/imaginary frequencies),
  and integrating to three modes per atom of the crystal within
  the tolerance broadening allows

#### Scenario: Grid and energy spacing are configurable

- **WHEN** the workflow is launched without specifying spacings
- **THEN** a default grid spacing of 0.1 reciprocal angstroms and a default energy
  bin width of 1.0 meV are applied
