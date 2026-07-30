"""Shared pytest fixtures.

The official AiiDA pytest fixtures (``aiida_profile``, ``aiida_localhost``,
``aiida_code_installed``, ...) are provided by ``aiida.manage.tests.pytest_fixtures``.
Enabling them here gives every test a temporary, throwaway AiiDA profile so no
external services or persistent config are required.
https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/plugins.html#testing-a-plugin
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Redirect AiiDA's configuration to an ephemeral, pytest-owned directory so the
# test session is hermetic: a developer's real, live ``~/.aiida`` (profiles,
# daemon, data) is never read or mutated, and tests run the same with or without
# an existing config.
#
# Why here (module top, before importing aiida): aiida-pythonjob builds its
# serializer registry at *import time*, calling ``get_config()``. With no existing
# config this raises MissingConfigurationError during pytest *collection* -- before
# any fixture can run -- as soon as a test module imports our package. AiiDA reads
# ``AIIDA_PATH`` to locate (and create) its ``.aiida`` config directory, so we set
# it to a fresh temp dir first, then create an empty config there. The
# ``aiida_profile`` fixtures still provide isolated, temporary profiles on top.
#
# ``TemporaryDirectory`` cleans itself up: explicitly via ``pytest_unconfigure``
# below, and as a safety net via its finalizer at interpreter exit. Keeping a
# module-level reference stops it being GC'd (and deleted) mid-session.
_AIIDA_CONFIG_TMPDIR = tempfile.TemporaryDirectory(
    prefix="aiida-test-config-", ignore_cleanup_errors=True
)
os.environ["AIIDA_PATH"] = _AIIDA_CONFIG_TMPDIR.name

from aiida.manage.configuration import get_config  # noqa: E402

get_config(create=True)


def pytest_unconfigure(config):
    """Remove the ephemeral AiiDA config directory at the end of the session."""
    _AIIDA_CONFIG_TMPDIR.cleanup()


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
def phonopy_dir() -> Path:
    """Directory of the bundled NaCl Phonopy example (from the Euphonic suite)."""
    return DATA_DIR / "phonopy" / "NaCl_default"


@pytest.fixture
def phonopy_files(phonopy_dir) -> dict[str, str]:
    """Phonopy summary/force-constants/born file paths (as strings)."""
    return {
        "summary": str(phonopy_dir / "phonopy.yaml"),
        "force_constants": str(phonopy_dir / "FORCE_CONSTANTS"),
        "born": str(phonopy_dir / "BORN"),
    }


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
