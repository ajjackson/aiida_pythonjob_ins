"""Band structure and DOS from Phonopy input
============================================

Read force constants from **Phonopy** output (NaCl: ``phonopy.yaml`` +
``FORCE_CONSTANTS`` + ``BORN``) as a ``PythonJob``, then reuse the *same*
:class:`~aiida_pythonjob_ins.workflows.DispersionWorkChain` and
:class:`~aiida_pythonjob_ins.workflows.DosWorkChain` -- they accept a
``force_constants`` node, so nothing about them is CASTEP-specific.
"""

# %%
# Set up AiiDA
# ------------

from _aiida_setup import example_data, get_python_code, show_provenance
from aiida import orm
from aiida.engine import run_get_node
from aiida_pythonjob import PythonJob

code = get_python_code()

# %%
# Read force constants from Phonopy
# ---------------------------------
# A PythonJob stages the Phonopy files and returns a ``ForceConstantsData`` node.

from aiida_pythonjob_ins.pythonjobs import prepare_read_phonopy_inputs

read_results, _ = run_get_node(
    PythonJob,
    **prepare_read_phonopy_inputs(
        summary=example_data("phonopy", "NaCl_default", "phonopy.yaml"),
        force_constants=example_data("phonopy", "NaCl_default", "FORCE_CONSTANTS"),
        born=example_data("phonopy", "NaCl_default", "BORN"),
        code=code,
    ),
)
force_constants = read_results["result"]
print(f"Force constants: {force_constants.get_force_constants().crystal.n_atoms} atoms")

# %%
# Band structure
# --------------
# Feed the Phonopy-derived force constants straight into the dispersion workflow.

from aiida.plugins import WorkflowFactory

# Load via WorkflowFactory (direct imports like
# `from aiida_pythonjob_ins.workflows import ...` also work)
DispersionWorkChain = WorkflowFactory("pythonjob_ins.dispersion")
DosWorkChain = WorkflowFactory("pythonjob_ins.dos")

bands_results, bands_node = run_get_node(
    DispersionWorkChain,
    force_constants=force_constants,
    q_spacing=orm.Float(0.1),
    code=code,
)
bands_results["band_structure"].show_mpl()

# %%
# Density of states
# -----------------

dos_results, _ = run_get_node(
    DosWorkChain,
    force_constants=force_constants,
    q_spacing=orm.Float(0.2),
    energy_spacing=orm.Float(1.0),
    code=code,
)

import matplotlib.pyplot as plt

dos = dos_results["dos"]
_, energy, energy_unit = dos.get_x()
((_, density, dos_unit),) = dos.get_y()

fig, ax = plt.subplots()
ax.plot(energy, density)
ax.set_xlabel(f"Energy ({energy_unit})")
ax.set_ylabel(f"Density of states ({dos_unit})")
ax.set_title("NaCl phonon DOS (from Phonopy)")
fig.tight_layout()

# %%
# Provenance
# ----------
# The graph traces the band structure back through the dispersion workflow to the
# Phonopy read job -- the full history in one picture.

show_provenance(bands_node, title="Phonopy -> dispersion provenance")
