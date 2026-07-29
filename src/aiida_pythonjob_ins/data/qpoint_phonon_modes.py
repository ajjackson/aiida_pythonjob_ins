"""AiiDA Data node wrapping a Euphonic ``QpointPhononModes`` object.

``QpointPhononModes`` is a key *output* object: phonon frequencies and
eigenvectors evaluated at a set of q-points (e.g. a band-structure path).
https://euphonic.readthedocs.io/en/stable/qpoint-phonon-modes.html
"""

from __future__ import annotations

from typing import ClassVar

from euphonic import QpointPhononModes

from .base import EuphonicJSONData


class QpointPhononModesData(EuphonicJSONData):
    """Store a Euphonic ``QpointPhononModes`` object as an AiiDA node."""

    _euphonic_cls: ClassVar[type] = QpointPhononModes
    _filename: ClassVar[str] = "qpoint_phonon_modes.json"

    def get_modes(self) -> QpointPhononModes:
        """Return the wrapped :class:`euphonic.QpointPhononModes`."""
        return self.get_object()
