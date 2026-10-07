"""Shared base WorkChain that obtains force constants for a phonon calculation.

The concrete workflows (dispersion, DOS, TOSCA) all need a ``ForceConstantsData`` to
work from. This base lets that come from *either*:

* a CASTEP ``castep_file`` (``SinglefileData``) -- read in-process by the
  :func:`read_castep_force_constants` calcfunction (provenance-recorded, but not
  dispatched; the file-staging PythonJob pattern is still demonstrated by
  :func:`aiida_pythonjob_ins.pythonjobs.prepare_read_force_constants_inputs`,
  exercised by ``tests/test_remote_ssh.py``), or
* a pre-built ``force_constants`` (``ForceConstantsData``) node -- e.g. produced
  from Phonopy input (see
  :func:`aiida_pythonjob_ins.pythonjobs.prepare_read_phonopy_inputs`) or any other
  source.

Subclasses add their own inputs/outputs and an outline that begins with::

    cls.resolve_force_constants,
    ...  # their compute steps, using ``self.ctx.force_constants``

Reading Phonopy inside the workflow is intentionally *not* built in here: Phonopy
needs several files, so it is cleaner to read it up front into a
``ForceConstantsData`` and pass that as ``force_constants``.
"""

from __future__ import annotations

from typing import Any

from aiida.engine import ExitCode, WorkChain, calcfunction
from aiida.orm import AbstractCode, Dict, SinglefileData, to_aiida_type

from aiida_pythonjob_ins.data import ForceConstantsData


@calcfunction
def read_castep_force_constants(castep_file: SinglefileData) -> ForceConstantsData:
    """Read a CASTEP ``SinglefileData`` into a :class:`ForceConstantsData` in-process.

    A calcfunction (not a dispatched PythonJob): the read takes about 0.1 s, so the
    ~2.8 s of job machinery it used to incur is unjustified. It records a
    ``CalcFunctionNode`` linking the file to the ``ForceConstantsData`` it
    produces, and it can be cached.

    An unreadable file returns an ``ExitCode`` rather than raising. Spike task 1.1
    determined that Euphonic's reader raises ``EOFError`` on junk bytes, a
    truncated ``.castep_bin`` and an empty file -- all three yield ``Issue reading
    binary file ... Unexpected EOF reached``. Only that foreseeable, classifiable
    failure is caught (per AiiDA's guidance to return an ``ExitCode`` for such
    cases); any other exception propagates as an Excepted process.
    """
    try:
        with castep_file.as_path() as path:
            return ForceConstantsData.from_castep(path)
    except EOFError as exc:
        return ExitCode(300, f"Could not read CASTEP force constants: {exc}")


class ForceConstantsWorkChain(WorkChain):
    """Resolve ``self.ctx.force_constants`` from a CASTEP file or a given node.

    Exit Codes:
        * 400 (ERROR_SUB_PROCESS_FAILED): A PythonJob step did not finish successfully.
        * 410 (ERROR_READ_FAILED): The force constants could not be read.
    """

    @classmethod
    def define(cls, spec) -> None:
        super().define(spec)
        spec.input(
            "castep_file",
            valid_type=SinglefileData,
            required=False,
            help=(
                "CASTEP .castep_bin/.check file, read in-process by the "
                "``read_castep_force_constants`` calcfunction."
            ),
        )
        spec.input(
            "force_constants",
            valid_type=ForceConstantsData,
            required=False,
            help="Pre-built force constants (e.g. from Phonopy); skips the read step.",
        )
        spec.input(
            "code",
            valid_type=AbstractCode,
            help="Python code used to run the PythonJob steps.",
        )
        spec.input(
            "options",
            valid_type=Dict,
            required=False,
            serializer=to_aiida_type,
            help="Optional scheduler and execution options passed to child PythonJobs.",
        )
        spec.inputs.validator = cls._validate_source
        spec.exit_code(
            400,
            "ERROR_SUB_PROCESS_FAILED",
            message="A PythonJob step did not finish successfully.",
        )
        spec.exit_code(
            410,
            "ERROR_READ_FAILED",
            message="The force constants could not be read.",
        )

    @staticmethod
    def _validate_source(inputs, _port) -> str | None:
        """Require exactly one of ``castep_file`` / ``force_constants``."""
        has_file = "castep_file" in inputs
        has_fc = "force_constants" in inputs
        if has_file == has_fc:
            return "Provide exactly one of `castep_file` or `force_constants`."
        return None

    def get_job_metadata(self) -> dict[str, Any]:
        """Return metadata dictionary for child PythonJobs."""
        if "options" in self.inputs:
            return {"options": self.inputs.options.get_dict()}
        return {}

    def resolve_force_constants(self):
        """Set ``self.ctx.force_constants`` from the supplied node or the read step.

        A single outline step replacing the former
        ``if_(cls.should_read_castep)(cls.read_force_constants),
        cls.assign_force_constants`` pair. Calcfunctions run synchronously, so the
        split that existed only to wait on a submitted job is no longer needed.

        If a ``force_constants`` node was supplied, it is used directly. Otherwise
        the in-process :func:`read_castep_force_constants` calcfunction reads the
        ``castep_file``; a failed read terminates the workflow with
        ``ERROR_READ_FAILED`` (410) rather than proceeding with missing data.
        """
        if "force_constants" in self.inputs:
            self.ctx.force_constants = self.inputs.force_constants
            return None

        result, node = read_castep_force_constants.run_get_node(self.inputs.castep_file)
        if node.is_finished_ok:
            self.ctx.force_constants = result
            return None
        self.report(node.exit_message)
        return self.exit_codes.ERROR_READ_FAILED
