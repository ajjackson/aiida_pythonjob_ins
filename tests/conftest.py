"""Shared pytest fixtures.

The official AiiDA pytest fixtures (``aiida_profile``, ``aiida_localhost``,
``aiida_code_installed``, ...) are provided by ``aiida.manage.tests.pytest_fixtures``.
Enabling them here gives every test a temporary, throwaway AiiDA profile so no
external services or persistent config are required.
https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/plugins.html#testing-a-plugin
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest_plugins = ["aiida.tools.pytest_fixtures"]

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def quartz_castep_bin() -> Path:
    """Path to the bundled quartz CASTEP force-constants file.

    Quartz is the canonical Euphonic example material; this ``.castep_bin``
    is copied from the Euphonic test suite.
    """
    return DATA_DIR / "quartz.castep_bin"


@pytest.fixture
def python_code(aiida_code_installed):
    """An AiiDA Code for running PythonJobs on localhost.

    Points at the *current* interpreter (``sys.executable``) so the job runs in
    this project's virtualenv, where euphonic and this package are installed.
    ``pythonjob.pythonjob`` is the calcjob plugin provided by aiida-pythonjob.
    """
    return aiida_code_installed(
        default_calc_job_plugin="pythonjob.pythonjob",
        filepath_executable=sys.executable,
    )
