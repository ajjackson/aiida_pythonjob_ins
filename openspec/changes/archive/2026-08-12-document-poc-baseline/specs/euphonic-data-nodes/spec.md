## Purpose

Persist Euphonic's core lattice-dynamics objects as AiiDA `Data` nodes, so force
constants, phonon modes and crystal structures can be stored, queried and linked
into AiiDA provenance without losing fidelity.

## ADDED Requirements

### Requirement: Euphonic objects round-trip through storage without loss

The plugin SHALL provide AiiDA `Data` node types wrapping the Euphonic objects
that move between workflow steps: `ForceConstantsData` for `ForceConstants`,
`QpointPhononModesData` for `QpointPhononModes`, and `EuphonicCrystalData` for
`Crystal`. Storing an object and reading it back after persistence SHALL yield an
equivalent object.

Equivalence means every field the wrapped type carries, together with its physical
units - not merely enough of it to identify the structure:

- a `Crystal` preserves its lattice vectors, atomic species, fractional atomic
  positions and atomic masses;
- `ForceConstants` preserves its crystal, the force-constants matrix, and the
  supercell description and dipole data (Born effective charges and dielectric
  tensor) needed to reproduce an interpolation;
- `QpointPhononModes` preserves its crystal, q-points, q-point weights,
  frequencies and eigenvectors.

#### Scenario: A stored and reloaded object matches the original field by field

- **WHEN** any of the supported Euphonic objects is wrapped in its node type, the
  node is stored, and the object is retrieved again
- **THEN** every field listed above matches the original to within floating-point
  tolerance, carrying the same physical units

#### Scenario: A reloaded object reproduces the original's results

- **WHEN** phonon modes are interpolated at the same q-points from a
  `ForceConstants` retrieved from a stored node and from the original object
- **THEN** the two calculations agree, so the stored node is a substitute for the
  original rather than merely a record of it

#### Scenario: Reconstruction does not require the original input file

- **WHEN** a node is retrieved in a session where the calculator output it was
  originally read from is unavailable
- **THEN** the wrapped object is reconstructed in full from the node alone

### Requirement: Bulk numerical data is held in the node repository

Wrapped objects SHALL be serialised into the node's file repository rather than
into database attributes, so that large force-constant arrays do not inflate the
AiiDA database.

#### Scenario: A stored node keeps its payload as a repository object

- **WHEN** a node wrapping a Euphonic object is stored
- **THEN** the serialised object is retrievable from the node's file repository
- **AND** no force-constant or eigenvector array is written to the node's database
  attributes

### Requirement: Construction rejects objects of the wrong type

Each node type SHALL validate that the object it is given matches the Euphonic
class it wraps, and SHALL raise `TypeError` otherwise, so that a mistyped input
fails at construction rather than at some later retrieval.

#### Scenario: A non-Euphonic object is rejected

- **WHEN** a caller constructs a `ForceConstantsData` from an object that is not
  a `ForceConstants` instance
- **THEN** a `TypeError` is raised naming the expected and received types

### Requirement: Force-constants nodes can be built directly from calculator output

`ForceConstantsData` SHALL offer constructors that read force constants from the
supported upstream formats without the caller handling Euphonic objects: a CASTEP
`.castep_bin`/`.check` file, and a Phonopy output set.

#### Scenario: Reading a CASTEP file

- **WHEN** a caller builds a `ForceConstantsData` from a CASTEP force-constants
  file
- **THEN** the node yields force constants equivalent to reading the same file
  directly with Euphonic's own CASTEP reader

#### Scenario: Reading a Phonopy output set

- **WHEN** a caller builds a `ForceConstantsData` from a Phonopy summary,
  force-constants and optional Born-charges file
- **THEN** the node yields force constants equivalent to reading the same files
  directly with Euphonic's own Phonopy reader

#### Scenario: Rebuilding a node from a previously written Euphonic JSON file

- **WHEN** a caller builds a node from an existing Euphonic JSON file
- **THEN** the node wraps the object described by that file, without
  re-reading the original calculator output

### Requirement: Nodes that carry a crystal expose it as a structure

A node whose wrapped object carries crystal information SHALL be able to yield
that crystal as a native AiiDA `StructureData`. Node types whose wrapped object
has no crystal SHALL NOT offer this operation, so the API does not advertise
structure extraction where none is possible.

#### Scenario: Force constants yield their structure

- **WHEN** `to_structure()` is called on a `ForceConstantsData`
- **THEN** a `StructureData` is returned with one site per atom of the wrapped
  crystal, carrying the same species, positions and masses

#### Scenario: Phonon modes yield their structure

- **WHEN** `to_structure()` is called on a `QpointPhononModesData`
- **THEN** a `StructureData` is returned describing the modes' own crystal, with
  the same species, positions and masses

#### Scenario: A crystal node yields its own structure

- **WHEN** `to_structure()` is called on an `EuphonicCrystalData`
- **THEN** a `StructureData` describing that crystal is returned
