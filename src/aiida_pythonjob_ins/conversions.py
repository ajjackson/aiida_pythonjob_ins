"""Mappings between Euphonic objects and AiiDA's native materials-science types.

AiiDA ships domain data types for reciprocal-space data
(https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/data_types.html#materials-science-data-types):

* ``KpointsData`` -- k-/q-point positions (+ optional labels + cell). We use it as
  the q-point *specification* for Fourier interpolation, and as the natural
  representation of a phonon band path.
* ``BandsData`` (a ``KpointsData`` subclass) -- band energies on those points. A
  Euphonic ``QpointPhononModes`` is essentially ``BandsData`` (frequencies) plus
  eigenvectors, so we build a ``BandsData`` by *composition* and keep the
  eigenvectors in our own ``QpointPhononModesData``.

Using ``BandsData`` also unlocks existing AiiDA plotting, e.g.
``bands.show_mpl()`` pops up a matplotlib band-structure plot without any
AiiDALab dependency.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from aiida.orm import BandsData, KpointsData, StructureData


def structure_to_spglib_cell(
    structure: StructureData,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a ``StructureData`` to a spglib/seekpath ``(lattice, positions,
    numbers)`` tuple, using only AiiDA's native API (no ASE).

    ``numbers`` are per-kind integer labels (distinct species markers) -- all
    seekpath needs to detect symmetry; they need not be atomic numbers.
    """
    cell = np.array(structure.cell)
    inverse_cell = np.linalg.inv(cell)
    kind_number = {kind.name: index + 1 for index, kind in enumerate(structure.kinds)}
    positions = np.array(
        [np.array(site.position) @ inverse_cell for site in structure.sites]
    )
    numbers = np.array([kind_number[site.kind_name] for site in structure.sites])
    return cell, positions, numbers


def qpoints_to_kpoints_data(
    qpoints: np.ndarray,
    cell: np.ndarray,
    labels: list[tuple[int, str]] | None = None,
) -> KpointsData:
    """Build a ``KpointsData`` from fractional q-points, a cell and labels."""
    kpoints = KpointsData()
    kpoints.set_cell(np.asarray(cell))
    kpoints.set_kpoints(np.asarray(qpoints), cartesian=False, labels=labels)
    return kpoints


def kpoints_data_to_qpoints(kpoints: KpointsData) -> np.ndarray:
    """Extract fractional q-points from a ``KpointsData`` node."""
    return kpoints.get_kpoints()


def modes_to_bands_data(
    modes: Any,
    kpoints: KpointsData | None = None,
) -> BandsData:
    """Compose a ``BandsData`` from Euphonic ``QpointPhononModes``.

    ``BandsData`` is a *join*: q-points + cell + high-symmetry labels (from the
    path) plus frequencies (from ``modes``); neither Euphonic class holds all of
    it (``QpointPhononModes`` has no labels; ``Spectrum1DCollection`` has no
    3-D q-points/eigenvectors).

    Parameters
    ----------
    modes
        A Euphonic ``QpointPhononModes`` object (supplies q-points + frequencies).
    kpoints
        Optional ``KpointsData`` providing the exact q-point positions *and*
        high-symmetry labels (e.g. the path used to compute ``modes``). If given,
        its q-points and cell are **validated** against ``modes`` (a mismatch
        means path and modes are inconsistent). If omitted, positions come from
        ``modes`` and labels fall back to Euphonic's automatic tick labels
        (``QpointPhononModes.get_dispersion().x_tick_labels``).
    """
    cell = modes.crystal.cell_vectors.to("angstrom").magnitude

    if kpoints is not None:
        _validate_kpoints_match_modes(kpoints, modes, cell)
        positions = kpoints.get_kpoints()
        labels = kpoints.labels
    else:
        positions = modes.qpts
        # Euphonic derives tick labels heuristically from the q-point coordinates.
        labels = modes.get_dispersion().x_tick_labels

    bands = BandsData()
    bands.set_cell(cell)
    bands.set_kpoints(positions, cartesian=False, labels=labels)
    # Phonon frequencies play the role of "band energies"; keep them in meV.
    bands.set_bands(modes.frequencies.to("meV").magnitude, units="meV")
    return bands


def _validate_kpoints_match_modes(
    kpoints: KpointsData, modes: Any, cell: np.ndarray
) -> None:
    """Raise if a ``KpointsData`` path is inconsistent with the phonon modes."""
    if not np.allclose(kpoints.get_kpoints(), modes.qpts):
        msg = (
            "KpointsData q-points do not match the phonon modes' q-points; "
            "the band path and the computed modes are inconsistent."
        )
        raise ValueError(msg)
    if not np.allclose(np.asarray(kpoints.cell), cell):
        msg = (
            "KpointsData cell does not match the phonon modes' crystal cell; "
            "q-point fractional coordinates would refer to a different lattice."
        )
        raise ValueError(msg)
