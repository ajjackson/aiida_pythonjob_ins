"""Atomic Euphonic operations, written as plain Python functions.

These functions use only the **public** Euphonic API and know nothing about
AiiDA, so they can be unit-tested directly and reused elsewhere. They are turned
into AiiDA processes by the helpers in :mod:`aiida_pythonjob_ins.calculations`.

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
from typing import NamedTuple

import numpy as np
import seekpath

# Imported at module level (not under TYPE_CHECKING) because aiida-pythonjob
# resolves the function's type hints at runtime via ``typing.get_type_hints``.
from euphonic import ForceConstants, QpointPhononModes

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


def read_force_constants_from_castep(filename: str) -> ForceConstants:
    """Read a CASTEP ``.castep_bin``/``.check`` file into ``ForceConstants``.

    A thin wrapper over ``ForceConstants.from_castep``. It exists because a
    PythonJob's ``function`` must be a plain module-level function: a bound
    classmethod (``ForceConstants.from_castep``) is a ``method``, not a
    ``FunctionType``, so aiida-pythonjob's ``build_function_data`` rejects it. The
    wrapper is also where we attach logging.

    ``filename`` is resolved relative to the working directory. When run as a
    PythonJob the CASTEP file is staged there via ``upload_files`` (see
    :func:`aiida_pythonjob_ins.calculations.prepare_read_force_constants_inputs`).
    """
    LOGGER.info("Reading force constants from CASTEP file: %s", filename)
    return ForceConstants.from_castep(filename)


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
