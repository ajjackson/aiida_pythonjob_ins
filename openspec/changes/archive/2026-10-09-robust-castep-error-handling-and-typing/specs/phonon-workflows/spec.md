# Spec Delta: phonon-workflows

## MODIFIED Requirements

### Requirement: A failed step terminates the workflow with a distinct exit code

If a step does not finish successfully, the workflow SHALL stop and return a
dedicated failure exit code rather than proceeding with missing results.

#### Scenario: A job step fails

- **WHEN** any `PythonJob` step of a workflow finishes unsuccessfully
- **THEN** the workflow terminates with exit code 400, reporting that a job step
  did not finish successfully
- **AND** no downstream outputs are emitted

#### Scenario: Force constants cannot be read

- **WHEN** a workflow is launched with a file that cannot be read as CASTEP force
  constants, including truncated binary data, corrupt record markers, unsupported
  CASTEP versions, or calculation outputs lacking force constants
- **THEN** the workflow terminates with an exit code dedicated to failing to
  obtain force constants, distinct from exit code 400, reporting why
- **AND** no downstream outputs are emitted
