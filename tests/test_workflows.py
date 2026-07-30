"""End-to-end test for the dispersion WorkChain."""

from __future__ import annotations

from aiida.engine import run_get_node
from aiida.orm import BandsData, CalcJobNode, Float, KpointsData, SinglefileData

from aiida_pythonjob_ins.data import QpointPhononModesData
from aiida_pythonjob_ins.workflows import DispersionWorkChain


def test_dispersion_workchain(python_code, quartz_castep_bin):
    """Read force constants -> q-point path -> modes -> band structure.

    Checks the native-type outputs (KpointsData path, BandsData) and that the
    three PythonJob steps were orchestrated as one provenance graph.
    """
    castep_file = SinglefileData(str(quartz_castep_bin))

    results, node = run_get_node(
        DispersionWorkChain,
        castep_file=castep_file,
        q_spacing=Float(0.2),  # coarse spacing keeps the test fast
        code=python_code,
    )

    assert node.is_finished_ok, node.exit_status

    modes_node = results["phonon_modes"]
    band_path = results["band_path"]
    band_structure = results["band_structure"]
    assert isinstance(modes_node, QpointPhononModesData)
    assert isinstance(band_path, KpointsData)
    assert isinstance(band_structure, BandsData)

    # The band path carries high-symmetry labels (e.g. Gamma).
    assert band_path.labels, "expected labelled high-symmetry points"

    # BandsData bands come from the phonon frequencies: shapes must line up with
    # the q-point path and the number of phonon branches.
    modes = modes_node.get_modes()
    n_branches = modes.crystal.n_atoms * 3
    bands = band_structure.get_bands()
    assert bands.shape == (modes.frequencies.shape[0], n_branches)
    assert band_path.get_kpoints().shape[0] == bands.shape[0]

    # Two PythonJob CalcJobs (read + interpolate) were orchestrated; the band path
    # and band-structure steps are calcfunctions, not CalcJobs.
    calcjobs = [p for p in node.called_descendants if isinstance(p, CalcJobNode)]
    assert len(calcjobs) == 2
