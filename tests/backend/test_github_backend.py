"""Unit tests for the GitHub backend

NOTE: these tests mock actual requests / responses to GitHub
"""
import logging
import os

import pytest
from github import GithubException

from metastore.backend.gh import GitHubStorage

from . import CommonBackendTestSuite, create_test_datapackage


class CleaningGitHubStorage(GitHubStorage):
    """A wrapper around the GitHub storage class that cleans up after itself
    """

    def __init__(self, *args, **kwargs):
        super(CleaningGitHubStorage, self).__init__(*args, **kwargs)
        self._packages = set()
        self._log = logging.getLogger(__name__)

    def create(self, package_id, metadata, change_desc=None):
        package = super(CleaningGitHubStorage, self).create(package_id, metadata, change_desc)
        self._packages.add(package.package_id)
        return package

    def cleanup__(self):
        for pkg in self._packages:
            try:
                self.delete(pkg)
            except (GithubException, RuntimeError):
                self._log.warning("Failed cleaning up GitHub repo after test: %s", pkg)
        self._packages = set()


@pytest.fixture()
def backend():
    backend = CleaningGitHubStorage(github_options={"login_or_token": os.environ.get('GITHUB_TOKEN')},
                                    default_owner=os.environ.get('GITHUB_OWNER'))
    try:
        yield backend
    finally:
        backend.cleanup__()


# @pytest.mark.vcr()
@pytest.mark.skipif(not (os.environ.get('GITHUB_TOKEN') and os.environ.get('GITHUB_OWNER')),
                    reason="GITHUB_TOKEN or GITHUB OWNER is not set")
class TestGitHubBackend(CommonBackendTestSuite):

    ID_PREFIX = 'test__'

    # GitHub has different rules for valid tag names

    @pytest.mark.parametrize('name', [
        'with space',
        'with\n',
        '',
    ])
    def test_tag_create_invalid_names(self, name, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        with pytest.raises(ValueError):
            backend.tag_create(p1.package_id, p1.revision, name, description="Invalid tag name")
