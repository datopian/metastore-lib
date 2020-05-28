"""Tests for the filysystem based storage backend
"""
import pytest

from metastore.backend.filesystem import FilesystemStorage

from . import CommonBackendTestSuite


@pytest.fixture()
def backend():
    return FilesystemStorage('mem://')


class TestFilesystemBackend(CommonBackendTestSuite):
    pass
