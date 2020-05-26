"""Tests for the Git LFS helpers module
"""
from metastore.backend import git_lfs_helpers


def test_generate_gitattributes():
    expected = 'data/* filter=lfs diff=lfs merge=lfs -text\n'
    assert expected == git_lfs_helpers.generate_gitattributes('data/*')


def test_generate_gitattributes_multi_patterns():
    expected = ('data/*.csv filter=lfs diff=lfs merge=lfs -text\n'
                'data/*.xls filter=lfs diff=lfs merge=lfs -text\n')
    assert expected == git_lfs_helpers.generate_gitattributes(['data/*.csv', 'data/*.xls'])
