"""End-to-end tests for the WorkChains."""

from __future__ import annotations

import pytest
from aiida.engine import run_get_node
from aiida.orm import (
    BandsData,
    CalcJobNode,
    Float,
    KpointsData,
    SinglefileData,
    StructureData,
    XyData,
)
from euphonic import ForceConstants

from aiida_pythonjob_ins.data import ForceConstantsData, QpointPhononModesData
from aiida_pythonjob_ins.workflows import DispersionWorkChain, DosWorkChain


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
    structure = results["structure"]
    band_path = results["band_path"]
    band_structure = results["band_structure"]
    assert isinstance(modes_node, QpointPhononModesData)
    assert isinstance(structure, StructureData)
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


def test_dos_workchain(python_code, quartz_castep_bin):
    """Read force constants -> phonon DOS as XyData."""
    castep_file = SinglefileData(str(quartz_castep_bin))

    results, node = run_get_node(
        DosWorkChain,
        castep_file=castep_file,
        q_spacing=Float(0.5),  # coarse grid keeps the test fast
        energy_spacing=Float(2.0),
        code=python_code,
    )

    assert node.is_finished_ok, node.exit_status
    dos = results["dos"]
    assert isinstance(dos, XyData)
    _, energy, _ = dos.get_x()
    ((_, values, _),) = dos.get_y()
    assert len(energy) == len(values)
    assert (values >= 0).all()

    # read + dos, both PythonJobs
    calcjobs = [p for p in node.called_descendants if isinstance(p, CalcJobNode)]
    assert len(calcjobs) == 2


def _force_constants_from_phonopy(phonopy_dir):
    fc = ForceConstants.from_phonopy(
        path=str(phonopy_dir),
        summary_name="phonopy.yaml",
        fc_name="FORCE_CONSTANTS",
        born_name="BORN",
    )
    return ForceConstantsData(fc)


def test_dispersion_from_phonopy(python_code, phonopy_dir):
    """DispersionWorkChain accepts a ForceConstantsData (here from Phonopy)."""
    results, node = run_get_node(
        DispersionWorkChain,
        force_constants=_force_constants_from_phonopy(phonopy_dir),
        q_spacing=Float(0.3),
        code=python_code,
    )
    assert node.is_finished_ok, node.exit_status
    assert isinstance(results["band_structure"], BandsData)
    # No CASTEP read step, so only the interpolation PythonJob runs.
    calcjobs = [p for p in node.called_descendants if isinstance(p, CalcJobNode)]
    assert len(calcjobs) == 1


def test_dos_from_phonopy(python_code, phonopy_dir):
    """DosWorkChain accepts a ForceConstantsData (here from Phonopy)."""
    results, node = run_get_node(
        DosWorkChain,
        force_constants=_force_constants_from_phonopy(phonopy_dir),
        q_spacing=Float(0.5),
        energy_spacing=Float(2.0),
        code=python_code,
    )
    assert node.is_finished_ok, node.exit_status
    assert isinstance(results["dos"], XyData)


def test_workchain_requires_exactly_one_source(python_code, quartz_castep_bin):
    """Providing both castep_file and force_constants is rejected."""
    castep_file = SinglefileData(str(quartz_castep_bin))
    fc_node = ForceConstantsData(ForceConstants.from_castep(str(quartz_castep_bin)))
    with pytest.raises(ValueError, match="exactly one"):
        run_get_node(
            DispersionWorkChain,
            castep_file=castep_file,
            force_constants=fc_node,
            code=python_code,
        )
