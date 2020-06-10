"""Tests for the Git LFS helpers module
"""
import pytest

from metastore.backend import git_lfs_helpers


def test_create_git_attributes():
    expected = 'data/* filter=lfs diff=lfs merge=lfs -text\n'
    assert expected == git_lfs_helpers.create_git_attributes_file('data/*')


def test_create_git_attributes_multi_patterns():
    expected = ('data/*.csv filter=lfs diff=lfs merge=lfs -text\n'
                'data/*.xls filter=lfs diff=lfs merge=lfs -text\n')
    assert expected == git_lfs_helpers.create_git_attributes_file(['data/*.csv', 'data/*.xls'])


def test_create_lfs_config_file():
    expected = '[remote "origin"]\n\tlfsurl = https://lfs.example.com/foo/bar'
    assert expected == git_lfs_helpers.create_lfs_config_file('https://lfs.example.com/foo/bar')


def test_create_lfs_config_file_custom_remote_name():
    expected = '[remote "baz-baz"]\n\tlfsurl = https://lfs.example.com/baz/baz'
    assert expected == git_lfs_helpers.create_lfs_config_file('https://lfs.example.com/baz/baz', remote='baz-baz')


def create_lfs_pointer_file():
    resource = {"sha256": "0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a",
                "bytes": 1744,
                "path": "data/resource.csv"}

    expected = ('version https://git-lfs.github.com/spec/v1\n'
                'oid sha256:0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a\n'
                'size 1744\n')

    assert expected == git_lfs_helpers.create_lfs_pointer_file(resource)


@pytest.mark.parametrize('resource', [
    {"bytes": 1744, "path": "data/resource.csv"},
    {"sha256": "0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a"},
    {"bytes": 1744, "sha256": "ef42bab1191da272f13935f78c401e3de0c11afb"},
    {"bytes": 1744, "sha256": "0f112804X248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a"},
    {"sha256": "0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a", "size": 1744},
])
def create_lfs_pointer_file_invalid_resource(resource):
    with pytest.raises(ValueError):
        git_lfs_helpers.create_lfs_pointer_file(resource)
