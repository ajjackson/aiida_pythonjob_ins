"""Atomic Euphonic operations, written as plain Python functions.

These functions use only the **public** Euphonic API and know nothing about
AiiDA, so they can be unit-tested directly and reused elsewhere. Crucially, this
module's import chain is AiiDA-free (the package ``__init__`` is empty), so
by-reference cloudpickling can target a lean remote environment (euphonic +
seekpath + numpy, no aiida). They are turned into AiiDA PythonJobs by the
helpers in :mod:`aiida_pythonjob_ins.pythonjobs`.

The dispersion workflow is built from composable pieces, mirroring
``euphonic.cli.dispersion`` (https://euphonic.readthedocs.io/en/stable/cli.html)
without relying on Euphonic's private ``_bands_from_force_constants`` helper:

1. :func:`band_path_qpoints` -- build a high-symmetry q-point path (seekpath).
2. :func:`interpolate_phonon_modes` -- Fourier-interpolate modes at those points.

``calculate_dispersion`` is a convenience that chains the two. The band path is
turned into a native ``KpointsData`` by a parent-side ``calcfunction`` (see
:func:`aiida_pythonjob_ins.workflows.dispersion.generate_band_path`), so these
functions stay AiiDA-free and unit-testable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
import seekpath

if TYPE_CHECKING:
    import pint

# Imported at module level (not under TYPE_CHECKING) because aiida-pythonjob
# resolves the function's type hints at runtime via ``typing.get_type_hints``.
from euphonic import ForceConstants, QpointPhononModes, Quantity, Spectrum1D, ureg
from euphonic.util import mode_gradients_to_widths, mp_grid

# Library code only *emits* logs; it never configures handlers or levels -- the
# host application (or AiiDA) decides how these are surfaced. When these functions
# run inside a PythonJob, their stdout/stderr are captured into the job's retrieved
# files, so configured logging is preserved in provenance.
LOGGER = logging.getLogger(__name__)


class QpointPath(NamedTuple):
    """A high-symmetry q-point path: positions + labels + cell (no energies).

    A well-defined return type for :func:`band_path_qpoints`. It is a plain
    ``NamedTuple`` used purely on the Python side; the parent-side
    ``generate_band_path`` calcfunction turns it into a native ``KpointsData``.

    (Note: aiida-pythonjob would treat a ``NamedTuple`` *return annotation* as a
    structured multi-output spec, splitting it into one output port per field. That
    does not apply here because ``band_path_qpoints`` is not used as a PythonJob
    ``function`` -- if it were, the split into qpoints/labels/cell could even be
    desirable.)
    """

    qpoints: np.ndarray
    labels: list[tuple[int, str]]
    cell: np.ndarray


def read_force_constants_from_castep(filename: str | Path) -> ForceConstants:
    """Read a CASTEP ``.castep_bin``/``.check`` file into ``ForceConstants``.

    A thin wrapper over ``ForceConstants.from_castep``. It exists because a
    PythonJob's ``function`` must be a plain module-level function: a bound
    classmethod (``ForceConstants.from_castep``) is a ``method``, not a
    ``FunctionType``, so aiida-pythonjob's ``build_function_data`` rejects it. The
    wrapper is also where we attach logging.

    ``filename`` is resolved relative to the working directory. When run as a
    PythonJob the CASTEP file is staged there via ``upload_files`` (see
    :func:`aiida_pythonjob_ins.pythonjobs.prepare_read_force_constants_inputs`).
    """
    LOGGER.info("Reading force constants from CASTEP file: %s", filename)
    return ForceConstants.from_castep(filename)


def read_force_constants_from_phonopy(
    summary_name: str = "phonopy.yaml",
    fc_name: str = "FORCE_CONSTANTS",
    born_name: str | None = None,
) -> ForceConstants:
    """Read force constants from Phonopy output into ``ForceConstants``.

    Thin wrapper over ``ForceConstants.from_phonopy`` (requires euphonic's
    ``phonopy-reader`` extra, which this package installs by default). All names
    are resolved in the working directory; when run as a PythonJob the files are
    staged there via ``upload_files`` (see
    :func:`aiida_pythonjob_ins.pythonjobs.prepare_read_phonopy_inputs`).

    ``born_name`` is optional (Born charges for LO-TO splitting); pass ``None`` to
    skip it.
    """
    LOGGER.info(
        "Reading force constants from Phonopy: summary=%s fc=%s born=%s",
        summary_name,
        fc_name,
        born_name,
    )
    return ForceConstants.from_phonopy(
        path=".", summary_name=summary_name, fc_name=fc_name, born_name=born_name
    )


def band_path_qpoints(
    cell: tuple[np.ndarray, np.ndarray, np.ndarray],
    q_spacing: float = 0.025,
    *,
    insert_gamma: bool = True,
) -> QpointPath:
    """Return a :class:`QpointPath` (q-points + labels + cell) for a band path.

    ``cell`` is a spglib-style ``(lattice, scaled_positions, numbers)`` tuple --
    e.g. from ``euphonic.Crystal.to_spglib_cell()`` or an ASE ``Atoms``. Only the
    structure is needed; force constants are not. Pure/AiiDA-free: the parent-side
    ``generate_band_path`` calcfunction wraps this into a native ``KpointsData``.
    """
    # Work in the *original* cell so the returned q-points are valid inputs to
    # ``calculate_qpoint_phonon_modes`` (which uses the same cell's reciprocal basis).
    bandpath = seekpath.get_explicit_k_path_orig_cell(
        cell, reference_distance=q_spacing
    )

    labels = list(bandpath["explicit_kpoints_labels"])
    qpts = np.asarray(bandpath["explicit_kpoints_rel"])

    if insert_gamma:
        # Duplicate Gamma points so LO-TO splitting can be represented (matches
        # Euphonic's default behaviour).
        gamma_indices = [i for i in range(1, len(labels) - 1) if labels[i] == "GAMMA"]
        for index in reversed(gamma_indices):
            qpts = np.insert(qpts, index, [0.0, 0.0, 0.0], axis=0)
            labels.insert(index, "GAMMA")

    # ``Γ`` renders nicely as a matplotlib/KpointsData tick label.
    tick_labels = [
        (index, "\u0393" if label == "GAMMA" else label)
        for index, label in enumerate(labels)
        if label
    ]
    LOGGER.info(
        "Generated band path: %d q-points, %d high-symmetry points",
        len(qpts),
        len(tick_labels),
    )
    lattice = np.asarray(cell[0])  # real-space cell (Angstrom) for KpointsData
    return QpointPath(qpoints=qpts, labels=tick_labels, cell=lattice)


def interpolate_phonon_modes(
    force_constants: ForceConstants,
    qpoints: np.ndarray,
    *,
    asr: str | None = "reciprocal",
) -> QpointPhononModes:
    """Fourier-interpolate phonon modes at the given fractional q-points.

    ``qpoints`` is an ``(N, 3)`` array in the crystal's reciprocal basis (as
    provided by an AiiDA ``KpointsData``). This is the core
    ``ForceConstants -> QpointPhononModes`` step.
    """
    qpoints = np.asarray(qpoints)
    LOGGER.info(
        "Computing phonon modes: %d modes across %d q-points",
        force_constants.crystal.n_atoms * 3,
        len(qpoints),
    )
    # reduce_qpts=False keeps every q-point on the explicit path (matches CLI).
    return force_constants.calculate_qpoint_phonon_modes(
        qpoints, asr=asr, reduce_qpts=False
    )


def calculate_dispersion(
    force_constants: ForceConstants,
    q_spacing: float = 0.025,
    *,
    insert_gamma: bool = True,
    asr: str | None = "reciprocal",
) -> QpointPhononModes:
    """Convenience: build a band path and interpolate modes along it."""
    path = band_path_qpoints(
        force_constants.crystal.to_spglib_cell(), q_spacing, insert_gamma=insert_gamma
    )
    return interpolate_phonon_modes(force_constants, path.qpoints, asr=asr)


def default_energy_bins(
    frequencies: pint.Quantity,
    energy_spacing: pint.Quantity,
    *,
    padding_fraction: float = 0.05,
) -> pint.Quantity:
    """Compute default bin edges with asymmetric padding and fixed physical spacing.

    Parameters
    ----------
    frequencies
        Phonon frequencies as a dimensional Quantity.
    energy_spacing
        Width of each energy bin as a dimensional Quantity (e.g. ``1.0 * ureg('meV')``).
    padding_fraction
        Fractional padding based on the occupied frequency span (default: 0.05).
        Always added above the maximum frequency; added below the minimum frequency
        only if negative (imaginary modes present).

    Returns
    -------
    pint.Quantity
        Bin edges with uniform spacing in the units of ``energy_spacing``.
    """
    freqs = frequencies.to(energy_spacing.units, "spectroscopy")
    emin, emax = freqs.min(), freqs.max()

    span = max(emax - emin, energy_spacing)
    pad = padding_fraction * span

    upper = emax + pad
    lower = (emin - pad) if emin < 0 else 0

    start_idx = np.floor((lower / energy_spacing).magnitude)
    stop_idx = np.ceil((upper / energy_spacing).magnitude) + 1.0

    return np.arange(start_idx, stop_idx) * energy_spacing


def calculate_dos(
    force_constants: ForceConstants,
    q_spacing: float = 0.1,
    energy_spacing: float = 1.0,
    *,
    energy_unit: str = "meV",
    adaptive: bool = True,
    asr: str | None = "reciprocal",
) -> Spectrum1D:
    """Compute a phonon density of states by sampling a Monkhorst-Pack grid.

    Parameters
    ----------
    force_constants
        Interatomic force constants to interpolate from.
    q_spacing
        Target spacing of the sampling grid, in 1/Angstrom (finer -> denser grid).
    energy_spacing
        Width of the DOS energy bins, in ``energy_unit``.
    energy_unit
        Unit for the energy axis (e.g. ``"meV"``, ``"1/cm"``).
    adaptive
        Use adaptive broadening (per-mode widths from mode gradients) rather than
        fixed bins. Recommended; requires computing mode gradients.
    asr
        Acoustic sum rule applied during interpolation (``None`` to disable).

    Returns
    -------
    Spectrum1D
        Density of states vs energy (bin edges in ``x_data``, values in
        ``y_data``; use ``get_bin_centres()`` for matching x/y lengths).
    """
    grid = force_constants.crystal.get_mp_grid_spec(
        spacing=q_spacing * ureg("1/angstrom")
    )
    qpts = mp_grid(grid)
    LOGGER.info(
        "Sampling DOS: %dx%dx%d grid (%d q-points), adaptive=%s",
        *grid,
        len(qpts),
        adaptive,
    )
    result = force_constants.calculate_qpoint_phonon_modes(
        qpts, asr=asr, return_mode_gradients=adaptive
    )
    if adaptive:
        modes, mode_gradients = result
        mode_widths = mode_gradients_to_widths(
            mode_gradients, force_constants.crystal.cell_vectors
        )
    else:
        modes, mode_widths = result, None

    dos_bins = default_energy_bins(
        modes.frequencies, Quantity(energy_spacing, energy_unit)
    )
    return modes.calculate_dos(dos_bins, mode_widths=mode_widths)
