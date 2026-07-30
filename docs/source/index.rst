aiida-pythonjob-ins documentation
=================================

Proof-of-concept `AiiDA <https://www.aiida.net/>`_ plugin that wraps inelastic
neutron scattering (INS) Python libraries -- starting with
`Euphonic <https://euphonic.readthedocs.io/en/stable/>`_ -- using the
`aiida-pythonjob <https://github.com/aiidateam/aiida-pythonjob>`_ execution model
(running Python functions as AiiDA jobs) rather than command-line wrappers.

.. important::

   Proof-of-concept / alpha: names and APIs will change. Pin to a minor version
   if you build on it.

The worked examples below are executed when the documentation is built: each runs
a real AiiDA workflow, plots the result, and visualises the resulting provenance
graph. They can be downloaded as Jupyter notebooks for experimentation.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   auto_examples/index
   autoapi/index
