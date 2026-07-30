"""Mappings between Euphonic objects and AiiDA's native materials-science types.

AiiDA ships domain data types for reciprocal-space data
(https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/data_types.html#materials-science-data-types):

* ``KpointsData`` -- k-/q-point positions (+ optional labels + cell). We use it as
  the q-point *specification* for Fourier interpolation, and as the natural
  representation of a phonon band path.
* ``BandsData`` (a ``KpointsData`` subclass) -- band energies on those points. A
  Euphonic ``QpointPhononModes`` is essentially ``BandsData`` (frequencies) plus
  eigenvectors, so we build a ``BandsData`` by *composition* and keep the
  eigenvectors in our own ``QpointPhononModesData``.

Using ``BandsData`` also unlocks existing AiiDA plotting, e.g.
``bands.show_mpl()`` pops up a matplotlib band-structure plot without any
AiiDALab dependency.

**These are plain converter functions, deliberately NOT ``calcfunction``s.** They
are the reusable "verbs" that *produce* an object (an AiiDA node or a euphonic
object), called from contexts that each preclude the decorator: inside the
workflow's calcfunctions (``generate_band_path``, ``assemble_bands``) and inside
Data-class methods (``to_structure``/``to_kpoints``/``to_bands``), which must work
without any engine. Several also take/return non-node objects (euphonic
``Crystal``, ``ndarray``), which a calcfunction could not accept. Provenance is
recorded one level up, by the ``@calcfunction``/``PythonJob`` wrappers in
:mod:`aiida_pythonjob_ins.workflows` that call these helpers.

(The reverse direction -- node -> plain Python for aiida-pythonjob *inputs* -- is
a deserialization concern and lives in :mod:`aiida_pythonjob_ins.serialization`.)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from aiida.orm import BandsData, KpointsData, StructureData
from euphonic import Crystal, ureg


def crystal_to_structure(crystal: Crystal) -> StructureData:
    """Convert a Euphonic ``Crystal`` to a native AiiDA ``StructureData``.

    Single source of truth for the Crystal -> StructureData direction (used by
    ``EuphonicCrystalData`` and by ``CrystalStructureMixin.to_structure``). Uses
    AiiDA's native API only -- no ASE. Euphonic stores fractional positions;
    ``StructureData`` wants Cartesian. Masses are carried over for fidelity.
    """
    cell = crystal.cell_vectors.to("angstrom").magnitude
    cartesian = np.asarray(crystal.atom_r) @ cell
    masses = crystal.atom_mass.to("amu").magnitude

    # A euphonic Crystal is always a 3D-periodic lattice, so set pbc explicitly
    # rather than relying on StructureData's default.
    structure = StructureData(cell=cell.tolist(), pbc=(True, True, True))
    for symbol, position, mass in zip(
        crystal.atom_type, cartesian, masses, strict=True
    ):
        structure.append_atom(
            position=position.tolist(), symbols=str(symbol), mass=float(mass)
        )
    return structure


def structure_to_crystal(structure: StructureData) -> Crystal:
    """Convert a native AiiDA ``StructureData`` to a Euphonic ``Crystal``.

    The reverse of :func:`crystal_to_structure`. ``Crystal`` requires atom masses,
    which ``StructureData`` carries on its kinds.
    """
    cell = np.array(structure.cell)
    inverse_cell = np.linalg.inv(cell)
    kinds = {kind.name: kind for kind in structure.kinds}
    atom_r = np.array(
        [np.array(site.position) @ inverse_cell for site in structure.sites]
    )
    atom_type = np.array([kinds[site.kind_name].symbol for site in structure.sites])
    atom_mass = np.array([kinds[site.kind_name].mass for site in structure.sites])
    return Crystal(cell * ureg("angstrom"), atom_r, atom_type, atom_mass * ureg("amu"))


def structure_to_spglib_cell(
    structure: StructureData,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a ``StructureData`` to the spglib/seekpath ``(lattice, positions,
    numbers)`` tuple, reusing Euphonic's ``Crystal.to_spglib_cell`` (rather than
    re-deriving the species numbering by hand).
    """
    return structure_to_crystal(structure).to_spglib_cell()


def qpoints_to_kpoints_data(
    qpoints: np.ndarray,
    cell: np.ndarray,
    labels: list[tuple[int, str]] | None = None,
) -> KpointsData:
    """Build a ``KpointsData`` from fractional q-points, a cell and labels."""
    kpoints = KpointsData()
    kpoints.set_cell(np.asarray(cell))
    kpoints.set_kpoints(np.asarray(qpoints), cartesian=False, labels=labels)
    return kpoints


def modes_to_bands_data(
    modes: Any,
    kpoints: KpointsData | None = None,
) -> BandsData:
    """Compose a ``BandsData`` from Euphonic ``QpointPhononModes``.

    ``BandsData`` is a *join*: q-points + cell + high-symmetry labels (from the
    path) plus frequencies (from ``modes``); neither Euphonic class holds all of
    it (``QpointPhononModes`` has no labels; ``Spectrum1DCollection`` has no
    3-D q-points/eigenvectors).

    Parameters
    ----------
    modes
        A Euphonic ``QpointPhononModes`` object (supplies q-points + frequencies).
    kpoints
        Optional ``KpointsData`` providing the exact q-point positions *and*
        high-symmetry labels (e.g. the path used to compute ``modes``). If given,
        its q-points and cell are **validated** against ``modes`` (a mismatch
        means path and modes are inconsistent). If omitted, positions come from
        ``modes`` and labels fall back to Euphonic's automatic tick labels
        (``QpointPhononModes.get_dispersion().x_tick_labels``).
    """
    cell = modes.crystal.cell_vectors.to("angstrom").magnitude

    if kpoints is not None:
        _validate_kpoints_match_modes(kpoints, modes, cell)
        positions = kpoints.get_kpoints()
        labels = kpoints.labels
    else:
        positions = modes.qpts
        # Euphonic derives tick labels heuristically from the q-point coordinates.
        labels = modes.get_dispersion().x_tick_labels

    bands = BandsData()
    bands.set_cell(cell)
    bands.set_kpoints(positions, cartesian=False, labels=labels)
    # Phonon frequencies play the role of "band energies"; keep them in meV.
    bands.set_bands(modes.frequencies.to("meV").magnitude, units="meV")
    return bands


def _validate_kpoints_match_modes(
    kpoints: KpointsData, modes: Any, cell: np.ndarray
) -> None:
    """Raise if a ``KpointsData`` path is inconsistent with the phonon modes."""
    if not np.allclose(kpoints.get_kpoints(), modes.qpts):
        msg = (
            "KpointsData q-points do not match the phonon modes' q-points; "
            "the band path and the computed modes are inconsistent."
        )
        raise ValueError(msg)
    if not np.allclose(np.asarray(kpoints.cell), cell):
        msg = (
            "KpointsData cell does not match the phonon modes' crystal cell; "
            "q-point fractional coordinates would refer to a different lattice."
        )
        raise ValueError(msg)
