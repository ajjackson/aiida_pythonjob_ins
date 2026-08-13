## 1. Relax Python version requirement

- [x] 1.1 Update `pyproject.toml` `requires-python` from `==3.12.*` to `>=3.11`.
- [x] 1.2 Verify `uv sync` resolves correctly.

## 2. Reflow README formatting for ruff compatibility

- [x] 2.1 Reflow hand-aligned comments in `README.md` example blocks to pass `ruff format --check`.
- [x] 2.2 Run `uv run ruff check` and `uv run ruff format --check` locally to confirm zero errors.

## 3. Wire ruff checks and Python matrix into CI workflow

- [x] 3.1 Edit `.github/workflows/ci.yml` to create a `lint` job running `uv run ruff check` and `uv run ruff format --check` on a single Python version (e.g. 3.12).
- [x] 3.2 Update `.github/workflows/ci.yml` `test` job to depend on `lint` (`needs: lint`) and run the test suite across a matrix of Python 3.11, 3.12, 3.13, and 3.14.

## 4. Verification and Closeout

- [x] 4.1 Run full test suite (`uv run pytest`) and linting (`uv run ruff check` / `uv run ruff format --check`).
- [x] 4.2 Mark item 5 and item 11 in `openspec/changes/archive/2026-08-12-document-poc-baseline/design.md` as addressed.
