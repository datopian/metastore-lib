"""Base library tests
"""
from metastore.backend import create_metastore
from metastore.backend.filesystem import FilesystemStorage
from metastore.backend.github import GitHubStorage


def test_factory_instantiates_filesystem_backend():
    backend = create_metastore('filesystem', dict(uri='mem://'))
    assert isinstance(backend, FilesystemStorage)


def test_factory_instantiates_github_backend():
    backend = create_metastore('github', {"github_options": {}})
    assert isinstance(backend, GitHubStorage)
