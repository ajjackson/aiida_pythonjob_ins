# Spec Delta: phonon-workflows

## MODIFIED Requirements

### Requirement: Compute steps are dispatchable to a Computer

Computationally heavy steps SHALL execute through a `Code` on a `Computer`, so a
workflow can be directed at a remote machine without modification. Every step SHALL
be recorded in the provenance graph.

The workflow SHALL accept an optional `options` input port (holding a `Dict` or dictionary
describing scheduler and execution options, such as resources, wallclock limits, or queue names)
and SHALL forward these options to every dispatched job step. When `options` is not supplied,
the default execution options of the underlying job step SHALL apply.
A workflow that does not dispatch any job steps SHALL NOT require a `Code` or `options` input port.

The division of work between steps is an implementation concern and is not fixed
here; what is required is that heavy work is dispatchable, that no redundant work
is performed, and that the result is fully provenance-linked.

Steps that are cheap by comparison — such as reading force constants from a CASTEP file,
or regrouping or broadening an already-computed spectrum — need not be dispatched,
but SHALL still be recorded as their own steps in the provenance graph so that they
can be repeated independently of the heavy work.

#### Scenario: Heavy steps run through the supplied code

- **WHEN** a workflow runs
- **THEN** mode interpolation, density-of-states sampling
  and scattering-intensity calculation each execute through the supplied code
  rather than in the caller's process
- **AND** each appears as a calculation in the workflow's provenance graph

#### Scenario: Force constants reading from a file runs in-process

- **WHEN** a workflow runs from a CASTEP `SinglefileData` file
- **THEN** reading the force constants executes in-process as a `calcfunction` rather than through the supplied code
- **AND** it produces a `ForceConstantsData` node connected to the `SinglefileData` in the provenance graph

#### Scenario: Caller supplies scheduler options to the workflow

- **WHEN** a workflow is launched with an `options` input specifying scheduler resources
- **THEN** each dispatched `PythonJob` calculation executes with those resources configured in its metadata options
- **AND** the `options` node is linked as an input in the workflow's provenance graph

#### Scenario: Caller omits scheduler options

- **WHEN** a workflow is launched without an `options` input
- **THEN** each dispatched `PythonJob` calculation executes with its standard default options

#### Scenario: A prepared force-constants node is not re-read

- **WHEN** a workflow runs from a `ForceConstantsData` node rather than a CASTEP
  file
- **THEN** no force-constants reading step is performed

#### Scenario: Cheap post-processing is recorded as its own step

- **WHEN** a workflow groups or broadens a spectrum it has already computed
- **THEN** that post-processing appears in the provenance graph as a step distinct
  from the calculation that produced the spectrum

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

#### Scenario: A file-reading step fails

- **WHEN** a workflow fails to read force constants from a supplied file
- **THEN** the workflow terminates with exit code 410, reporting that force constants could not be read
- **AND** no downstream outputs are emitted
