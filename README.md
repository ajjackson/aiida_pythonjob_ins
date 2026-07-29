# aiida-python-ins

Proof-of-concept [AiiDA](https://www.aiida.net/) plugin that wraps inelastic
neutron scattering (INS) Python libraries — starting with
[Euphonic](https://euphonic.readthedocs.io/) — using the
[`aiida-pythonjob`](https://github.com/aiidateam/aiida-pythonjob) execution model
(running Python functions as AiiDA jobs) rather than command-line wrappers.

See [`PLAN.md`](./PLAN.md) for the design and roadmap.

## Development setup

This project uses [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync          # create .venv and install deps (+ dev group)
uv run pytest    # run the test suite
```

### aarch64 Euphonic wheel (local workaround)

PyPI has no aarch64 wheel for Euphonic yet. On aarch64, `uv` installs a vendored
wheel from `wheels/` (selected via a `platform_machine == 'aarch64'` marker in
`pyproject.toml`); on x86-64 (e.g. CI) Euphonic is resolved from PyPI normally.

The wheel is **not** committed (see `.gitignore`). On aarch64, place it manually:

```bash
mkdir -p wheels
# extract euphonic-...aarch64.whl into wheels/
```

Once aarch64 wheels are published to PyPI, delete the `[tool.uv.sources]` block.

## What's implemented

- **Custom data types**: `ForceConstantsData`, `QpointPhononModesData` (wrap
  Euphonic objects via their public JSON round-trip, stored in the node
  repository).
- **Native AiiDA types**: the seekpath step returns a `KpointsData` (q-point path
  with high-symmetry labels), which is also the *input* q-point specification for
  Fourier interpolation. Results map to `BandsData` (frequencies as bands), so
  `bands.show_mpl()` plots the phonon band structure with no AiiDALab dependency.
- **Atomic operations** (plain public-API functions, run as `aiida-pythonjob`
  `PythonJob`s): `read_force_constants_from_castep`, `generate_qpoint_path`,
  `interpolate_phonon_modes` (plus a `calculate_dispersion` convenience).
- **Workflow**: `DispersionWorkChain` chains three PythonJobs (read force
  constants -> seekpath q-point path -> interpolate modes) and composes a
  `BandsData`, with full provenance.

## Usage sketch

```python
import matplotlib
from aiida import load_profile, orm
from aiida.engine import run_get_node
from aiida_pythonjob_ins.workflows import DispersionWorkChain

load_profile()

# A Python `Code` on some computer (here: interpreter with euphonic installed).
code = orm.load_code("python3@localhost")

results, node = run_get_node(
    DispersionWorkChain,
    castep_file=orm.SinglefileData("quartz.castep_bin"),
    q_spacing=orm.Float(0.025),
    code=code,
)

results["band_path"]      # KpointsData: q-point path + high-symmetry labels
results["band_structure"] # BandsData: phonon band structure
results["phonon_modes"]   # QpointPhononModesData: frequencies + eigenvectors

# Plot with the native AiiDA/matplotlib tooling (no AiiDALab needed):
results["band_structure"].show_mpl()

# Or drop back to Euphonic objects when needed:
modes = results["phonon_modes"].get_modes()  # euphonic.QpointPhononModes
spectrum = modes.get_dispersion()            # euphonic.Spectrum1D
```

See `tests/` for runnable examples using the official AiiDA pytest fixtures.

## Roadmap

See [`PLAN.md`](./PLAN.md). Next: `abinslib` and `resins` wrappers reusing the
same PythonJob + custom-Data pattern.
