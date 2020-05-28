"""Unit tests for the GitHub backend

NOTE: these tests mock actual requests / responses to GitHub
"""
import os

import pytest
from github import GithubException

from metastore.backend.gh import GitHubStorage

from . import CommonBackendTestSuite


class CleaningGitHubStorage(GitHubStorage):
    """A wrapper around the GitHub storage class that cleans up after itself
    """

    def __init__(self, *args, **kwargs):
        super(CleaningGitHubStorage, self).__init__(*args, **kwargs)
        self._packages = set()

    def create(self, package_id, metadata, change_desc=None):
        package = super(CleaningGitHubStorage, self).create(package_id, metadata, change_desc)
        self._packages.add(package.package_id)
        return package

    def cleanup__(self):
        for pkg in self._packages:
            try:
                self.delete(pkg)
            except (GithubException, RuntimeError):
                pass
        self._packages = set()


@pytest.fixture()
def backend():
    backend = CleaningGitHubStorage(github_options={"login_or_token": os.environ.get('GITHUB_TOKEN')},
                                    default_owner=os.environ.get('GITHUB_OWNER'))
    try:
        yield backend
    finally:
        backend.cleanup__()


@pytest.mark.skipif(not (os.environ.get('GITHUB_TOKEN') and os.environ.get('GITHUB_OWNER')),
                    reason="GITHUB_TOKEN or GITHUB OWNER is not set")
@pytest.mark.vcr()
class TestGitHubBackend(CommonBackendTestSuite):

    ID_PREFIX = 'test__'
