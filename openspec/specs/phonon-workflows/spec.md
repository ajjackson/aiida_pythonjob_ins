# phonon-workflows Specification

## Purpose

Compose the individual phonon steps into end-to-end AiiDA workflows that turn
force constants into a band structure or a density of states, recording the whole
calculation as a single connected provenance graph.
## Requirements
### Requirement: Workflows accept exactly one source of force constants

Every phonon workflow SHALL obtain its force constants from either a CASTEP file,
read during the workflow, or a prepared force-constants node supplied by the
caller. Exactly one of the two SHALL be given, and the workflow SHALL reject
inputs that provide both or neither before any computation begins.

#### Scenario: A CASTEP file is supplied

- **WHEN** a workflow is launched with a CASTEP `SinglefileData` and no
  force-constants node
- **THEN** the workflow reads the force constants as its first step and proceeds

#### Scenario: A prepared node is supplied

- **WHEN** a workflow is launched with a `ForceConstantsData` node and no CASTEP
  file
- **THEN** the workflow uses that node directly and performs no read step

#### Scenario: Both sources are supplied

- **WHEN** a workflow is launched with both a CASTEP file and a force-constants
  node
- **THEN** the workflow is rejected with an error stating that exactly one of the
  two must be provided

#### Scenario: Neither source is supplied

- **WHEN** a workflow is launched with neither a CASTEP file nor a force-constants
  node
- **THEN** the workflow is rejected with the same error

### Requirement: The dispersion workflow produces a labelled band structure

The dispersion workflow SHALL derive the crystal structure from the force
constants, generate a high-symmetry q-point path from it, interpolate the phonon
modes along that path, and compose a band structure. It SHALL expose the phonon
modes, the structure, the band path and the band structure as separate outputs,
so that intermediate results remain available and provenance-linked.

#### Scenario: All four outputs are produced with native types

- **WHEN** the dispersion workflow completes successfully
- **THEN** it outputs a `QpointPhononModesData`, a `StructureData`, a
  `KpointsData` band path, and a `BandsData` band structure

#### Scenario: The band path carries high-symmetry labels

- **WHEN** the dispersion workflow completes
- **THEN** the output band path has labelled high-symmetry points

#### Scenario: Band structure dimensions match the path and the modes

- **WHEN** the dispersion workflow completes for a crystal of A atoms
- **THEN** the band structure has one row per q-point in the band path and 3A
  branches per row

#### Scenario: The q-point spacing is configurable

- **WHEN** the workflow is launched without specifying a q-point spacing
- **THEN** a default target spacing of 0.025 reciprocal angstroms is applied

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

### Requirement: Compute steps are dispatchable to a Computer

Computationally heavy steps SHALL execute through a `Code` on a `Computer`, so a
workflow can be directed at a remote machine without modification. Every step SHALL
be recorded in the provenance graph.

The division of work between steps is an implementation concern and is not fixed
here; what is required is that heavy work is dispatchable, that no redundant work
is performed, and that the result is fully provenance-linked.

#### Scenario: Heavy steps run through the supplied code

- **WHEN** a workflow runs
- **THEN** force-constants reading, mode interpolation and density-of-states
  sampling each execute through the supplied code rather than in the caller's
  process
- **AND** each appears as a calculation in the workflow's provenance graph

#### Scenario: A prepared force-constants node is not re-read

- **WHEN** a workflow runs from a `ForceConstantsData` node rather than a CASTEP
  file
- **THEN** no force-constants reading step is performed

#### Scenario: Outputs are provenance-linked to inputs

- **WHEN** a workflow completes
- **THEN** every output node is connected back to the workflow's inputs through the
  recorded steps

### Requirement: A failed step terminates the workflow with a distinct exit code

If a job step does not finish successfully, the workflow SHALL stop and return a
dedicated failure exit code rather than proceeding with missing results.

#### Scenario: A job step fails

- **WHEN** any `PythonJob` step of a workflow finishes unsuccessfully
- **THEN** the workflow terminates with exit code 400, reporting that a job step
  did not finish successfully
- **AND** no downstream outputs are emitted

