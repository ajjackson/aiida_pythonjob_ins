"""A WorkChain composing Euphonic steps into a dispersion workflow.

Steps:

1. read force constants from a CASTEP file  -> ForceConstantsData  (PythonJob)
2. extract the crystal structure            -> StructureData       (calcfunction)
3. generate a seekpath q-point path          -> KpointsData         (calcfunction)
4. interpolate phonon modes on that path    -> QpointPhononModesData (PythonJob)
5. compose a band structure                 -> BandsData           (calcfunction)

The two ``calcfunction`` steps run in-process (they need a loaded AiiDA profile to
build nodes and are cheap), while the compute-heavy read/interpolate steps run as
``PythonJob``s that could target a remote machine. Building the band path
parent-side lets it return a native ``KpointsData`` directly -- no custom carrier
type needed. ``BandsData`` plugs into AiiDA's plotting, e.g.
``results['band_structure'].show_mpl()``.

WorkChain reference:
https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/workflows/write.html
"""

from __future__ import annotations

from aiida.engine import ToContext, WorkChain, calcfunction
from aiida.orm import (
    AbstractCode,
    BandsData,
    Float,
    KpointsData,
    SinglefileData,
    StructureData,
)
from aiida_pythonjob import PythonJob

from aiida_pythonjob_ins.calculations import (
    band_path_qpoints,
    prepare_interpolation_inputs,
    prepare_read_force_constants_inputs,
)
from aiida_pythonjob_ins.conversions import (
    qpoints_to_kpoints_data,
    structure_to_spglib_cell,
)
from aiida_pythonjob_ins.data import QpointPhononModesData
from aiida_pythonjob_ins.data.base import SupportsToStructure


@calcfunction
def extract_structure(data: SupportsToStructure) -> StructureData:
    """Extract a ``StructureData`` from any node implementing ``to_structure()``.

    Generic on purpose: it works for ``ForceConstantsData``,
    ``QpointPhononModesData``, or any future node exposing ``to_structure()`` (the
    ``SupportsToStructure`` protocol). It is just a calcfunction wrapper so the
    method call becomes a provenance link between the input node and the
    ``StructureData`` on the workflow graph. AiiDA infers ``valid_type=(Data,)``
    from the protocol annotation; the ``to_structure()`` call does the rest.
    """
    return data.to_structure()


@calcfunction
def generate_band_path(structure: StructureData, q_spacing: Float) -> KpointsData:
    """Build a seekpath high-symmetry q-point path as a native ``KpointsData``.

    Depends only on the crystal *structure* (seekpath needs nothing else). A
    parent-side ``calcfunction`` (not a PythonJob): path-building is cheap and
    needs a loaded profile to construct the ``KpointsData`` node, which a remote
    PythonJob subprocess could not do.
    """
    cell = structure_to_spglib_cell(structure)
    path = band_path_qpoints(cell, q_spacing.value)
    return qpoints_to_kpoints_data(path.qpoints, path.cell, labels=path.labels)


@calcfunction
def assemble_bands(modes: QpointPhononModesData, qpoints: KpointsData) -> BandsData:
    """Compose a BandsData from phonon modes + the labelled q-point path.

    A ``calcfunction`` (so the BandsData is provenance-linked) that just delegates
    to the Data node's own converter; ``qpoints`` supplies the high-symmetry labels
    that Euphonic modes do not carry.
    """
    return modes.to_bands(qpoints)


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
            "structure",
            valid_type=StructureData,
            help="Crystal structure extracted from the force constants.",
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
        """Step 2: extract the structure, then build the q-point path.

        Both are parent-side calcfunctions (cheap, and they build AiiDA nodes).
        seekpath needs only the structure, so we materialize a ``StructureData``
        first -- reusable and idiomatic -- then derive the path from it.
        """
        if not self.ctx.read.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        # calcfunctions run synchronously and return their output node directly.
        self.ctx.structure = extract_structure(self.ctx.read.outputs.result)
        self.ctx.path = generate_band_path(self.ctx.structure, self.inputs.q_spacing)
        return None

    def interpolate(self):
        """Step 3: interpolate phonon modes on the q-point path."""
        inputs = prepare_interpolation_inputs(
            self.ctx.read.outputs.result,
            self.ctx.path,
            code=self.inputs.code,
        )
        return ToContext(modes=self.submit(PythonJob, **inputs))

    def finalize(self):
        """Expose the modes, path and a composed BandsData."""
        if not self.ctx.modes.is_finished_ok:
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED

        qpoints = self.ctx.path
        modes = self.ctx.modes.outputs.result
        self.out("phonon_modes", modes)
        self.out("structure", self.ctx.structure)
        self.out("band_path", qpoints)
        self.out("band_structure", assemble_bands(modes, qpoints))
        return None
