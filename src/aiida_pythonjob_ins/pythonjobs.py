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
initialise aiida (no profile/config needed there). By-reference pickling is the
required execution strategy: scientific dependencies like Euphonic, NumPy, and
seekpath contain compiled C-extensions that cannot be pickled by value. See
"Remote Execution, Pickling, and register_pickle_by_value" in
docs/source/design_notes.rst.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiida import orm
from aiida_pythonjob import prepare_pythonjob_inputs

from aiida_pythonjob_ins.operations import (
    band_path_qpoints,
    calculate_dispersion,
    calculate_dos,
    interpolate_phonon_modes,
    read_force_constants_from_castep,
    read_force_constants_from_phonopy,
)
from aiida_pythonjob_ins.serialization import (
    EUPHONIC_DESERIALIZERS,
    EUPHONIC_SERIALIZERS,
)

__all__ = [
    "band_path_qpoints",
    "calculate_dispersion",
    "calculate_dos",
    "interpolate_phonon_modes",
    "prepare_dispersion_inputs",
    "prepare_dos_inputs",
    "prepare_interpolation_inputs",
    "prepare_read_force_constants_inputs",
    "prepare_read_phonopy_inputs",
    "read_force_constants_from_castep",
    "read_force_constants_from_phonopy",
]


def _staged_filename(file: str | orm.SinglefileData) -> str:
    """Basename under which ``upload_files`` stages a file in the working dir."""
    return file.filename if isinstance(file, orm.SinglefileData) else Path(file).name


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
    filename = _staged_filename(castep_file)
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


def prepare_read_phonopy_inputs(
    summary: str | orm.SinglefileData,
    force_constants: str | orm.SinglefileData,
    born: str | orm.SinglefileData | None = None,
    *,
    computer: str | orm.Computer = "localhost",
    code: orm.AbstractCode | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build inputs to run :func:`read_force_constants_from_phonopy` as a PythonJob.

    The Phonopy ``summary`` (``phonopy.yaml``), ``force_constants`` (e.g.
    ``FORCE_CONSTANTS``) and optional ``born`` (``BORN``) files are staged into the
    working directory via ``upload_files``; the function reads them by basename and
    returns a ``ForceConstants`` serialized to a ``ForceConstantsData`` node.
    """
    upload_files: dict[str, str | orm.SinglefileData] = {
        "summary": summary,
        "force_constants": force_constants,
    }
    function_inputs: dict[str, Any] = {
        "summary_name": _staged_filename(summary),
        "fc_name": _staged_filename(force_constants),
    }
    if born is not None:
        upload_files["born"] = born
        function_inputs["born_name"] = _staged_filename(born)

    return prepare_pythonjob_inputs(
        function=read_force_constants_from_phonopy,
        function_inputs=function_inputs,
        upload_files=upload_files,
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


def prepare_dos_inputs(
    force_constants: orm.Data,
    q_spacing: float = 0.1,
    energy_spacing: float = 1.0,
    *,
    computer: str | orm.Computer = "localhost",
    code: orm.AbstractCode | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build inputs to run :func:`calculate_dos` as a PythonJob.

    ``q_spacing`` is the target Monkhorst-Pack grid spacing (1/Angstrom) and
    ``energy_spacing`` the DOS bin width (meV). The returned euphonic ``Spectrum1D``
    is serialized to a native ``XyData``.
    """
    return prepare_pythonjob_inputs(
        function=calculate_dos,
        function_inputs={
            "force_constants": force_constants,
            "q_spacing": q_spacing,
            "energy_spacing": energy_spacing,
        },
        serializers=EUPHONIC_SERIALIZERS,
        deserializers=EUPHONIC_DESERIALIZERS,
        computer=computer,
        code=code,
        **kwargs,
    )
