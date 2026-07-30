"""A WorkChain computing a phonon density of states from a CASTEP file.

Steps:

1. read force constants from a CASTEP file  -> ForceConstantsData  (PythonJob)
2. sample a grid and compute the DOS         -> XyData             (PythonJob)

Both compute steps are ``PythonJob``s (they could run on a remote machine); the
DOS ``Spectrum1D`` is serialized to a native ``XyData`` for easy plotting.
"""

from __future__ import annotations

from aiida.engine import ToContext, WorkChain
from aiida.orm import AbstractCode, Float, SinglefileData, XyData
from aiida_pythonjob import PythonJob

from aiida_pythonjob_ins.pythonjobs import (
    prepare_dos_inputs,
    prepare_read_force_constants_inputs,
)


class DosWorkChain(WorkChain):
    """Read force constants from a CASTEP file, then compute a phonon DOS."""

    @classmethod
    def define(cls, spec) -> None:
        super().define(spec)
        spec.input(
            "castep_file",
            valid_type=SinglefileData,
            help="CASTEP .castep_bin/.check file containing force constants.",
        )
        spec.input(
            "q_spacing",
            valid_type=Float,
            default=lambda: Float(0.1),
            help="Target Monkhorst-Pack grid spacing, in 1/Angstrom.",
        )
        spec.input(
            "energy_spacing",
            valid_type=Float,
            default=lambda: Float(1.0),
            help="DOS energy bin width, in meV.",
        )
        spec.input(
            "code",
            valid_type=AbstractCode,
            help="Python code used to run the PythonJob steps.",
        )
        spec.outline(
            cls.read_force_constants,
            cls.compute_dos,
            cls.finalize,
        )
        spec.output(
            "dos",
            valid_type=XyData,
            help="Phonon density of states (energy vs DOS).",
        )
        spec.exit_code(
            400,
            "ERROR_SUB_PROCESS_FAILED",
            message="A PythonJob step did not finish successfully.",
        )

    def read_force_constants(self):
        """Step 1: run the read-force-constants PythonJob."""
        inputs = prepare_read_force_constants_inputs(
            self.inputs.castep_file, code=self.inputs.code
        )
        return ToContext(read=self.submit(PythonJob, **inputs))

    def compute_dos(self):
        """Step 2: sample a grid and compute the DOS."""
        if not self.ctx.read.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        inputs = prepare_dos_inputs(
            self.ctx.read.outputs.result,
            q_spacing=self.inputs.q_spacing.value,
            energy_spacing=self.inputs.energy_spacing.value,
            code=self.inputs.code,
        )
        return ToContext(dos=self.submit(PythonJob, **inputs))

    def finalize(self):
        """Expose the DOS XyData."""
        if not self.ctx.dos.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED
        self.out("dos", self.ctx.dos.outputs.result)
        return None
