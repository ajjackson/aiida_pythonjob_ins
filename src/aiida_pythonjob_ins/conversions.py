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
from aiida.orm import BandsData, KpointsData


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

    Parameters
    ----------
    modes
        A Euphonic ``QpointPhononModes`` object.
    kpoints
        Optional ``KpointsData`` providing the exact q-point positions *and*
        high-symmetry labels (e.g. the path used to compute ``modes``). If given,
        its labels are carried onto the ``BandsData`` for nicely-ticked plots. If
        omitted, positions are taken from ``modes`` and no labels are set.
    """
    bands = BandsData()
    cell = modes.crystal.cell_vectors.to("angstrom").magnitude
    bands.set_cell(cell)

    if kpoints is not None:
        bands.set_kpoints(kpoints.get_kpoints(), cartesian=False, labels=kpoints.labels)
    else:
        bands.set_kpoints(modes.qpts, cartesian=False)

    # Phonon frequencies play the role of "band energies"; keep them in meV.
    frequencies = modes.frequencies.to("meV").magnitude
    bands.set_bands(frequencies, units="meV")
    return bands
