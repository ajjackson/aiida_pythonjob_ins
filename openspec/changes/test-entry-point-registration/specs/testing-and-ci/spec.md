## ADDED Requirements

### Requirement: Plugin registration is verified through the plugin factories

The suite SHALL verify that every class this package registers as an AiiDA plugin
is returned by the corresponding plugin factory when requested by its documented
entry-point name. Coverage SHALL be expressed per registered class, so that a
newly registered class without a corresponding case is a visible omission. The
verification SHALL exercise registration as installed in the environment under
test, rather than importing the classes directly.

#### Scenario: Each registered data type loads from the data factory

- **WHEN** a registered data type's documented entry-point name is requested from
  AiiDA's data factory
- **THEN** the factory returns that class

#### Scenario: Each registered workflow loads from the workflow factory

- **WHEN** a registered workflow's documented entry-point name is requested from
  AiiDA's workflow factory
- **THEN** the factory returns that class

#### Scenario: A registration that is removed or renamed is detected

- **WHEN** an entry-point declaration is removed, or its name changed, while the
  class itself remains importable
- **THEN** the suite fails

#### Scenario: Verification needs no stored data

- **WHEN** the registration checks run
- **THEN** they resolve the plugins without storing a node, submitting a job or
  requiring any service beyond the test session's own configuration
