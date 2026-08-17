"""Tests for the atomic Euphonic operations and their PythonJob wrappers."""

from __future__ import annotations

import logging

import numpy as np
from aiida.engine import run_get_node
from aiida.orm import XyData
from aiida_pythonjob import PythonJob
from euphonic import ForceConstants, Spectrum1D, ureg

from aiida_pythonjob_ins.data import ForceConstantsData, QpointPhononModesData
from aiida_pythonjob_ins.operations import (
    calculate_dispersion,
    calculate_dos,
    default_energy_bins,
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
        force_constants = read_force_constants_from_castep(quartz_castep_bin)
        calculate_dispersion(force_constants, q_spacing=0.3)

    messages = [rec.getMessage() for rec in caplog.records if rec.name == OPS_LOGGER]
    assert any("Reading force constants" in msg for msg in messages)
    assert any("Generated band path" in msg for msg in messages)
    assert any("Computing phonon modes" in msg for msg in messages)


def test_calculate_dispersion_pure_function(quartz_castep_bin):
    """The plain function returns modes on a non-trivial band path."""
    force_constants = ForceConstants.from_castep(quartz_castep_bin)
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
    force_constants = ForceConstants.from_castep(quartz_castep_bin)
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
    force_constants = ForceConstants.from_castep(quartz_castep_bin)
    dos = calculate_dos(force_constants, q_spacing=0.5, energy_spacing=2.0)

    assert isinstance(dos, Spectrum1D)
    # Histogram-like: x holds bin edges, get_bin_centres() matches y.
    assert len(dos.get_bin_centres()) == len(dos.y_data)
    assert (dos.y_data.magnitude >= 0).all()


def test_default_energy_bins_stable():
    """Stable frequencies clamp cleanly at 0.0 with 5% upper padding."""
    freqs = np.array([0.0, 5.0, 20.0]) * ureg.meV
    bins = default_energy_bins(freqs, 1.0 * ureg.meV)

    # Span = 20.0 meV, pad = 1.0 meV. Upper = 21.0 meV, lower = 0.0 meV.
    assert bins.units == ureg.meV
    assert bins[0] == 0.0 * ureg.meV
    assert bins[-1] == 21.0 * ureg.meV
    np.testing.assert_allclose(bins.magnitude, np.arange(0.0, 22.0, 1.0))


def test_default_energy_bins_negative_modes():
    """Negative/imaginary frequencies receive 5% padding below the minimum."""
    freqs = np.array([-10.0, 5.0, 30.0]) * ureg.meV
    bins = default_energy_bins(freqs, 1.0 * ureg.meV)

    # Span = 40.0 meV, pad = 2.0 meV. Upper = 32.0 meV, lower = -12.0 meV.
    assert bins.units == ureg.meV
    assert bins[0] == -12.0 * ureg.meV
    assert bins[-1] == 32.0 * ureg.meV
    np.testing.assert_allclose(bins.magnitude, np.arange(-12.0, 33.0, 1.0))


def test_default_energy_bins_cross_unit():
    """Quantity conversions work across spectroscopy contexts (e.g. THz to meV)."""
    freqs = np.array([0.0, 2.0, 5.0]) * ureg.THz
    bins = default_energy_bins(freqs, 1.0 * ureg.meV)

    # 5.0 THz = 20.678... meV. Span = 20.678... meV, pad = 1.0339... meV.
    # Upper = 21.712... meV -> ceil is 22.0 meV. Lower = 0.0 meV.
    assert bins.units == ureg.meV
    assert bins[0] == 0.0 * ureg.meV
    assert bins[-1] == 22.0 * ureg.meV
    np.testing.assert_allclose(bins.magnitude, np.arange(0.0, 23.0, 1.0))


def test_calculate_dos_preserves_negative_frequencies(quartz_castep_bin):
    """DOS on a dataset with negative frequencies spans below zero."""
    force_constants = ForceConstants.from_castep(quartz_castep_bin)
    dos = calculate_dos(force_constants, q_spacing=0.5, energy_spacing=1.0)

    # Quartz CASTEP force constants have small negative acoustic modes at zone centre,
    # so the padded energy axis extends into negative frequencies.
    assert dos.x_data[0] < 0.0 * ureg.meV


def test_calculate_dos_sum_rule(quartz_castep_bin):
    """Integrating DOS across the padded axis recovers 3 modes per formula unit."""
    force_constants = ForceConstants.from_castep(quartz_castep_bin)
    energy_spacing = 0.5

    # 1. Fixed binning (adaptive=False): all modes binned, integral is exact
    dos_fixed = calculate_dos(
        force_constants,
        q_spacing=0.2,
        energy_spacing=energy_spacing,
        adaptive=False,
    )
    integral_fixed = np.sum(dos_fixed.y_data.to("1/meV").magnitude * energy_spacing)
    np.testing.assert_allclose(integral_fixed, 3.0, rtol=1e-10)

    # 2. Adaptive broadening (adaptive=True): continuous Gaussian wings near edges
    dos_adaptive = calculate_dos(
        force_constants,
        q_spacing=0.2,
        energy_spacing=energy_spacing,
        adaptive=True,
    )
    integral_adaptive = np.sum(
        dos_adaptive.y_data.to("1/meV").magnitude * energy_spacing
    )
    np.testing.assert_allclose(integral_adaptive, 3.0, rtol=0.01)


def test_dos_pythonjob_returns_xydata(python_code, quartz_castep_bin):
    """Running the DOS op via PythonJob yields a native XyData."""
    force_constants = ForceConstants.from_castep(quartz_castep_bin)
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
