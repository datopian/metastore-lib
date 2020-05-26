"""Unit tests for the GitHub backend

NOTE: these tests mock actual requests / responses to GitHub
"""
import pytest

from metastore.backend.gh import GitHubStorage


@pytest.mark.skip()
def test_gh_create(requests_mock):
    storage = GitHubStorage(token='test-token')
    metadata = {"name": "my-package",
                "resources": [
                    {"path": "data/resource.csv"}
                ]}
    actual = storage.create('myorg/mypackage', metadata)
    assert 'my-package' == actual.package['name']


def test_gh_update():
    pass
