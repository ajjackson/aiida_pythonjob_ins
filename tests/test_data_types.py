"""Round-trip tests for the custom Euphonic Data nodes.

These verify that storing a Euphonic object in an AiiDA node and reading it back
(after a store/reload cycle) reproduces the original object.
"""

from __future__ import annotations

import numpy as np
from euphonic import ForceConstants

from aiida_pythonjob_ins.data import ForceConstantsData, QpointPhononModesData


def test_force_constants_roundtrip(aiida_profile, quartz_castep_bin):
    """A stored+reloaded ForceConstantsData yields equivalent force constants."""
    original = ForceConstants.from_castep(str(quartz_castep_bin))

    node = ForceConstantsData(original)
    node.store()  # persist to the temporary profile
    reloaded = node.get_force_constants()

    assert reloaded.crystal.n_atoms == original.crystal.n_atoms
    np.testing.assert_allclose(
        reloaded.force_constants.magnitude,
        original.force_constants.magnitude,
    )


def test_force_constants_from_castep_classmethod(aiida_profile, quartz_castep_bin):
    """The ``from_castep`` constructor produces a usable node."""
    node = ForceConstantsData.from_castep(quartz_castep_bin)
    assert node.get_force_constants().crystal.n_atoms == 9  # quartz: 3 Si + 6 O


def test_force_constants_type_validation(aiida_profile):
    """Passing a non-ForceConstants object raises TypeError."""
    import pytest

    with pytest.raises(TypeError):
        ForceConstantsData("not a force constants object")


def test_qpoint_phonon_modes_roundtrip(aiida_profile, quartz_castep_bin):
    """A stored+reloaded QpointPhononModesData reproduces frequencies."""
    force_constants = ForceConstants.from_castep(str(quartz_castep_bin))
    qpts = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]])
    modes = force_constants.calculate_qpoint_phonon_modes(qpts)

    node = QpointPhononModesData(modes)
    node.store()
    reloaded = node.get_modes()

    np.testing.assert_allclose(
        reloaded.frequencies.magnitude, modes.frequencies.magnitude
    )
