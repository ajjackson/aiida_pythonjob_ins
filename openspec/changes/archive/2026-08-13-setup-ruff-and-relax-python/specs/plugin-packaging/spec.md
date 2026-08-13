## MODIFIED Requirements

### Requirement: The distribution installs as a standard Python package

The distribution SHALL be named `aiida-pythonjob-ins` and provide the import
package `aiida_pythonjob_ins` from a src layout, SHALL declare its supported
Python version range as Python 3.11 or greater (`>=3.11`), and SHALL be built by a PEP 517 backend consistent with the
project's uv-based workflow.

#### Scenario: Installing provides the import package

- **WHEN** the distribution `aiida-pythonjob-ins` is installed
- **THEN** `aiida_pythonjob_ins` is importable

#### Scenario: The Python version requirement is enforced

- **WHEN** installation is attempted on a Python outside the declared supported
  version range
- **THEN** the installation is rejected by the declared requirement
