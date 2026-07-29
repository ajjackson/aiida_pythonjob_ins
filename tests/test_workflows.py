"""End-to-end test for the dispersion WorkChain."""

from __future__ import annotations

from aiida.engine import run_get_node
from aiida.orm import CalcJobNode, Float, SinglefileData

from aiida_pythonjob_ins.data import QpointPhononModesData
from aiida_pythonjob_ins.workflows import DispersionWorkChain


def test_dispersion_workchain(python_code, quartz_castep_bin):
    """The WorkChain reads force constants then produces phonon modes.

    Also checks provenance: the WorkChain node is a parent of both PythonJob
    steps, i.e. the two calculations were orchestrated as a single workflow.
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
    assert isinstance(modes_node, QpointPhononModesData)

    modes = modes_node.get_modes()
    n_branches = modes.crystal.n_atoms * 3
    assert modes.frequencies.shape[1] == n_branches
    assert modes.frequencies.shape[0] > 1

    # Two PythonJob CalcJobs (read + dispersion) were orchestrated by this
    # WorkChain; their process labels are ``PythonJob<function_name>``.
    calcjobs = [
        proc for proc in node.called_descendants if isinstance(proc, CalcJobNode)
    ]
    assert len(calcjobs) == 2
