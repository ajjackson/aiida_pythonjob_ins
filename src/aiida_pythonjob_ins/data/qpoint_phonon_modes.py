"""AiiDA Data node wrapping a Euphonic ``QpointPhononModes`` object.

``QpointPhononModes`` is a key *output* object: phonon frequencies and
eigenvectors evaluated at a set of q-points (e.g. a band-structure path).
https://euphonic.readthedocs.io/en/stable/qpoint-phonon-modes.html
"""

from __future__ import annotations

from typing import ClassVar

from aiida.orm import BandsData, KpointsData
from euphonic import QpointPhononModes

from aiida_pythonjob_ins.conversions import (
    modes_to_bands_data,
    qpoints_to_kpoints_data,
)

from .base import EuphonicJSONData


class QpointPhononModesData(EuphonicJSONData):
    """Store a Euphonic ``QpointPhononModes`` object as an AiiDA node."""

    _euphonic_cls: ClassVar[type] = QpointPhononModes
    _filename: ClassVar[str] = "qpoint_phonon_modes.json"

    def get_modes(self) -> QpointPhononModes:
        """Return the wrapped :class:`euphonic.QpointPhononModes`."""
        return self.get_object()

    def get_kpoints(self) -> KpointsData:
        """Map the q-point positions to a native ``KpointsData``.

        Note: Euphonic modes carry no high-symmetry labels, so the returned
        ``KpointsData`` has positions only. Labels come from the ``KpointsData``
        used to *generate* the path (see the dispersion workflow).
        """
        modes = self.get_modes()
        cell = modes.crystal.cell_vectors.to("angstrom").magnitude
        return qpoints_to_kpoints_data(modes.qpts, cell)

    def get_bands(self, kpoints: KpointsData | None = None) -> BandsData:
        """Compose a native ``BandsData`` (frequencies as bands) for plotting.

        Pass the path ``KpointsData`` to carry high-symmetry labels onto the
        ``BandsData``; then ``BandsData.show_mpl()`` yields a labelled plot.
        """
        return modes_to_bands_data(self.get_modes(), kpoints=kpoints)
