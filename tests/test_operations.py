"""Tests for the atomic Euphonic operations and their PythonJob wrappers."""

from __future__ import annotations

import logging

import numpy as np
from aiida.engine import run_get_node
from aiida.orm import XyData
from aiida_pythonjob import PythonJob
from euphonic import ForceConstants, Spectrum1D

from aiida_pythonjob_ins.data import ForceConstantsData, QpointPhononModesData
from aiida_pythonjob_ins.operations import (
    calculate_dispersion,
    calculate_dos,
    read_force_constants_from_castep,
)
from aiida_pythonjob_ins.pythonjobs import (
    prepare_dispersion_inputs,
    prepare_dos_inputs,
    prepare_read_phonopy_inputs,
)

OPS_LOGGER = "aiida_pythonjob_ins.operations"


def test_operations_emit_logs(quartz_castep_bin, caplog):
    """The atomic operations emit informative INFO log records.

    Verifies the library's logging is wired correctly. Library code only emits
    (never configures) logging, so the test raises the level via ``caplog``.
    ``calculate_dispersion`` chains the band-path and interpolation helpers, so it
    exercises both of their log messages.
    """
    with caplog.at_level(logging.INFO, logger=OPS_LOGGER):
        force_constants = read_force_constants_from_castep(str(quartz_castep_bin))
        calculate_dispersion(force_constants, q_spacing=0.3)

    messages = [rec.getMessage() for rec in caplog.records if rec.name == OPS_LOGGER]
    assert any("Reading force constants" in msg for msg in messages)
    assert any("Generated band path" in msg for msg in messages)
    assert any("Computing phonon modes" in msg for msg in messages)


def test_calculate_dispersion_pure_function(quartz_castep_bin):
    """The plain function returns modes on a non-trivial band path."""
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    modes = calculate_dispersion(force_constants, q_spacing=0.1)

    n_branches = force_constants.crystal.n_atoms * 3
    assert modes.frequencies.shape[1] == n_branches
    assert modes.frequencies.shape[0] > 1  # multiple q-points along the path


def test_dispersion_pythonjob_matches_direct_call(python_code, quartz_castep_bin):
    """Running via PythonJob reproduces a direct public-API computation.

    This is an *equivalence* test: rather than hard-coding reference frequencies,
    we compare the AiiDA-wrapped result against calling Euphonic directly.
    """
    q_spacing = 0.1
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    expected = calculate_dispersion(force_constants, q_spacing=q_spacing)

    fc_node = ForceConstantsData(force_constants)
    inputs = prepare_dispersion_inputs(fc_node, q_spacing=q_spacing, code=python_code)
    results, node = run_get_node(PythonJob, **inputs)

    assert node.is_finished_ok, node.exit_status
    modes_node = results["result"]
    assert isinstance(modes_node, QpointPhononModesData)

    # Tolerances allow for eigensolver numerical noise: the two computations run
    # in different processes (in-process vs the PythonJob subprocess), so BLAS/
    # LAPACK threading can perturb near-degenerate acoustic modes at ~1e-2 meV.
    np.testing.assert_allclose(
        modes_node.get_modes().frequencies.magnitude,
        expected.frequencies.magnitude,
        rtol=1e-3,
        atol=0.05,  # meV
    )


def test_calculate_dos_pure_function(quartz_castep_bin):
    """The plain DOS function returns a Spectrum1D with matching x/y lengths."""
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    dos = calculate_dos(force_constants, q_spacing=0.5, energy_spacing=2.0)

    assert isinstance(dos, Spectrum1D)
    # Histogram-like: x holds bin edges, get_bin_centres() matches y.
    assert len(dos.get_bin_centres()) == len(dos.y_data)
    assert (dos.y_data.magnitude >= 0).all()


def test_dos_pythonjob_returns_xydata(python_code, quartz_castep_bin):
    """Running the DOS op via PythonJob yields a native XyData."""
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    fc_node = ForceConstantsData(force_constants)
    inputs = prepare_dos_inputs(
        fc_node, q_spacing=0.5, energy_spacing=2.0, code=python_code
    )
    results, node = run_get_node(PythonJob, **inputs)

    assert node.is_finished_ok, node.exit_status
    dos_node = results["result"]
    assert isinstance(dos_node, XyData)
    _, energy, _ = dos_node.get_x()
    ((_, dos_values, _),) = dos_node.get_y()
    assert len(energy) == len(dos_values)


def test_read_phonopy_pythonjob(python_code, phonopy_files):
    """Reading Phonopy input via PythonJob yields a ForceConstantsData."""
    inputs = prepare_read_phonopy_inputs(
        summary=phonopy_files["summary"],
        force_constants=phonopy_files["force_constants"],
        born=phonopy_files["born"],
        code=python_code,
    )
    results, node = run_get_node(PythonJob, **inputs)

    assert node.is_finished_ok, node.exit_status
    fc_node = results["result"]
    assert isinstance(fc_node, ForceConstantsData)
    assert fc_node.get_force_constants().crystal.n_atoms == 8
