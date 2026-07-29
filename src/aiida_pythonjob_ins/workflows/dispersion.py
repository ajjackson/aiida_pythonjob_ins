"""A WorkChain composing two Euphonic PythonJobs into a dispersion workflow.

This demonstrates orchestration: the output ``ForceConstantsData`` of the first
PythonJob (reading a CASTEP file) flows as input into the second (computing the
band structure), with full AiiDA provenance linking the steps.

WorkChain reference:
https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/workflows/write.html
"""

from __future__ import annotations

from aiida.engine import ToContext, WorkChain
from aiida.orm import AbstractCode, Float, SinglefileData
from aiida_pythonjob import PythonJob

from ..calculations import (
    prepare_dispersion_inputs,
    prepare_read_force_constants_inputs,
)
from ..data import QpointPhononModesData


class DispersionWorkChain(WorkChain):
    """Read force constants from a CASTEP file, then compute phonon dispersion."""

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
            default=lambda: Float(0.025),
            help="Target q-point spacing along the band path, in 1/Angstrom.",
        )
        spec.input(
            "code",
            valid_type=AbstractCode,
            help="Python code used to run the PythonJob steps.",
        )
        spec.outline(
            cls.read_force_constants,
            cls.compute_dispersion,
            cls.finalize,
        )
        spec.output(
            "phonon_modes",
            valid_type=QpointPhononModesData,
            help="Phonon frequencies/eigenvectors along the band path.",
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

    def compute_dispersion(self):
        """Step 2: feed the force constants into the dispersion PythonJob."""
        if not self.ctx.read.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        inputs = prepare_dispersion_inputs(
            self.ctx.read.outputs.result,
            q_spacing=self.inputs.q_spacing.value,
            code=self.inputs.code,
        )
        return ToContext(dispersion=self.submit(PythonJob, **inputs))

    def finalize(self):
        """Expose the phonon modes as the WorkChain output."""
        if not self.ctx.dispersion.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED
        self.out("phonon_modes", self.ctx.dispersion.outputs.result)
        return None
