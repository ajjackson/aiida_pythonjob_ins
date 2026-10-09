Workflows
=========

The high-level ``WorkChain``\ s and their inputs/outputs. ``ForceConstantsWorkChain``
resolves a force-constants source (a CASTEP ``castep_file`` or a pre-built
``node``) into a ``ForceConstantsData``; it is also runnable standalone. The
workflows that start from force constants -- ``DispersionWorkChain``,
``DosWorkChain`` and ``ToscaFromForceConstantsWorkChain`` -- run it as a
sub-workflow, grouping its inputs under a single ``force_constants`` namespace
(e.g. ``force_constants={"castep_file": f}`` or ``force_constants={"node": fc}``).
``ToscaFromModesWorkChain`` instead starts from precomputed phonon modes and
offers no force-constants source at all -- see the worked
:doc:`examples <auto_examples/index>`.

These pages are generated from the live process **spec** by AiiDA's
``aiida-workchain`` directive, showing the inputs, outputs, and outline, with
exit codes documented in the class reference.

.. aiida-workchain:: ForceConstantsWorkChain
   :module: aiida_pythonjob_ins.workflows.force_constants

.. aiida-workchain:: DispersionWorkChain
   :module: aiida_pythonjob_ins.workflows.dispersion

.. aiida-workchain:: DosWorkChain
   :module: aiida_pythonjob_ins.workflows.dos

.. aiida-workchain:: ToscaFromModesWorkChain
   :module: aiida_pythonjob_ins.workflows.tosca

.. aiida-workchain:: ToscaFromForceConstantsWorkChain
   :module: aiida_pythonjob_ins.workflows.tosca
