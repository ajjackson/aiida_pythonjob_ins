Workflows
=========

The high-level ``WorkChain``\ s and their inputs/outputs. Each accepts *either* a
CASTEP ``castep_file`` or a pre-built ``force_constants`` node (e.g. from Phonopy)
-- see the worked :doc:`examples <auto_examples/index>`.

These pages are generated from the live process **spec** by AiiDA's
``aiida-workchain`` directive, showing the inputs, outputs, and outline, with
exit codes documented in the class reference.

.. aiida-workchain:: DispersionWorkChain
   :module: aiida_pythonjob_ins.workflows.dispersion

.. aiida-workchain:: DosWorkChain
   :module: aiida_pythonjob_ins.workflows.dos
