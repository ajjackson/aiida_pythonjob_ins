## Purpose

Keep the test suite runnable anywhere without external services or manual setup,
and guarantee that running it never reads or modifies a developer's real AiiDA
installation.

## ADDED Requirements

### Requirement: The test session is hermetic with respect to AiiDA configuration

A test run SHALL use an ephemeral AiiDA configuration directory created for that
session and removed afterwards. It SHALL NOT read or modify a developer's real
AiiDA configuration, profiles or stored data, and SHALL behave identically whether
or not such an installation exists.

#### Scenario: Running with no existing AiiDA installation

- **WHEN** the suite is run on a machine that has never had AiiDA configured
- **THEN** collection and execution succeed, using a configuration created in a
  temporary directory

#### Scenario: Running alongside a developer's live installation

- **WHEN** the suite is run on a machine with an existing AiiDA configuration
- **THEN** that configuration is neither read nor modified, and the results are the
  same as on a fresh machine

#### Scenario: Configuration is established before AiiDA is imported

- **WHEN** a test module imports this package during collection, which causes
  `aiida-pythonjob` to read AiiDA configuration at import time
- **THEN** the ephemeral configuration is already in place, so collection does not
  fail with a missing-configuration error

#### Scenario: The temporary configuration is cleaned up

- **WHEN** the test session ends
- **THEN** the ephemeral configuration directory is removed

### Requirement: Tests require no external services

The suite SHALL run using AiiDA's official pytest fixtures with temporary,
throwaway profiles on a file-backed store. It SHALL NOT require PostgreSQL, a
message broker, or a running AiiDA daemon.

#### Scenario: A full run on a bare machine

- **WHEN** the suite is run in an environment with only the project's declared
  dependencies installed
- **THEN** every test runs to completion without any database or broker service

### Requirement: Job tests execute in the active environment

Tests that launch jobs SHALL use the interpreter running the tests as their
execution code, so the job environment always contains the package version under
test and its dependencies.

#### Scenario: The test code points at the running interpreter

- **WHEN** a test needs a code to run a job on localhost
- **THEN** an installed code is provided whose executable is the current
  interpreter and whose default plugin is the PythonJob calculation plugin

### Requirement: Scientific results are verified by equivalence, not golden values

Tests of scientific behaviour SHALL compare the AiiDA-wrapped result against a
direct call to the underlying public Euphonic API, rather than against
hard-coded reference numbers, with tolerances wide enough to absorb eigensolver
noise between processes but narrow enough to catch real regressions.

#### Scenario: A wrapped calculation is checked against a direct one

- **WHEN** a phonon calculation is run both through AiiDA and directly
- **THEN** the two results are compared numerically within a stated tolerance, and
  no reference frequency values appear in the test

### Requirement: The environment provides the tools AiiDA's scheduler needs

AiiDA's direct scheduler polls running jobs using the system process tools, so any
environment running the suite SHALL provide them. This SHALL be treated as a
declared environment requirement rather than worked around in code.

#### Scenario: A container image used for development

- **WHEN** a development container image is built for this project
- **THEN** it installs the system process tools required by the direct scheduler

### Requirement: Continuous integration runs the suite on every change

The project SHALL run its test suite automatically on pushes to the main branch
and on pull requests, on an x86-64 Linux runner using the project's pinned Python
version and its uv-based install, so that the platform-specific wheel workaround
is exercised only where it applies.

#### Scenario: A pull request is opened

- **WHEN** a pull request is opened against the repository
- **THEN** continuous integration installs the project with uv and runs the test
  suite, reporting failure if any test fails

#### Scenario: The runner resolves Euphonic from PyPI

- **WHEN** continuous integration installs dependencies on its x86-64 runner
- **THEN** Euphonic is resolved from PyPI, with no local wheel required
