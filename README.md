# aiida-pythonjob-ins

**This is a prototype thrown together quickly with agentic coding. DO NOT USE IN PRODUCTION.**


Proof-of-concept [AiiDA](https://www.aiida.net/) plugin that wraps inelastic
neutron scattering (INS) Python libraries — starting with
[Euphonic](https://euphonic.readthedocs.io/) — using the
[`aiida-pythonjob`](https://github.com/aiidateam/aiida-pythonjob) execution model
(running Python functions as AiiDA jobs) rather than command-line wrappers.

The behaviour this package guarantees is specified in [`openspec/specs/`](./openspec/specs/),
and the reasoning behind the design is recorded in
[`docs/source/design_notes.rst`](./docs/source/design_notes.rst).

## Goals

The proof of concept set out to:

- Run Euphonic routines through the Python API inside AiiDA, rather than by
  shelling out to a command line, so the scientific logic stays as ordinary
  importable Python functions.
- Use only Euphonic's public API, depending on no private functions or methods.
- Provide custom AiiDA data types for the central objects passed between steps,
  force constants and q-point phonon modes.
- Start from `PythonJob`-wrapped atomic operations and compose them into
  workflows.
- Interact with `Computer` and `Code` in the standard AiiDA way, so the same code
  can run anywhere, even though the tests run on localhost.
- Test from the outset with `pytest` and the official AiiDA fixtures, run in
  continuous integration.
- Comment generously, citing the source documentation and projects, while keeping
  the code itself concise.

The first scientific target was importing force constants and computing a phonon
band structure along a q-point path, following the logic of
`euphonic.cli.dispersion`.

Deliberately out of scope: `abinslib` and `resins` wrappers, remote and HPC
scheduler execution (the hooks are there, but the tests stay on localhost),
richer data types beyond the three implemented, complex CI matrices, and
publishing to PyPI.

## Development setup

This project uses [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync          # create .venv and install deps (+ dev group)
uv run pytest    # run the test suite
```

### aarch64 Euphonic wheel (local workaround)

Euphonic is pinned to `~=2.0`. On **aarch64-Linux**, PyPI has no 2.x wheel yet,
so `uv` finds a local 2.0.x pre-release wheel in `wheels/` via `tool.uv.find-links`
in `pyproject.toml`. On x86-64 CI (where `wheels/` is empty or missing), `uv` installs
Euphonic 2.x directly from PyPI normally.

The wheel is **not** committed (see `.gitignore`). On aarch64-Linux, place it
manually:

```bash
mkdir -p wheels
# extract euphonic-...aarch64.whl into wheels/
```

Once an aarch64-Linux Euphonic 2.x wheel is published, delete the `[tool.uv]`
block from `pyproject.toml`.

## What's implemented

- **Custom data types**: `ForceConstantsData`, `QpointPhononModesData`,
  `EuphonicCrystalData` (wrap Euphonic objects via their public JSON round-trip,
  stored in the node repository). `EuphonicCrystalData` bridges euphonic's
  `Crystal` to/from AiiDA's native `StructureData`.
- **Native AiiDA types**: the force constants' crystal is exposed as a
  `StructureData` (no ASE dependency), from which a `KpointsData` band path is
  built (also the *input* q-point specification for Fourier interpolation).
  Results map to `BandsData` (frequencies as bands), so `bands.show_mpl()` plots
  the phonon band structure with no AiiDALab dependency.
- **Atomic operations** (plain public-API functions): `band_path_qpoints`
  (seekpath; structure only), `read_force_constants_from_castep` and
  `interpolate_phonon_modes` (plus a `calculate_dispersion` convenience), and
  `calculate_tosca_spectrum` (inelastic-neutron-scattering intensities via
  `abinslib` + `resins`). The compute-heavy ops run as `aiida-pythonjob`
  `PythonJob`s.
- **Input formats**: read force constants from CASTEP (`.castep_bin`) or from
  Phonopy output (`phonopy.yaml` + `FORCE_CONSTANTS` [+ `BORN`]); read phonon
  modes from a Euphonic `QpointPhononModes` JSON dump.
- **Workflows** starting from force constants (each accepts a `castep_file` *or*
  a pre-built `force_constants` node, so they work equally from CASTEP or
  Phonopy input):
  - `DispersionWorkChain` chains a read PythonJob with three `calcfunction`s
    (extract structure, build q-point path, compose `BandsData`) and an
    interpolation PythonJob, with full provenance.
  - `DosWorkChain` computes a phonon density of states (Monkhorst-Pack sampling +
    adaptive broadening) as a native `XyData`.
  - `ToscaFromForceConstantsWorkChain` samples modes across the Brillouin zone
    and delegates to `ToscaFromModesWorkChain` below, re-exposing its outputs.
- **Workflows** starting from phonon modes:
  - `ToscaFromModesWorkChain` simulates the spectrum the TOSCA spectrometer
    would record: a PythonJob computes the full line set (per atom, quantum
    order and detector bank) as a native `XyData`, then `calcfunction`s group
    and resolution-broaden it. Splitting the steps this way means regrouping
    reuses the cached intensity calculation.

## Usage sketch

```python
import matplotlib
from aiida import load_profile, orm
from aiida.engine import run_get_node
from aiida.plugins import WorkflowFactory

load_profile()

# Load plugins via standard AiiDA factories (direct imports like
# `from aiida_pythonjob_ins.workflows import DispersionWorkChain` also work)
DispersionWorkChain = WorkflowFactory("pythonjob_ins.dispersion")

# A Python `Code` on some computer (here: interpreter with euphonic installed).
code = orm.load_code("python3@localhost")

results, node = run_get_node(
    DispersionWorkChain,
    castep_file=orm.SinglefileData("quartz.castep_bin"),
    q_spacing=orm.Float(0.025),
    code=code,
)

results["band_path"]  # KpointsData: q-point path + high-symmetry labels
results["band_structure"]  # BandsData: phonon band structure
results["phonon_modes"]  # QpointPhononModesData: frequencies + eigenvectors

# Plot with the native AiiDA/matplotlib tooling (no AiiDALab needed):
results["band_structure"].show_mpl()

# Or drop back to Euphonic objects when needed:
modes = results["phonon_modes"].get_modes()  # euphonic.QpointPhononModes
spectrum = modes.get_dispersion()  # euphonic.Spectrum1D
```

See `tests/` for runnable examples using the official AiiDA pytest fixtures.

## Documentation

Sphinx docs combine API reference (`sphinx-autoapi`) with a runnable tutorial
gallery (`sphinx-gallery`): each example executes a real AiiDA workflow, plots the
result, and visualises the provenance graph. Build them with:

```bash
uv run --group doc make -C docs html   # needs system Graphviz + procps
```

Output lands in `docs/build/html`. The gallery runs in a throwaway in-memory AiiDA
profile, so it never touches your real `~/.aiida`.

## Logging

The atomic operations emit progress messages through the standard `logging`
module under the `aiida_pythonjob_ins` logger namespace. As a library, this
package only *emits* logs; it never installs handlers or sets levels, so you
control verbosity from your application:

```python
import logging

# Show INFO-level messages from this package (basicConfig adds a stderr handler):
logging.basicConfig(level=logging.WARNING)
logging.getLogger("aiida_pythonjob_ins").setLevel(logging.INFO)
```

Use `logging.DEBUG` for more detail, or `logging.WARNING` (the effective default)
to silence progress messages. Because the package logger is separate from
AiiDA's own `aiida` logger, changing this level does not affect AiiDA's logging.

When an operation runs inside a `PythonJob` (a separate process), its stdout and
stderr are captured into the calculation's retrieved files. To have INFO logs
appear there, raise the level inside that process — e.g. via the code's
`prepend_text`, or AiiDA's logging configuration (`verdi config set`).

## Roadmap

Next: `abinslib` and `resins` wrappers reusing the same PythonJob and custom-data
pattern. Work that this proof of concept deliberately left undone is recorded
under "Deferred work" in the archived baseline change in
[`openspec/changes/archive/`](./openspec/changes/archive/); each item is intended
to become its own change proposed against the specs.

## References

- Euphonic — [docs](https://euphonic.readthedocs.io/),
  [PyPI](https://pypi.org/project/Euphonic/)
- [`abinslib`](https://pypi.org/project/abinslib/) and
  [`resins`](https://pypi.org/project/resins) — future wrapper targets
- [`aiida-pythonjob`](https://github.com/aiidateam/aiida-pythonjob) —
  [docs](https://aiida-pythonjob.readthedocs.io/)
- [Writing AiiDA plugins](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/plugins.html)
  and [testing them](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/plugins.html#testing-a-plugin)
- [AiiDA materials-science data types](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/data_types.html#materials-science-data-types)
- Related in-house effort, with testing notes:
  [stfc/alc-ux#32](https://github.com/stfc/alc-ux/issues/32)
