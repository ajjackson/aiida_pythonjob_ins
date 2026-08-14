## MODIFIED Requirements

### Requirement: Worked examples are executed when the documentation is built

The documentation SHALL include runnable examples that execute real workflows
during the build, so a broken example fails the build rather than silently
misleading readers. Each example SHALL present both its scientific result and the
provenance graph that produced it, and SHALL be downloadable as a notebook. Worked
examples and project README examples SHALL demonstrate loading custom data nodes
and workflows through AiiDA's standard plugin factories (`DataFactory` and `WorkflowFactory`)
as the primary pattern, noting that direct class imports are also supported.

#### Scenario: Examples cover the supported inputs and both workflows

- **WHEN** the example gallery is built
- **THEN** it includes a band structure from CASTEP input, a density of states from
  CASTEP input, and both quantities from Phonopy input

#### Scenario: Each example shows its provenance

- **WHEN** an example runs during the build
- **THEN** it renders the scientific result as a figure and the resulting AiiDA
  provenance graph as a second figure

#### Scenario: Examples use bundled sample data

- **WHEN** an example needs input data
- **THEN** it locates the sample files bundled in the repository at runtime, rather
  than downloading them or requiring the reader to supply them

#### Scenario: Examples use plugin factories for loading classes

- **WHEN** an example or README snippet loads a registered data type or workflow
- **THEN** it demonstrates loading via `DataFactory` or `WorkflowFactory`, with a brief note that direct class imports are also supported

### Requirement: Workflow interfaces are documented from their runtime spec

A WorkChain's interface is defined at runtime and is invisible to static analysis,
which would otherwise expose only its internal step methods. The documentation
SHALL therefore render workflow interfaces from the live process specification,
and SHALL keep the misleading static view out of the API reference. The workflow
documentation SHALL explicitly document the WorkChain exit codes defined by the
package (including exit code 400 `ERROR_SUB_PROCESS_FAILED`).

#### Scenario: A workflow page shows its real interface

- **WHEN** the documentation is built
- **THEN** each workflow's page lists its actual inputs, outputs, exit codes and outline

#### Scenario: Outline methods are not presented as the public interface

- **WHEN** the generated API reference is built
- **THEN** WorkChain classes are excluded from it, so their internal step methods
  are not shown in place of their interface
