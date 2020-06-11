"""Unit tests for the GitHub backend

NOTE: these tests mock actual requests / responses to GitHub
"""
import logging
import os

import pytest
from github import GithubException

from metastore.backend.github import GitHubStorage

from . import CommonBackendTestSuite, create_test_datapackage


class CleaningGitHubStorage(GitHubStorage):
    """A wrapper around the GitHub storage class that cleans up after itself
    """

    def __init__(self, *args, **kwargs):
        super(CleaningGitHubStorage, self).__init__(*args, **kwargs)
        self._packages = set()
        self._log = logging.getLogger(__name__)

    def create(self, package_id, metadata, author=None, message=None):
        package = super(CleaningGitHubStorage, self).create(package_id, metadata, author, message)
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


@pytest.fixture()
def lfs_backend():
    backend = CleaningGitHubStorage(github_options={"login_or_token": os.environ.get('GITHUB_TOKEN')},
                                    default_owner=os.environ.get('GITHUB_OWNER'),
                                    lfs_server_url='https://lfs.example.com/foo/bar')
    try:
        yield backend
    finally:
        backend.cleanup__()


def create_test_lfs_package(name, **kwargs):
    if 'resources' in kwargs:
        return create_test_datapackage(name, **kwargs)

    pkg = create_test_datapackage(name, **kwargs)
    pkg['resources'][0].update({
        "sha256": '0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a',
        "bytes": 1744
    })
    return pkg


@pytest.fixture(scope='module')
def vcr_config():
    have_github_access = bool(os.environ.get('GITHUB_TOKEN') and os.environ.get('GITHUB_OWNER'))
    force_record = bool(os.environ.get('DISABLE_VCR'))
    if have_github_access:
        if force_record:
            mode = 'all'
        else:
            mode = 'once'
    else:
        mode = 'none'

    return {
        "filter_headers": [
            ('authorization', 'fake-authz-header')
        ],
        "record_mode": mode
    }


@pytest.mark.vcr()
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

    def test_datapackage_create_fetch_with_lfs(self, lfs_backend):
        """Test we can create and fetch packages with LFS configured
        """
        p1_info = lfs_backend.create(self.dataset_id('mydataset'), create_test_lfs_package('mydataset'))

        assert p1_info.package_id == self.dataset_id('mydataset')
        assert p1_info.revision is not None
        assert p1_info.package['resources'][0]['path'] == 'data/myresource.csv'

        p2_info = lfs_backend.fetch(self.dataset_id('mydataset'))
        assert p1_info.package == p2_info.package
        assert p2_info.package['resources'][0]['bytes'] == 1744

    def test_datapackage_create_with_lfs_conflicting_resources(self, lfs_backend):
        """Test the backend does not accept conflicting LFS resources
        """
        datapkg = create_test_lfs_package('mydataset')
        datapkg['resources'].append({
            "path": "data/myresource.csv",
            "bytes": 1515,
            "sha256": "08419486253228102a04995a0376ffdaec0bf1dbaf9cff3669f34d29ad483a02",
        })

        with pytest.raises(ValueError):
            lfs_backend.create(self.dataset_id('mydataset'), datapkg)

    @pytest.mark.parametrize('path', [
        '/foo/someresource.csv',
        'foo/../../someresource.csv',
        '../foo/someresource.csv'
    ])
    def test_datapackage_create_with_lfs_invalid_resources(self, lfs_backend, path):
        """Test the backend does not accept conflicting LFS resources
        """
        datapkg = create_test_lfs_package('mydataset')
        datapkg['resources'][0].update({
            "path": path,
            "bytes": 1515,
            "sha256": "08419486253228102a04995a0376ffdaec0bf1dbaf9cff3669f34d29ad483a02",
        })

        with pytest.raises(ValueError):
            lfs_backend.create(self.dataset_id('mydataset'), datapkg)
