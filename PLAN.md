# aiida-pythonjob-ins — Development Plan (PoC)

> Self-contained plan for a proof-of-concept AiiDA plugin that wraps
> inelastic-neutron-scattering (INS) Python libraries — starting with
> **Euphonic** — using the **`aiida-pythonjob`** Python-API execution model
> rather than command-line entry-point wrappers.
>
> This file is intended to be readable in a fresh LLM context with no other
> history. It restates the background, decisions, and step-by-step plan.

---

## 0. Quick context for a fresh session

- **Environment**: Sandboxed Podman container, non-root user `pi`, arch **aarch64**.
  Python is **not** on `PATH`; use **`uv`** for everything (`uv venv`, `uv run`,
  `uv sync`). See `/workspace/AGENTS.md` for sandbox rules (tmpfs `/home/pi`,
  persistent `/workspace`, no `sudo`, no in-container git).
- **Project location**: `/workspace/aiida_pythonjob_ins` (src-layout).
- **Distribution name**: `aiida-pythonjob-ins`. **Import package**: `aiida_pythonjob_ins`.
  Entry-point prefix: `pythonjob_ins`. (Names are generic because the package will
  host Euphonic + abinslib + resins wrappers, and signal the `aiida-pythonjob`
  execution model. Likely to be renamed later if the approach sticks.)
- **Euphonic wheel**: A prebuilt aarch64-Linux wheel is provided because PyPI has
  no aarch64-Linux 2.x wheel yet. The vendored file is
  `euphonic-2.0.1.dev1-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`
  (a 2.0.x pre-release build; the official release is 2.0.0). It requires
  **Python 3.12** and is placed in `wheels/` (gitignored).
- **Euphonic source repo**: When implementation starts, ask the user to expose the
  Euphonic repository read-only at `/inspect`. It contains the existing unit/script
  tests and reference data for phonon dispersion, to be reused as test fixtures.

### Reference libraries
- Euphonic — https://pypi.org/project/Euphonic/ (docs: https://euphonic.readthedocs.io/)
- abinslib — https://pypi.org/project/abinslib/ (future step)
- resins — https://pypi.org/project/resins (future step)

### Key AiiDA references
- AiiDA plugins overview — https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/plugins.html
- `aiida-pythonjob` — https://github.com/aiidateam/aiida-pythonjob
  (docs: https://aiida-pythonjob.readthedocs.io/)
- AiiDA pytest fixtures — https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/plugins.html#testing-a-plugin
  and `aiida.manage.tests.pytest_fixtures` (`aiida_profile`, `aiida_localhost`,
  `aiida_code_installed`, `aiida_computer`, ...).
- Related in-house effort / testing notes: https://github.com/stfc/alc-ux/issues/32

---

## 1. Goals

1. **Python-API execution**: Run Euphonic routines inside AiiDA via
   `aiida-pythonjob`, not by shelling out to a CLI. This keeps the scientific
   logic as ordinary importable Python functions.
2. **First scientific task**: Import force constants and compute a **phonon band
   structure (dispersion)** along a q-point path. Imitate the logic of
   `euphonic.cli.dispersion` but **do not depend on Euphonic private
   functions/methods** — use only the public API.
3. **Custom AiiDA Data types** for the two central data-exchange objects:
   `ForceConstants` and `QpointPhononModes`.
4. **Composable design**: Start with `PythonJob`-wrapped *atomic* operations, then
   compose them into a `WorkChain`/`WorkGraph`.
5. **Standard AiiDA hooks**: Implementation must interact with `Computer`/`Code`
   the standard way so it can run anywhere, even though tests use `localhost`.
6. **Testing from day one**: `pytest` with the official AiiDA fixtures; GitHub
   Actions running a simple `pytest` invocation on **x86-64 Linux**.
7. **Exemplar quality**: Generous comments citing the source docs/projects, while
   keeping the code itself concise.

### Explicitly out of scope for the PoC (future steps)
- `abinslib` and `resins` wrappers (planned as follow-on milestones).
- Remote/HPC scheduler execution (design keeps the hooks; tests stay on localhost).
- Rich custom Data types beyond `ForceConstants` / `QpointPhononModes`.
- Complex CI matrices, packaging to PyPI, docs site.

---

## 2. Technical stack & environment

- **Python**: 3.12 (pinned by the provided Euphonic wheel).
- **Package manager**: `uv` (`uv venv --python 3.12`, `uv sync`, `uv run pytest`).
- **Dependency-pinning principle** (this is a *plugin*, co-installed with others):
  bound each dependency by *our own* API usage; add upper caps only where
  individually justified; never mirror a sibling dependency's transitive
  constraints (the resolver intersects everyone's requirements). Avoid needlessly
  narrow pins that could conflict with other plugins.
- **Core dependencies** (see `pyproject.toml` for exact specifiers + rationale):
  - `aiida-core>=2.6,<3` — floor = our own use (SQLite test backend +
    `aiida.tools.pytest_fixtures`, both 2.6); `<3` because an aiida-core major
    bump would likely break plugin APIs. (aiida-pythonjob independently requires
    `>=2.7.1`, enforced by the resolver — we don't restate it.)
  - `aiida-pythonjob~=0.5.2` — pre-1.0 alpha, no documented stability policy;
    minor releases evolve the API, so pin to the tested 0.5.x series.
  - `euphonic~=2.0` (SemVer-compliant), except aarch64-Linux which uses the
    vendored 2.0.x pre-release wheel until a 2.x aarch64-Linux wheel is
    published on PyPI — see §6.
  - `seekpath>=2.2.1,<3` — we call `get_explicit_k_path_orig_cell` (preferred over
    the older path helper) and want 2.2.1's bugfixes/compat fixes. This coincides
    with Euphonic's pin (pace-neutrons/Euphonic#457) but is set for our own
    reasons, not to track Euphonic.
  - Dev: `pytest`, `ruff` (AiiDA fixtures come from `aiida.tools.pytest_fixtures`;
    the SQLite backend means no `pgtest`/PostgreSQL is required). Ruff runs a broad
    rule set modelled on Euphonic's (see `[tool.ruff.lint]` in `pyproject.toml`);
    intra-package imports are absolute (satisfies TID252).

---

## 3. Architecture & design

### 3.0 Native AiiDA materials-science types (KpointsData / BandsData)
We integrate AiiDA's built-in reciprocal-space types
(https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/data_types.html#materials-science-data-types):

- **`KpointsData`** is the q-point *specification* for Fourier interpolation
  (`ForceConstants` + `KpointsData` -> `QpointPhononModes`) and the natural
  representation of a band path (positions + high-symmetry labels + cell). The
  seekpath PythonJob returns a plain, picklable `QpointPath`
  (`qpoint_path.py`) that a registered serializer converts to `KpointsData`.
- **`BandsData`** (a `KpointsData` subclass) represents the output band
  structure. A Euphonic `QpointPhononModes` is essentially `BandsData`
  (frequencies) + eigenvectors, so we build `BandsData` by *composition*
  (`conversions.modes_to_bands_data`) and keep the eigenvectors in
  `QpointPhononModesData`. `BandsData.show_mpl()` / `export(..., 'mpl_png')`
  plots the dispersion with no AiiDALab dependency.

### 3.1 Custom Data types (`aiida_pythonjob_ins.data`)
Wrap Euphonic objects that move between steps. Euphonic objects expose public
`to_dict()` / `from_dict()` and JSON file round-trips, which we use for storage.

- **`ForceConstantsData`**
  - Stores the Euphonic `ForceConstants` object. Preferred storage: serialize via
    the public API to a file kept in the node repository (repository storage suits
    the potentially large force-constants arrays better than DB attributes).
  - Methods: `set_force_constants(fc)`, `get_force_constants() -> ForceConstants`.
  - Convenience constructors: `from_castep_bin(path)`, `from_phonopy(...)` using
    Euphonic's public readers.
- **`QpointPhononModesData`**
  - Stores frequencies + eigenvectors + q-points (a Euphonic `QpointPhononModes`).
  - Methods: `set_modes(modes)`, `get_modes() -> QpointPhononModes`.
  - Lightweight numeric arrays may additionally be surfaced via `ArrayData`-like
    accessors for downstream inspection.

Registered under the `aiida.data` entry-point group (see §5).

> Note for `aiida-pythonjob`: PythonJob serializes function inputs/outputs. Verify
> whether custom Data types need registered serializers/deserializers for
> pythonjob, or whether functions should accept/return plain Euphonic objects and
> let thin wrapper `calcfunction`s convert to/from our Data types. Decide during
> implementation; prefer the simplest approach that keeps provenance.

### 3.2 Atomic operations (`aiida_pythonjob_ins.calculations`)
Plain Python functions wrapped for execution with `aiida-pythonjob`:

1. `read_force_constants(...)` → `ForceConstantsData`
   - Read a `.castep_bin` / `phonopy.yaml` into a Euphonic `ForceConstants`.
2. `calculate_dispersion(force_constants, qpath_params)` → `QpointPhononModesData`
   - Build a q-point path and interpolate phonon frequencies/eigenvectors.
   - Mirror the *public-API* logic of `euphonic.cli.dispersion`.
3. (later) `calculate_dos`, `structure_factor`, etc.

### 3.3 Composition (`aiida_pythonjob_ins.workflows`)
- A `WorkChain` (or `aiida-workgraph` graph) that chains
  `read_force_constants → calculate_dispersion` and returns the band structure.
- Demonstrates provenance across multiple PythonJob steps.

### 3.4 Standard Computer/Code hooks
- Tests target `aiida_localhost` + a locally-installed Python `Code`, but the
  calculation/workflow accept a `code`/`computer` in the standard AiiDA way so the
  same code can target a remote scheduler unchanged.

### 3.5 PythonJob execution model & the Code environment
How a `PythonJob` step actually runs (verified against aiida-pythonjob 0.5.2
source: `calculations/pythonjob.py`, `calculations/utils.py`, `utils.py`):

- **Parent (AiiDA) side, per step**: input nodes are converted to raw Python via
  our deserializers (e.g. `ForceConstantsData -> euphonic.ForceConstants`,
  `KpointsData -> ndarray`); the function and inputs are cloudpickled
  (`function.pkl`, `inputs.pickle`); `script.py` and any `upload_files` are staged.
  After the run, `results.pickle` is loaded and outputs are serialized back to
  nodes via our serializers.
- **Remote (Code) side**: `python script.py` imports `cloudpickle`, loads the two
  pickles, calls `function(**inputs)`, writes `results.pickle`. It never imports
  aiida.
- **Function pickling** (`build_function_data` / `inspect_function`):
  - a *module-level* function in an installed package (our case) -> pickled **by
    reference** (module + name); the remote must import the defining module.
  - a function in `__main__` or a *nested* callable -> pickled **by value**
    (source/bytecode shipped); the remote does *not* need the package. (This is
    why the aiida-pythonjob docs' auto-created conda env installs only science
    libs and no plugin: their example functions are defined inline in `__main__`.)
  - `register_pickle_by_value=True` forces by-value even for an installed module.

- **What the remote (Code) environment must contain**:
  - Always: `cloudpickle` + whatever the function imports (`numpy`, `seekpath`,
    `euphonic`). (`node_graph` only if you pass an inputs/outputs spec; we don't.)
  - **By reference (our default)**: also the defining module must be importable.
    Because our ops live under `calculations/`, whose `__init__` imports
    aiida-pythonjob, importing the ops by reference currently also pulls in
    aiida-core -> the remote ends up ~equivalent to a full plugin install.
  - **By value** (`register_pickle_by_value=True`): the plugin need not be
    installed remotely; only `cloudpickle` + `numpy` + `seekpath` + `euphonic`.
    Note the env saving is just "skip aiida + the plugin" -- euphonic (the heavy
    dep) is still required. (Restructuring the pure ops into an aiida-free module
    would give the same env saving while keeping by-reference.)
- **euphonic in the *parent*** is required by our current design (Data classes
  import euphonic at load; parent-side (de)serialization builds/unpickles euphonic
  objects). It is avoidable only by keeping euphonic imports lazy and exchanging
  plain data (JSON/arrays) across the PythonJob boundary rather than euphonic
  objects.
- **By-reference vs by-value at scale**: by-reference ships a tiny module+name
  string per job and stores nothing extra in provenance; by-value re-serializes
  the function/module code on *every* submission, which aiida-pythonjob stores per
  calculation node -- so at production scale (many jobs) by-value inflates network
  transfer, submission time, and the AiiDA repository/DB. **By-reference is the
  better production default** (and is what we use); reserve by-value for notebooks/
  experiments or when the package genuinely cannot be installed remotely.
- **Providing the Code environment**: prefer *deriving* it from the project's
  pinned deps (e.g. `uv export`) over a hand-maintained requirements file, which
  drifts. cloudpickle round-trips are sensitive to version skew (cloudpickle
  version, numpy ABI, euphonic version), so keeping the two environments closely
  matched is a feature, not overhead.

---

## 4. Project layout (src-layout)

```
aiida_pythonjob_ins/
├── PLAN.md                         # this file
├── pyproject.toml                  # metadata, deps, entry points, uv sources
├── uv.lock
├── README.md
├── wheels/                         # vendored aarch64 euphonic wheel (gitignored)
│   └── euphonic-...aarch64.whl
├── src/
│   └── aiida_pythonjob_ins/
│       ├── __init__.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── force_constants.py
│       │   └── qpoint_phonon_modes.py
│       ├── calculations/
│       │   ├── __init__.py
│       │   └── euphonic_ops.py     # read_force_constants, calculate_dispersion
│       └── workflows/
│           ├── __init__.py
│           └── dispersion.py       # WorkChain / WorkGraph composition
└── tests/
    ├── conftest.py                 # enable aiida pytest fixtures
    ├── data/                       # reference inputs (from Euphonic /inspect)
    ├── test_data_types.py
    ├── test_calculations.py
    └── test_workflows.py
```

---

## 5. Entry points (in `pyproject.toml`)

```toml
[project.entry-points."aiida.data"]
"pythonjob_ins.force_constants" = "aiida_pythonjob_ins.data.force_constants:ForceConstantsData"
"pythonjob_ins.qpoint_phonon_modes" = "aiida_pythonjob_ins.data.qpoint_phonon_modes:QpointPhononModesData"

# Calculations/workflows exposed as needed once implemented, e.g.:
# [project.entry-points."aiida.workflows"]
# "pythonjob_ins.dispersion" = "aiida_pythonjob_ins.workflows.dispersion:DispersionWorkChain"
```

---

## 6. Euphonic wheel handling (aarch64 workaround)

Use `uv` per-package sources with an environment marker so the vendored wheel is
only used on aarch64; every other platform (x86-64 CI) resolves from PyPI:

```toml
[project]
dependencies = ["euphonic~=2.0", "aiida-core", "aiida-pythonjob"]

[tool.uv.sources]
euphonic = [
  { path = "wheels/euphonic-2.0.1.dev1-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl",
    marker = "platform_machine == 'aarch64'" },
]
```

- On **x86-64** the marker is false → Euphonic comes from PyPI automatically.
- On **aarch64** uv installs the vendored wheel.
- When aarch64 wheels reach PyPI, delete the `[tool.uv.sources]` block; nothing
  else changes.
- **Repo hygiene**: the wheel is extracted from
  `/workspace/wheel-manylinux-3.12-aarch64.zip` into `wheels/` and **gitignored**
  (CI never needs it). Document in README that aarch64 devs must place the wheel
  there. *(Override this if you'd rather commit the wheel.)*

---

## 7. Testing strategy

- **Framework**: `pytest`, run via `uv run pytest`.
- **AiiDA fixtures**: enable `aiida.manage.tests.pytest_fixtures` in
  `tests/conftest.py` (`pytest_plugins = ["aiida.manage.tests.pytest_fixtures"]`).
  Use `aiida_profile` (temporary throwaway profile), `aiida_localhost`
  (Computer), and `aiida_code_installed` (Code) so no external services are needed.
- **Reference data**: reuse Euphonic's phonon-dispersion test data/fixtures from
  the `/inspect` repo; copy minimal inputs into `tests/data/`.
- **Test tiers**:
  1. `test_data_types.py` — round-trip `ForceConstantsData` /
     `QpointPhononModesData` (store → reload → compare against Euphonic objects).
  2. `test_calculations.py` — run each PythonJob op on `aiida_localhost`; check
     frequencies against known-good values (regression/allclose).
  3. `test_workflows.py` — run the composed WorkChain end-to-end; assert
     provenance links and final band structure.
- Notes/decisions from https://github.com/stfc/alc-ux/issues/32 to be folded in.

---

## 8. GitHub Actions (kept minimal)

- Runner: **`ubuntu-latest` (x86-64)** → Euphonic installs from PyPI (no wheel).
- Steps: checkout → install `uv` (`astral-sh/setup-uv`) → `uv sync` →
  `uv run pytest`.
- Python 3.12 to match the local dev pin.
- Keep it to a single job / single `pytest` invocation for now; expand later.

---

## 9. Milestones / step-by-step

1. [x] **Scaffold**: `pyproject.toml` (metadata, deps, entry points, uv sources),
   src-layout packages, Python 3.12 pin, wheel extracted to `wheels/`, `uv sync`.
2. [x] **Data types**: `ForceConstantsData` and `QpointPhononModesData` with
   round-trip tests (`tests/test_data_types.py`).
3. [x] **Atomic ops**: `read_force_constants_from_castep`, `generate_qpoint_path`
   (seekpath) and `interpolate_phonon_modes` (public API only), wrapped with
   `aiida-pythonjob`, tested on localhost (`tests/test_calculations.py`).
4. [x] **Native types + workflow**: KpointsData q-point spec, BandsData output
   (`conversions.py`), and `DispersionWorkChain` composing three PythonJobs;
   E2E + conversion tests (`tests/test_workflows.py`, `tests/test_conversions.py`).
5. [x] **CI**: minimal GitHub Actions workflow (`.github/workflows/ci.yml`),
   x86-64, `uv sync` + `uv run pytest`.
6. [x] **Docs**: README with setup, wheel note, and usage example.
7. [ ] **Future**: add `abinslib`, then `resins` wrappers as new op/data modules,
   reusing the same PythonJob + Data-type patterns.

### Implementation notes / decisions made

- **AiiDA test profile**: use `aiida.tools.pytest_fixtures` (not the deprecated
  `aiida.manage.tests.pytest_fixtures`); its default profile uses the SQLite
  backend, so **no PostgreSQL** is needed.
- **System dependency**: AiiDA's `DirectScheduler` polls jobs with `ps`, so the
  runtime needs `procps` installed (CI runners have it; the dev container needed
  a one-off `just root-install ... procps`).
- **PythonJob type hints**: aiida-pythonjob resolves a function's annotations at
  runtime via `typing.get_type_hints`, so annotated types (e.g. `ForceConstants`)
  must be importable at module load time — do **not** hide them behind
  `TYPE_CHECKING`.
- **Custom Data <-> Euphonic bridging**: pass `serializers`/`deserializers` dicts
  explicitly to `prepare_pythonjob_inputs` (see `serialization.py`) rather than
  overloading `aiida.data` entry-point names; keeps one clean entry point per
  Data class. Our Data class constructors double as serializers
  (`ForceConstantsData(fc, user=...)`).
- **PythonJob return types & structured outputs**: aiida-pythonjob treats a
  `@dataclass` (or TypedDict/NamedTuple) return annotation as a *structured*
  multi-output spec (one output port per field), bypassing type-based
  serializers. `QpointPath` is therefore a **plain class** so it serializes as a
  single `result` output -> `KpointsData`.
- **procps in the image**: added `procps` to the repo `Containerfile` so fresh
  dev containers have `ps` for AiiDA's DirectScheduler (was a manual install).
- **Logging (not print)**: the atomic ops use a module `logging` logger
  (`euphonic_ops.LOGGER`) with lazy `%`-style messages; the `T20` ruff rule bans
  stray `print`. Library code only *emits* logs (never configures handlers/levels),
  so INFO messages surface only when the host/AiiDA enables them; inside a
  PythonJob they are not shown at INFO by default (Python's default surfaces only
  WARNING+ to stderr). A `caplog` test (`test_operations_emit_logs`) verifies
  emission. WorkChains should use `self.report(...)` for step-level messages.
- **Build backend**: `uv_build` (uv's native backend) for consistency with the
  uv-based workflow; `setuptools` is the conservative "established standard"
  alternative. The distribution (`aiida-pythonjob-ins`) normalizes to the import
  package (`aiida_pythonjob_ins`), so `uv_build` derives the module name
  automatically -- no `[tool.uv.build-backend]` override needed.
- **Import-time config requirement (test collection)**: aiida-pythonjob builds
  its serializer registry at import time via `get_config()`. With no existing
  AiiDA config this raises `MissingConfigurationError` during pytest *collection*
  (before fixtures run) as soon as a test module imports our package. `conftest.py`
  handles this at module top (before importing aiida) by pointing `AIIDA_PATH` at
  an ephemeral `tempfile.mkdtemp()` directory and calling `get_config(create=True)`
  there, then removing it in `pytest_unconfigure`. This makes the session
  hermetic: it runs the same with or without an existing config, and a developer's
  real, live `~/.aiida` is never read or mutated. The `aiida_profile` fixtures
  still supply isolated temp profiles.
- **PythonJob Code**: the code's executable must be a Python interpreter with
  this package + euphonic installed; tests point it at `sys.executable`.
- **Equivalence testing**: rather than hard-coding reference frequencies, tests
  compare the AiiDA-wrapped result against a direct public-API Euphonic call.
  Tolerances (`rtol=1e-3, atol=0.05 meV`) absorb eigensolver noise on
  near-degenerate acoustic modes between the in-process and subprocess runs.
- **Euphonic version skew**: aarch64 dev uses the vendored 2.0.1.dev1 wheel;
  x86-64 CI resolves euphonic 2.0.0 from PyPI. Both are 2.x, so the public API
  matches; revisit if CI surfaces differences.
- **Test data**: `tests/data/quartz.castep_bin` copied from the Euphonic test
  suite (canonical example material).

---

## 10. Open items to confirm during implementation

- Exact force-constants input format for the first test (CASTEP `.castep_bin`
  vs Phonopy) — decide from what `/inspect` provides.
- Whether `aiida-pythonjob` needs custom serializers for our Data types, or if
  thin `calcfunction` adapters around plain Euphonic objects are cleaner.
- q-path specification API for `calculate_dispersion` (explicit q-points vs
  seekpath/spglib high-symmetry path); prefer public, well-documented input.
</content>
</invoke>
