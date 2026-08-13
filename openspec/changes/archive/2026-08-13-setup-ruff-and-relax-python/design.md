## Context

See `proposal.md` - Why. The constraints for this change:

- `ruff` is already configured in `pyproject.toml` with line length and linter rules, and `ruff check` currently passes cleanly.
- `ruff format --check` currently fails due to hand-aligned comment blocks in `README.md`.
- `pyproject.toml` sets `requires-python = "==3.12.*"`, which was introduced due to a local aarch64 wheel built for 3.12, but restricts standard installation on Python 3.11 or 3.13.

## Goals / Non-Goals

**Goals:**
- Add `ruff check` and `ruff format --check` steps into `.github/workflows/ci.yml`.
- Expand GitHub Actions workflow test matrix to run on Python 3.11, 3.12, 3.13, and 3.14.
- Reflow hand-aligned comments in `README.md` so `ruff format --check` succeeds across all files.
- Relax `requires-python` in `pyproject.toml` to `>=3.11`.

**Non-Goals:**
- Changing existing ruff linting rule sets or line length configuration in `pyproject.toml`.

## Decisions

### 1. Separate "lint" job from "test" matrix job in CI

**Chosen: Split CI into a standalone `lint` job and a matrixed `test` job.**
*Rationale:* Static linting and code formatting checks (`ruff check` and `ruff format --check`) are Python-version-agnostic and fast. Running them in a single `lint` job before the `test` matrix avoids redundant checks and fails fast if formatting or linting fails, before triggering the full test suite across Python 3.11, 3.12, 3.13, and 3.14.

### 2. Reflow README.md hand-aligned comments vs. excluding Markdown from formatting

**Chosen: Reflow README.md hand-aligned comments.**
*Rationale:* Keeping formatting checks universal across the repo prevents formatting drift in documentation examples. Reflowing the hand-aligned block makes `ruff format --check` clean without requiring ignore patterns or custom exclusion overrides.

### 2. Set Python lower bound to `>=3.11` and test 3.11–3.14 in CI

**Chosen: Set `requires-python = ">=3.11"` and add a matrix for 3.11, 3.12, 3.13, and 3.14.**
*Rationale:* `aiida-core>=2.6` and `aiida-pythonjob` support Python 3.11+. Relaxing the pin allows downstream users and developers on Python 3.11 through 3.14 to install and run the package. Testing 3.11 through 3.14 in CI verifies compatibility across the supported Python releases.

## Risks / Trade-offs

- [Developers on aarch64 trying to use Python 3.11 or 3.13 with the local wheel] → The local pre-release wheel in `wheels/` is built for CPython 3.12. The `README.md` note documents that developers using the aarch64 local wheel specifically need a Python 3.12 virtualenv.

## Migration Plan

No runtime data or migration steps required. Pushing the change triggers the updated CI workflow.
