Workflows
=========

The high-level ``WorkChain``\ s and their inputs/outputs. Each accepts *either* a
CASTEP ``castep_file`` or a pre-built ``force_constants`` node (e.g. from Phonopy)
-- see the worked :doc:`examples <auto_examples/index>`.

These pages are generated from the process **spec** by AiiDA's own
``aiida-workchain`` directive, so they show the real inputs, outputs, exit codes
and outline rather than the internal step methods.

.. aiida-workchain:: DispersionWorkChain
   :module: aiida_pythonjob_ins.workflows.dispersion

.. aiida-workchain:: DosWorkChain
   :module: aiida_pythonjob_ins.workflows.dos
