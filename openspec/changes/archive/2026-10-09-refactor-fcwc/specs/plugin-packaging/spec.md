# Spec Delta: plugin-packaging

## MODIFIED Requirements

### Requirement: Plugin classes are discoverable through AiiDA entry points

The package SHALL register its data types under the `aiida.data` entry-point group
and its workflows under `aiida.workflows`, using the `pythonjob_ins` prefix, so
that AiiDA users can load them through the standard plugin factories rather than
by direct import. The registered set SHALL cover every data type and workflow
intended for users to load, so introducing one is a modification to this
requirement and to the scenarios below.

Where two workflows perform the same calculation from different starting data,
their entry-point names SHALL distinguish them by that starting data, since the
result alone does not.

#### Scenario: Data classes load through the data factory

- **WHEN** `pythonjob_ins.crystal`, `pythonjob_ins.force_constants` or
  `pythonjob_ins.qpoint_phonon_modes` is requested from AiiDA's data factory
- **THEN** the corresponding `EuphonicCrystalData`, `ForceConstantsData` or
  `QpointPhononModesData` class is returned

#### Scenario: Workflows load through the workflow factory

- **WHEN** `pythonjob_ins.force_constants`, `pythonjob_ins.dispersion`,
  `pythonjob_ins.dos`, `pythonjob_ins.tosca_from_modes` or
  `pythonjob_ins.tosca_from_force_constants` is requested from AiiDA's workflow
  factory
- **THEN** the corresponding `ForceConstantsWorkChain`, `DispersionWorkChain`,
  `DosWorkChain`, `ToscaFromModesWorkChain` or `ToscaFromForceConstantsWorkChain`
  class is returned

#### Scenario: Every declared entry point resolves to its class

- **WHEN** the installed AiiDA plugins are listed for the `aiida.data` and
  `aiida.workflows` groups
- **THEN** every entry point this package declares is listed, and each loads the
  class it names
