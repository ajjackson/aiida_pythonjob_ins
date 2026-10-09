"""Standalone WorkChain that resolves force constants from a source.

``ForceConstantsWorkChain`` is a launchable source-resolution unit: exactly one
of a CASTEP ``castep_file`` (``SinglefileData``) or a prepared ``node``
(``ForceConstantsData``) goes in, and a ``force_constants`` output comes out. It
dispatches no jobs and takes no ``Code`` or execution options -- remote or
job-based sources are produced upstream by the caller and passed as ``node``.

Consuming workflows (dispersion, DOS, TOSCA-from-force-constants) run it as a
sub-workflow, exposing its inputs under a ``force_constants`` namespace (see
:mod:`aiida_pythonjob_ins.workflows.base`). Keeping source resolution here means
the steps that turn an input into a ``ForceConstantsData`` can grow (new
formats, multi-step imports) without touching every consumer's outline, and
the unit can also be launched alone.

WorkChain reference:
https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/workflows/write.html
"""

from __future__ import annotations

import struct

from aiida.engine import ExitCode, WorkChain, calcfunction, if_
from aiida.orm import SinglefileData

from aiida_pythonjob_ins.data import ForceConstantsData


@calcfunction
def read_castep_force_constants(
    castep_file: SinglefileData,
) -> ForceConstantsData | ExitCode:
    """Read a CASTEP ``SinglefileData`` into a :class:`ForceConstantsData` in-process.

    A calcfunction (not a dispatched PythonJob): the read takes about 0.1 s, so the
    ~2.8 s of job machinery it used to incur is unjustified. It records a
    ``CalcFunctionNode`` linking the file to the ``ForceConstantsData`` it
    produces, and it can be cached.

    An unreadable or invalid file returns an ``ExitCode(300, ...)`` rather than
    raising. All foreseeable Euphonic reader failures on truncated, corrupt, or
    non-phonon CASTEP inputs are caught per AiiDA's guidance to return an
    ``ExitCode`` for classifiable failures. ``RuntimeError`` is matched by
    message so that genuine internal bugs continue to propagate as Excepted
    processes.
    """
    try:
        with castep_file.as_path() as path:
            return ForceConstantsData.from_castep(path)
    except (EOFError, struct.error, OSError, ValueError) as exc:
        return ExitCode(300, f"Could not read CASTEP force constants: {exc}")
    except RuntimeError as exc:
        msg = str(exc)
        if "Force constants matrix could not be found" in msg or "Invalid file" in msg:
            return ExitCode(300, f"Could not read CASTEP force constants: {exc}")
        raise


class ForceConstantsWorkChain(WorkChain):
    """Resolve a ``ForceConstantsData`` from a CASTEP file or a prepared node.

    Exactly one source is accepted: a ``castep_file`` (read in-process by the
    :func:`read_castep_force_constants` calcfunction, which records a
    ``CalcFunctionNode`` linking the file to the output) or a ``node`` (passed
    through directly, with no calculation). The resolved force constants are
    exposed as the ``force_constants`` output.

    It takes no ``Code`` or execution options: a ``node`` from a job-based source
    is produced upstream by the caller.

    Exit Codes:
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
            "node",
            valid_type=ForceConstantsData,
            required=False,
            help="Pre-built force constants (e.g. from Phonopy); passed through.",
        )
        spec.inputs.validator = cls._validate_source
        spec.outline(
            if_(cls.has_castep_file)(cls.read_castep_file).else_(cls.use_node),
            cls.finalize,
        )
        spec.output(
            "force_constants",
            valid_type=ForceConstantsData,
            help="The resolved force constants (read from a file or passed through).",
        )
        spec.exit_code(
            410,
            "ERROR_READ_FAILED",
            message="The force constants could not be read.",
        )

    @staticmethod
    def _validate_source(inputs, _port) -> str | None:
        """Require exactly one of ``castep_file`` / ``node``."""
        has_file = "castep_file" in inputs
        has_node = "node" in inputs
        if has_file == has_node:
            return "Provide exactly one of `castep_file` or `node`."
        return None

    def has_castep_file(self) -> bool:
        """Return whether a CASTEP file was supplied as the source."""
        return "castep_file" in self.inputs

    def read_castep_file(self) -> ExitCode | None:
        """Read the supplied CASTEP file in-process and store the result.

        A failed read terminates the workflow with ``ERROR_READ_FAILED`` (410)
        before the ``finalize`` step, so no output is emitted.
        """
        result, node = read_castep_force_constants.run_get_node(self.inputs.castep_file)
        if not node.is_finished_ok:
            self.report(node.exit_message)
            return self.exit_codes.ERROR_READ_FAILED
        self.ctx.force_constants = result
        return None

    def use_node(self):
        """Pass the supplied force-constants node through directly."""
        self.ctx.force_constants = self.inputs.node

    def finalize(self) -> None:
        """Expose the resolved force constants as the workflow output."""
        self.out("force_constants", self.ctx.force_constants)
