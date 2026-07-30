"""Atomic Euphonic operations, written as plain Python functions.

These functions use only the **public** Euphonic API and know nothing about
AiiDA, so they can be unit-tested directly and reused elsewhere. They are turned
into AiiDA processes by the helpers in :mod:`aiida_pythonjob_ins.calculations`.

The dispersion workflow is split into two composable steps, mirroring
``euphonic.cli.dispersion`` (https://euphonic.readthedocs.io/en/stable/cli.html)
without relying on Euphonic's private ``_bands_from_force_constants`` helper:

1. :func:`generate_qpoint_path` -- build a high-symmetry q-point path (seekpath).
2. :func:`interpolate_phonon_modes` -- Fourier-interpolate modes at those points.

``calculate_dispersion`` is a convenience that chains the two.
"""

from __future__ import annotations

import numpy as np
import seekpath

# Imported at module level (not under TYPE_CHECKING) because aiida-pythonjob
# resolves the function's type hints at runtime via ``typing.get_type_hints``.
from euphonic import ForceConstants, QpointPhononModes

from aiida_pythonjob_ins.qpoint_path import QpointPath


def read_force_constants_from_castep(filename: str) -> ForceConstants:
    """Read a CASTEP ``.castep_bin``/``.check`` file into ``ForceConstants``.

    ``filename`` is resolved relative to the working directory. When run as a
    PythonJob the CASTEP file is staged there via ``upload_files`` (see
    :func:`aiida_pythonjob_ins.calculations.prepare_read_force_constants_inputs`).
    """
    return ForceConstants.from_castep(filename)


def _seekpath_qpoints(
    force_constants: ForceConstants,
    q_spacing: float,
    insert_gamma: bool,
) -> tuple[np.ndarray, list[tuple[int, str]]]:
    """Return explicit q-points and ``(index, label)`` pairs for a band path."""
    # ``to_spglib_cell`` is public; seekpath works in the *original* cell so the
    # returned q-points are valid inputs to ``calculate_qpoint_phonon_modes``.
    structure = force_constants.crystal.to_spglib_cell()
    bandpath = seekpath.get_explicit_k_path_orig_cell(
        structure, reference_distance=q_spacing
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
    return qpts, tick_labels


def generate_qpoint_path(
    force_constants: ForceConstants,
    q_spacing: float = 0.025,
    *,
    insert_gamma: bool = True,
) -> QpointPath:
    """Build a high-symmetry q-point path from the crystal structure.

    Returns a :class:`~aiida_pythonjob_ins.qpoint_path.QpointPath` (positions +
    labels + cell); at the AiiDA layer this becomes a native ``KpointsData``.
    """
    qpts, labels = _seekpath_qpoints(force_constants, q_spacing, insert_gamma)
    cell = force_constants.crystal.cell_vectors.to("angstrom").magnitude
    return QpointPath(qpoints=qpts, labels=labels, cell=cell)


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
    # reduce_qpts=False keeps every q-point on the explicit path (matches CLI).
    return force_constants.calculate_qpoint_phonon_modes(
        np.asarray(qpoints), asr=asr, reduce_qpts=False
    )


def calculate_dispersion(
    force_constants: ForceConstants,
    q_spacing: float = 0.025,
    *,
    insert_gamma: bool = True,
    asr: str | None = "reciprocal",
) -> QpointPhononModes:
    """Convenience: build a band path and interpolate modes along it."""
    qpts, _ = _seekpath_qpoints(force_constants, q_spacing, insert_gamma)
    return interpolate_phonon_modes(force_constants, qpts, asr=asr)
