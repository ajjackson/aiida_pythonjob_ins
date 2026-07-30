Examples
========

A collection of worked examples. They are executed when the documentation is
built and rendered as a gallery; each can also be downloaded as an executable
Jupyter notebook for further experimentation.

Every example runs a real AiiDA workflow in a temporary, throwaway profile (set
up by a shared helper, ``_aiida_setup.py``), plots the scientific result, and
visualises the AiiDA **provenance graph** that records how it was produced.

Sample data (CASTEP and Phonopy inputs) is bundled in the repository's
``tests/data`` directory and located by the examples at runtime.
