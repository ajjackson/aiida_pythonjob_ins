# Spec Delta: phonon-workflows

## MODIFIED Requirements

### Requirement: Workflows accept exactly one source of force constants

Every workflow that starts from force constants SHALL obtain them from either a
CASTEP file, read during the workflow, or a prepared force-constants node supplied
by the caller. Exactly one of the two SHALL be given, and the workflow SHALL reject
inputs that provide both or neither before any computation begins.

The source inputs SHALL be grouped under a single `force_constants` input
namespace whose ports are those of `ForceConstantsWorkChain`: `castep_file` for a
CASTEP file and `node` for a prepared node.

A workflow whose input is a different quantity — such as one that starts from
prepared phonon modes — SHALL NOT offer a force-constants source at all, rather
than offering one that is optional or ignored.

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

#### Scenario: Source inputs are grouped in one namespace

- **WHEN** the inputs of a workflow that starts from force constants are inspected
- **THEN** the CASTEP file and force-constants node ports appear only inside its
  `force_constants` namespace, with the same names as the inputs of
  `ForceConstantsWorkChain`

#### Scenario: A workflow starting from another quantity has no force-constants input

- **WHEN** the inputs of a workflow that starts from prepared phonon modes are
  inspected
- **THEN** they include no CASTEP file and no force-constants node

## ADDED Requirements

### Requirement: Force constants are resolved by a standalone workflow

`ForceConstantsWorkChain` SHALL accept exactly one force-constants source, either
a CASTEP file or a `ForceConstantsData` node, and SHALL output the resolved
`ForceConstantsData` as `force_constants`. It SHALL dispatch no jobs and SHALL NOT
take a `Code` or execution options.

#### Scenario: A CASTEP file is resolved

- **WHEN** the workflow is launched with a CASTEP `SinglefileData`
- **THEN** it outputs a `ForceConstantsData` equivalent to reading the same file
  with Euphonic's own CASTEP reader
- **AND** the read appears as its own calculation in the provenance graph,
  linking the file to the output

#### Scenario: A prepared node is passed through

- **WHEN** the workflow is launched with a `ForceConstantsData` node
- **THEN** its `force_constants` output is that same node, and no calculation is
  performed

#### Scenario: No code or options are accepted

- **WHEN** the inputs of the workflow are inspected
- **THEN** they include neither a code nor an options input

#### Scenario: An unreadable file fails with a dedicated exit code

- **WHEN** the workflow is launched with a file that cannot be read as CASTEP
  force constants
- **THEN** it terminates with an exit code dedicated to read failure and emits no
  output

### Requirement: Force-constants workflows delegate source resolution

Every workflow that starts from force constants SHALL obtain them by running
`ForceConstantsWorkChain` as a sub-workflow, whichever source is supplied. If the
sub-workflow does not finish successfully, the workflow SHALL stop with an exit
code dedicated to that failure, distinct from its other exit codes, and SHALL emit
no outputs.

#### Scenario: The source workflow appears in provenance

- **WHEN** a workflow that starts from force constants runs, from either kind of
  source
- **THEN** exactly one `ForceConstantsWorkChain` appears as a called sub-workflow
- **AND** its `force_constants` output is the node the subsequent steps consume

#### Scenario: A failed source resolution stops the workflow

- **WHEN** the `ForceConstantsWorkChain` sub-workflow does not finish successfully
- **THEN** the workflow terminates with its dedicated source-failure exit code,
  distinct from the code used for a failed job step
- **AND** no outputs are emitted
