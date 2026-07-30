"""Bridges between Euphonic objects and our AiiDA Data nodes for aiida-pythonjob.

``aiida-pythonjob`` converts a plain Python function into an AiiDA process. To do
so it must (de)serialize the function's inputs/outputs to/from AiiDA nodes:

* **serializers** map a *Python type* (``module.ClassName``) to a callable that
  returns an ``aiida.orm.Data`` node. Our Data classes already accept the Euphonic
  object in their constructor (``ForceConstantsData(fc, user=...)``), so the class
  itself is a valid serializer.
* **deserializers** map an *AiiDA node type* back to the Python object the function
  expects.

We pass these dicts explicitly via ``prepare_pythonjob_inputs(serializers=...,
deserializers=...)`` rather than registering extra entry points, keeping the
``aiida.data`` entry points clean (one per Data class).
See https://aiida-pythonjob.readthedocs.io/ (data serialization).
"""

from __future__ import annotations

from typing import Any

from aiida.orm import KpointsData, Node

from .conversions import qpoints_to_kpoints_data
from .data import ForceConstantsData, QpointPhononModesData

# Python type (module.ClassName) -> dotted path of a callable returning a Data node.
EUPHONIC_SERIALIZERS: dict[str, str] = {
    "euphonic.force_constants.ForceConstants": (
        "aiida_pythonjob_ins.data.force_constants.ForceConstantsData"
    ),
    "euphonic.qpoint_phonon_modes.QpointPhononModes": (
        "aiida_pythonjob_ins.data.qpoint_phonon_modes.QpointPhononModesData"
    ),
    # The seekpath PythonJob returns a QpointPath, serialized to native KpointsData.
    "aiida_pythonjob_ins.qpoint_path.QpointPath": (
        "aiida_pythonjob_ins.serialization.qpoint_path_to_kpoints_data"
    ),
}

# AiiDA node type (module.ClassName) -> dotted path of a callable returning the object.
EUPHONIC_DESERIALIZERS: dict[str, str] = {
    "aiida_pythonjob_ins.data.force_constants.ForceConstantsData": (
        "aiida_pythonjob_ins.serialization.force_constants_from_node"
    ),
    "aiida_pythonjob_ins.data.qpoint_phonon_modes.QpointPhononModesData": (
        "aiida_pythonjob_ins.serialization.qpoint_phonon_modes_from_node"
    ),
    # A KpointsData input to the interpolation op deserializes to a q-points array.
    "aiida.orm.nodes.data.array.kpoints.KpointsData": (
        "aiida_pythonjob_ins.conversions.kpoints_data_to_qpoints"
    ),
}


def qpoint_path_to_kpoints_data(
    qpoint_path: Any,
    user: Any = None,  # noqa: ARG001 (required by aiida-pythonjob serializer signature)
) -> KpointsData:
    """Serializer: QpointPath -> aiida.orm.KpointsData (positions + labels + cell)."""
    return qpoints_to_kpoints_data(
        qpoint_path.qpoints, qpoint_path.cell, labels=qpoint_path.labels
    )


def force_constants_from_node(node: ForceConstantsData) -> Any:
    """Deserializer: ForceConstantsData node -> euphonic.ForceConstants."""
    return node.get_force_constants()


def qpoint_phonon_modes_from_node(node: QpointPhononModesData) -> Any:
    """Deserializer: QpointPhononModesData node -> euphonic.QpointPhononModes."""
    return node.get_modes()


def _assert_node(value: Node) -> None:
    """Guard used in tests to confirm serialization produced a Data node."""
    if not isinstance(value, Node):
        msg = f"Expected an AiiDA Node, got {type(value).__name__}."
        raise TypeError(msg)
