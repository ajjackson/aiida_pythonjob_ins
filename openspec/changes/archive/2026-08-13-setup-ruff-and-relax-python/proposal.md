## Why

Continuous integration currently runs `pytest` but does not enforce linting or code formatting via `ruff`.
Additionally, `pyproject.toml` pins Python to `==3.12.*` strictly to support a local aarch64 Euphonic wheel workaround, forcing an unnecessary constraint on non-aarch64 developers and limiting Python version compatibility across environments.

Wiring `ruff check` and `ruff format --check` into CI ensures code quality automated gates, while relaxing `requires-python` to `>=3.11` (while preserving local wheel compatibility notes) permits broader Python ecosystem compatibility.

## What Changes

- Update GitHub Actions CI workflow (`.github/workflows/ci.yml`) to run `uv run ruff check` and `uv run ruff format --check`.
- Expand GitHub Actions test matrix across supported Python versions (3.11, 3.12, 3.13, and 3.14).
- Reflow hand-aligned comment blocks in `README.md` (or adjust ruff config/exclusions) so `ruff format --check` succeeds on clean codebase state.
- Update `pyproject.toml` `requires-python` from `==3.12.*` to `>=3.11`.
- Update packaging documentation notes where relevant regarding Python version requirements.

## Non-Goals

- Removing the local aarch64 wheel workaround itself (which depends on upstream PyPI releases).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `plugin-packaging`: updates the Python environment requirements to specify a `>=3.11` version bound instead of an exact `3.12` pin.
- `testing-and-ci`: updates continuous integration requirements to state that linting and formatting checks (`ruff`) are enforced automatically alongside the test suite.

## Impact

- `.github/workflows/ci.yml`: modified to include ruff lint and format check steps.
- `pyproject.toml`: `requires-python` constraint relaxed.
- `README.md`: code/example formatting aligned with ruff formatting rules.
- `openspec/specs/plugin-packaging/spec.md` & `openspec/specs/testing-and-ci/spec.md`: delta specs created for requirement updates.
