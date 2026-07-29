"""Atomic Euphonic operations, written as plain Python functions.

These functions use only the **public** Euphonic API and know nothing about
AiiDA, so they can be unit-tested directly and reused elsewhere. They are turned
into AiiDA processes by the helpers in :mod:`aiida_pythonjob_ins.calculations`.

``calculate_dispersion`` reproduces the logic of ``euphonic.cli.dispersion``
(https://euphonic.readthedocs.io/en/stable/cli.html#dispersion) without relying
on Euphonic's private ``_bands_from_force_constants`` helper: it builds a
high-symmetry q-point path with seekpath and interpolates phonon modes.
"""

from __future__ import annotations

from typing import Any

# Imported at module level (not under TYPE_CHECKING) because aiida-pythonjob
# resolves the function's type hints at runtime via ``typing.get_type_hints``.
from euphonic import ForceConstants, QpointPhononModes


def read_force_constants_from_castep(filename: str) -> ForceConstants:
    """Read a CASTEP ``.castep_bin``/``.check`` file into ``ForceConstants``.

    ``filename`` is resolved relative to the working directory. When run as a
    PythonJob the CASTEP file is staged there via ``upload_files`` (see
    :func:`aiida_pythonjob_ins.calculations.prepare_read_force_constants_inputs`).
    """
    return ForceConstants.from_castep(filename)


def band_structure_qpoints(
    force_constants: ForceConstants,
    q_spacing: float = 0.025,
    *,
    insert_gamma: bool = True,
) -> tuple[Any, list[tuple[int, str]]]:
    """Return q-points (and axis tick labels) for a high-symmetry band path.

    Parameters
    ----------
    force_constants
        Euphonic ``ForceConstants`` providing the crystal structure.
    q_spacing
        Target spacing between q-points along the path, in 1/Angstrom.
    insert_gamma
        Duplicate Gamma points so LO-TO splitting can be represented (matches
        Euphonic's default behaviour).

    Returns
    -------
    qpts
        Fractional q-points (N, 3) in the crystal's reciprocal basis.
    x_tick_labels
        ``(index, label)`` pairs for high-symmetry points, with Greek letters
        rendered for matplotlib.
    """
    import numpy as np
    import seekpath

    # ``to_spglib_cell`` is public; seekpath works in the *original* cell so the
    # returned q-points are valid inputs to ``calculate_qpoint_phonon_modes``.
    structure = force_constants.crystal.to_spglib_cell()
    bandpath = seekpath.get_explicit_k_path_orig_cell(
        structure, reference_distance=q_spacing
    )

    labels = list(bandpath["explicit_kpoints_labels"])
    qpts = np.asarray(bandpath["explicit_kpoints_rel"])

    if insert_gamma:
        gamma_indices = [i for i in range(1, len(labels) - 1) if labels[i] == "GAMMA"]
        for index in reversed(gamma_indices):
            qpts = np.insert(qpts, index, [0.0, 0.0, 0.0], axis=0)
            labels.insert(index, "GAMMA")

    x_tick_labels = [
        (index, r"$\Gamma$" if label == "GAMMA" else label)
        for index, label in enumerate(labels)
        if label
    ]
    return qpts, x_tick_labels


def calculate_dispersion(
    force_constants: ForceConstants,
    q_spacing: float = 0.025,
    *,
    insert_gamma: bool = True,
    asr: str | None = "reciprocal",
) -> QpointPhononModes:
    """Compute phonon modes along a high-symmetry band-structure path.

    Parameters
    ----------
    force_constants
        Interatomic force constants to interpolate from.
    q_spacing
        Target q-point spacing in 1/Angstrom.
    insert_gamma
        See :func:`band_structure_qpoints`.
    asr
        Acoustic sum rule applied during interpolation (Euphonic option); use
        ``None`` to disable.

    Returns
    -------
    QpointPhononModes
        Frequencies and eigenvectors along the band path.
    """
    qpts, _ = band_structure_qpoints(
        force_constants, q_spacing=q_spacing, insert_gamma=insert_gamma
    )
    # reduce_qpts=False keeps every q-point on the explicit path (matches CLI).
    return force_constants.calculate_qpoint_phonon_modes(
        qpts, asr=asr, reduce_qpts=False
    )
