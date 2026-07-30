"""Tests for mapping Euphonic results onto native AiiDA KpointsData/BandsData."""

from __future__ import annotations

import matplotlib as mpl
import numpy as np
from aiida.engine import run_get_node
from aiida.orm import BandsData, Float, KpointsData
from aiida_pythonjob import PythonJob
from euphonic import ForceConstants

from aiida_pythonjob_ins.calculations import (
    calculate_dispersion,
    interpolate_phonon_modes,
    prepare_interpolation_inputs,
)
from aiida_pythonjob_ins.conversions import (
    kpoints_data_to_qpoints,
    qpoints_to_kpoints_data,
)
from aiida_pythonjob_ins.data import ForceConstantsData, QpointPhononModesData
from aiida_pythonjob_ins.workflows.dispersion import generate_band_path


def test_kpoints_roundtrip(aiida_profile):
    """qpoints -> KpointsData -> qpoints preserves positions and labels."""
    qpts = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [0.5, 0.5, 0.0]])
    cell = np.eye(3) * 4.0
    labels = [(0, "\u0393"), (2, "M")]

    kpoints = qpoints_to_kpoints_data(qpts, cell, labels=labels)
    np.testing.assert_allclose(kpoints_data_to_qpoints(kpoints), qpts)
    assert kpoints.labels == labels


def test_modes_data_to_native_types(aiida_profile, quartz_castep_bin):
    """QpointPhononModesData exposes KpointsData and BandsData views."""
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    qpts = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]])
    modes = force_constants.calculate_qpoint_phonon_modes(qpts)
    node = QpointPhononModesData(modes)

    kpoints = node.get_kpoints()
    assert isinstance(kpoints, KpointsData)
    np.testing.assert_allclose(kpoints.get_kpoints(), qpts)

    bands = node.get_bands()
    assert isinstance(bands, BandsData)
    n_branches = force_constants.crystal.n_atoms * 3
    assert bands.get_bands().shape == (len(qpts), n_branches)


def test_bandsdata_matplotlib_export(aiida_profile, quartz_castep_bin, tmp_path):
    """BandsData renders a band-structure image via matplotlib (no AiiDALab)."""
    mpl.use("Agg")  # headless

    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    modes = calculate_dispersion(force_constants, q_spacing=0.3)
    bands = QpointPhononModesData(modes).get_bands()
    bands.store()

    out = tmp_path / "bands.png"
    bands.export(str(out), fileformat="mpl_png")
    assert out.exists()
    assert out.stat().st_size > 0


def test_interpolation_from_kpoints_matches_direct(python_code, quartz_castep_bin):
    """The KpointsData-driven interpolation PythonJob matches a direct call.

    Demonstrates KpointsData as the q-point specification input for the
    ForceConstants -> QpointPhononModes step.
    """
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    fc_node = ForceConstantsData(force_constants).store()

    # Build the path as a KpointsData via the parent-side calcfunction.
    kpoints = generate_band_path(fc_node, Float(0.2))
    assert isinstance(kpoints, KpointsData)

    expected = interpolate_phonon_modes(force_constants, kpoints.get_kpoints())

    results, node = run_get_node(
        PythonJob,
        **prepare_interpolation_inputs(fc_node, kpoints, code=python_code),
    )
    assert node.is_finished_ok, node.exit_status
    modes_node = results["result"]
    assert isinstance(modes_node, QpointPhononModesData)

    # Tolerances absorb eigensolver noise on near-degenerate acoustic modes.
    np.testing.assert_allclose(
        modes_node.get_modes().frequencies.magnitude,
        expected.frequencies.magnitude,
        rtol=1e-3,
        atol=0.05,  # meV
    )
