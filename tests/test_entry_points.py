"""Tests for plugin entry-point registration.

Note: Entry-point metadata is written at install time, so a stale editable install
can make these tests pass or fail independently of edits to pyproject.toml until
reinstalled.
"""

from __future__ import annotations

import pytest
from aiida.plugins import DataFactory, WorkflowFactory

from aiida_pythonjob_ins.data import (
    EuphonicCrystalData,
    ForceConstantsData,
    QpointPhononModesData,
)
from aiida_pythonjob_ins.workflows import DispersionWorkChain, DosWorkChain


@pytest.mark.parametrize(
    ("entry_point_name", "expected_class"),
    [
        ("pythonjob_ins.crystal", EuphonicCrystalData),
        ("pythonjob_ins.force_constants", ForceConstantsData),
        ("pythonjob_ins.qpoint_phonon_modes", QpointPhononModesData),
    ],
)
def test_data_plugin_registration(aiida_profile, entry_point_name, expected_class):
    """Data entry points resolve to their expected classes via DataFactory."""
    resolved_class = DataFactory(entry_point_name)
    assert resolved_class is expected_class


@pytest.mark.parametrize(
    ("entry_point_name", "expected_class"),
    [
        ("pythonjob_ins.dispersion", DispersionWorkChain),
        ("pythonjob_ins.dos", DosWorkChain),
    ],
)
def test_workflow_plugin_registration(aiida_profile, entry_point_name, expected_class):
    """Workflow entry points resolve to their expected classes via WorkflowFactory."""
    resolved_class = WorkflowFactory(entry_point_name)
    assert resolved_class is expected_class
