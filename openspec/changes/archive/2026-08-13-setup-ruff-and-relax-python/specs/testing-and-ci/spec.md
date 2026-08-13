## MODIFIED Requirements

### Requirement: Continuous integration runs the suite on every change

The project SHALL run its test suite and static analysis (linting and code formatting checks via `ruff`) automatically on pushes to the main branch
and on pull requests, across a matrix of supported Python versions (3.11, 3.12, 3.13, and 3.14), installing dependencies from
the project's declared configuration. Coverage SHALL include the primary target
platform, x86-64 Linux; extending it to further platforms SHALL NOT require any
change to this requirement.

#### Scenario: A pull request is opened

- **WHEN** a pull request is opened against the repository
- **THEN** continuous integration installs the project, verifies code formatting and linting rules with ruff, and runs the test suite across the Python version matrix,
  reporting failure if any step fails

#### Scenario: The primary target platform is covered

- **WHEN** the continuous integration configuration is inspected
- **THEN** it runs the suite on x86-64 Linux across Python versions 3.11, 3.12, 3.13, and 3.14
