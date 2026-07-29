"""A lightweight, picklable q-point path container.

This is the return type of the seekpath PythonJob
(:func:`aiida_pythonjob_ins.calculations.euphonic_ops.generate_qpoint_path`). It
holds only q-point *positions* and high-symmetry *labels* (seekpath knows nothing
about band energies), and is deliberately free of AiiDA imports so it can travel
through the PythonJob subprocess (a plain interpreter with no loaded profile).

At the AiiDA layer it is converted into a native :class:`aiida.orm.KpointsData`
by a registered serializer
(:func:`aiida_pythonjob_ins.serialization.qpoint_path_to_kpoints_data`), following
the same serializer pattern used for the Euphonic objects.
"""

from __future__ import annotations

import numpy as np


class QpointPath:
    """A high-symmetry q-point path (positions + labels, no energies).

    Deliberately a plain class, *not* a dataclass: aiida-pythonjob treats a
    dataclass return annotation as a structured multi-output spec (one output per
    field), which would bypass our ``QpointPath -> KpointsData`` serializer. A
    plain class is serialized as a single ``result`` output instead.

    Parameters
    ----------
    qpoints
        Fractional q-points, shape ``(N, 3)``, in the crystal's reciprocal basis.
    labels
        ``(index, label)`` pairs marking high-symmetry points (AiiDA's
        ``KpointsData.labels`` convention).
    cell
        Real-space lattice vectors (3x3) in Angstrom, so the resulting
        ``KpointsData`` can convert fractional q-points to distances for plotting.
    """

    def __init__(
        self,
        qpoints: np.ndarray,
        labels: list[tuple[int, str]],
        cell: np.ndarray,
    ) -> None:
        self.qpoints = qpoints
        self.labels = labels
        self.cell = cell
