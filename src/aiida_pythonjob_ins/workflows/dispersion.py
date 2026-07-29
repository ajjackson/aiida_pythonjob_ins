"""A WorkChain composing Euphonic PythonJobs into a dispersion workflow.

Steps (each a separate PythonJob, so provenance links them all):

1. read force constants from a CASTEP file  -> ForceConstantsData
2. generate a seekpath q-point path         -> KpointsData (positions + labels)
3. interpolate phonon modes on that path    -> QpointPhononModesData

Finally, a ``calcfunction`` composes a native ``BandsData`` from the modes and
the path ``KpointsData`` (carrying its high-symmetry labels). ``BandsData``
plugs into AiiDA's plotting, e.g. ``results['band_structure'].show_mpl()``.

WorkChain reference:
https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/workflows/write.html
"""

from __future__ import annotations

from aiida.engine import ToContext, WorkChain, calcfunction
from aiida.orm import AbstractCode, BandsData, Float, KpointsData, SinglefileData
from aiida_pythonjob import PythonJob

from ..calculations import (
    prepare_interpolation_inputs,
    prepare_qpoint_path_inputs,
    prepare_read_force_constants_inputs,
)
from ..conversions import modes_to_bands_data
from ..data import QpointPhononModesData


@calcfunction
def assemble_bands(modes: QpointPhononModesData, qpoints: KpointsData) -> BandsData:
    """Compose a BandsData from phonon modes + the labelled q-point path.

    A ``calcfunction`` so the BandsData is provenance-linked to its inputs.
    """
    return modes_to_bands_data(modes.get_modes(), kpoints=qpoints)


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
            cls.generate_path,
            cls.interpolate,
            cls.finalize,
        )
        spec.output(
            "phonon_modes",
            valid_type=QpointPhononModesData,
            help="Frequencies + eigenvectors along the band path.",
        )
        spec.output(
            "band_path",
            valid_type=KpointsData,
            help="The high-symmetry q-point path (positions + labels).",
        )
        spec.output(
            "band_structure",
            valid_type=BandsData,
            help="Phonon band structure (frequencies as bands) for plotting.",
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

    def generate_path(self):
        """Step 2: build the seekpath q-point path as a KpointsData."""
        if not self.ctx.read.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        inputs = prepare_qpoint_path_inputs(
            self.ctx.read.outputs.result,
            q_spacing=self.inputs.q_spacing.value,
            code=self.inputs.code,
        )
        return ToContext(path=self.submit(PythonJob, **inputs))

    def interpolate(self):
        """Step 3: interpolate phonon modes on the q-point path."""
        if not self.ctx.path.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        inputs = prepare_interpolation_inputs(
            self.ctx.read.outputs.result,
            self.ctx.path.outputs.result,
            code=self.inputs.code,
        )
        return ToContext(modes=self.submit(PythonJob, **inputs))

    def finalize(self):
        """Expose the modes, path and a composed BandsData."""
        if not self.ctx.modes.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        qpoints = self.ctx.path.outputs.result
        modes = self.ctx.modes.outputs.result
        self.out("phonon_modes", modes)
        self.out("band_path", qpoints)
        self.out("band_structure", assemble_bands(modes, qpoints))
        return None
