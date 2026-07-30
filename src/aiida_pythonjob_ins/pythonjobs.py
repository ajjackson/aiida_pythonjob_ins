"""AiiDA process wrappers around the atomic Euphonic operations.

We use ``aiida-pythonjob`` to run the plain functions in
:mod:`aiida_pythonjob_ins.operations` as AiiDA ``PythonJob`` processes.
``PythonJob`` runs through a ``Code`` on a ``Computer`` (localhost in tests, but
any configured machine in production), so the standard AiiDA Computer/Code hooks
apply. See https://github.com/aiidateam/aiida-pythonjob .

Code-environment note: aiida-pythonjob cloudpickles these module-level functions
*by reference* -- a tiny module+name string per job -- so the remote unpickles via
``from aiida_pythonjob_ins.operations import ...``. That module's import chain is
deliberately AiiDA-free, so loading the function on the remote does not import or
initialise aiida (no profile/config needed there). This is the preferred
production default: the code lives once on the remote and provenance stays small.
(The package is still *installed* on the remote, which pulls aiida-core as a
dependency; to avoid that entirely, pass ``register_pickle_by_value=True`` via
``**kwargs`` below to ship the function *by value* -- then the Code needs only
cloudpickle + the science libs, at the cost of re-sending/re-storing the code on
every submission. See PLAN.md §3.5.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiida import orm
from aiida_pythonjob import prepare_pythonjob_inputs

from aiida_pythonjob_ins.operations import (
    band_path_qpoints,
    calculate_dispersion,
    interpolate_phonon_modes,
    read_force_constants_from_castep,
)
from aiida_pythonjob_ins.serialization import (
    EUPHONIC_DESERIALIZERS,
    EUPHONIC_SERIALIZERS,
)

__all__ = [
    "band_path_qpoints",
    "calculate_dispersion",
    "interpolate_phonon_modes",
    "prepare_dispersion_inputs",
    "prepare_interpolation_inputs",
    "prepare_read_force_constants_inputs",
    "read_force_constants_from_castep",
]


def prepare_interpolation_inputs(
    force_constants: orm.Data,
    qpoints: orm.KpointsData,
    *,
    computer: str | orm.Computer = "localhost",
    code: orm.AbstractCode | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build inputs to run :func:`interpolate_phonon_modes` as a PythonJob.

    ``qpoints`` is a native ``KpointsData`` q-point specification, deserialized to
    a fractional-coordinate array before interpolation. The returned modes are
    serialized to a :class:`~aiida_pythonjob_ins.data.QpointPhononModesData`.
    """
    return prepare_pythonjob_inputs(
        function=interpolate_phonon_modes,
        function_inputs={"force_constants": force_constants, "qpoints": qpoints},
        serializers=EUPHONIC_SERIALIZERS,
        deserializers=EUPHONIC_DESERIALIZERS,
        computer=computer,
        code=code,
        **kwargs,
    )


def prepare_read_force_constants_inputs(
    castep_file: str | orm.SinglefileData,
    *,
    computer: str | orm.Computer = "localhost",
    code: orm.AbstractCode | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build inputs to run :func:`read_force_constants_from_castep` as a PythonJob.

    The CASTEP file is staged into the job's working directory via ``upload_files``
    (mirroring how a real remote calculation stages its inputs); the function then
    reads it by basename and returns a ``ForceConstants`` serialized to a
    :class:`~aiida_pythonjob_ins.data.ForceConstantsData` node.
    """
    filename = (
        castep_file.filename
        if isinstance(castep_file, orm.SinglefileData)
        else Path(castep_file).name
    )
    return prepare_pythonjob_inputs(
        function=read_force_constants_from_castep,
        function_inputs={"filename": filename},
        upload_files={"castep_file": castep_file},
        serializers=EUPHONIC_SERIALIZERS,
        deserializers=EUPHONIC_DESERIALIZERS,
        computer=computer,
        code=code,
        **kwargs,
    )


def prepare_dispersion_inputs(
    force_constants: orm.Data,
    q_spacing: float = 0.025,
    *,
    computer: str | orm.Computer = "localhost",
    code: orm.AbstractCode | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build the input dict to run :func:`calculate_dispersion` as a PythonJob.

    Parameters
    ----------
    force_constants
        A :class:`~aiida_pythonjob_ins.data.ForceConstantsData` node. It is
        deserialized to a Euphonic ``ForceConstants`` before the function runs.
    q_spacing
        Target q-point spacing in 1/Angstrom.
    computer, code
        Standard AiiDA execution targets. If ``code`` is ``None``,
        aiida-pythonjob resolves/creates a Python code on ``computer``.
    kwargs
        Extra keyword arguments forwarded to ``prepare_pythonjob_inputs``.

    Returns
    -------
    dict
        Inputs to launch with ``aiida.engine.run``/``submit`` and
        ``aiida_pythonjob.PythonJob``.
    """
    return prepare_pythonjob_inputs(
        function=calculate_dispersion,
        function_inputs={"force_constants": force_constants, "q_spacing": q_spacing},
        # Teach PythonJob how to move our custom Data <-> Euphonic objects.
        serializers=EUPHONIC_SERIALIZERS,
        deserializers=EUPHONIC_DESERIALIZERS,
        computer=computer,
        code=code,
        **kwargs,
    )
