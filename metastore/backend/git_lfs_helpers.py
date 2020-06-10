"""Git LFS Helpers used by all Git based backends that support Git-LFS
"""
from typing import Any, Dict, Iterable, Union

from six import string_types

from ..util import is_hex_str


def is_posix_path_resource(resource):
    # type: (Dict[str, Any]) -> bool
    """Tell if a resource represents a POSIX-path (i.e. local file) resource

    >>> is_posix_path_resource({"path": "data/file.csv"})
    True

    >>> is_posix_path_resource({"path": "a file with some stange name"})
    True

    >>> is_posix_path_resource({"path": "http://example.com/my-resource"})
    False

    >>> is_posix_path_resource({"data": "some-inline-data"})
    False

    >>> is_posix_path_resource({"path": ["file1.csv", "file2.csv"]})
    False
    """
    if 'path' not in resource:
        return False

    if not isinstance(resource['path'], str):
        return False

    if resource['path'][:7] in {'http://', 'https:/'}:
        return False

    return True


def has_lfs_attributes(resource):
    # type: (Dict[str, Any]) -> bool
    """Tell if a resource has the attributes required for an LFS-stored resource

    >>> has_lfs_attributes({"path": "data.csv", "bytes": 1234, "sha256": "someshavalue"})
    True

    >>> has_lfs_attributes({"path": "data.csv", "size": 1234, "sha256": "someshavalue"})
    False

    >>> has_lfs_attributes({"path": "data.csv", "sha256": "someshavalue"})
    False

    >>> has_lfs_attributes({"path": "data.csv", "bytes": 1234})
    False

    >>> has_lfs_attributes({"path": "data.csv"})
    False
    """
    if not isinstance(resource.get('sha256'), str):
        return False

    if not isinstance(resource.get('bytes'), int):
        return False

    return True


def create_git_attributes_file(track_files):
    # type: (Union[str, Iterable[str]]) -> str
    """Create the contents of a .gitattributes file as required by Git LFS
    """
    if isinstance(track_files, string_types):
        track_files = [track_files]

    lines = ['{} filter=lfs diff=lfs merge=lfs -text\n'.format(p) for p in track_files]
    return ''.join(lines)


def create_lfs_config_file(lfs_server_url, remote='origin'):
    # type: (str, str) -> str
    """Create contents of .lfsconfig file
    """
    return '[remote "{remote}"]\n\tlfsurl = {lfsurl}'.format(remote=remote, lfsurl=lfs_server_url)


def create_lfs_pointer_file(resource):
    # type: (Dict[str, Any]) -> str
    """Create contents for LFS pointer file
    """
    if not is_hex_str(resource['sha256'], chars=64):
        raise ValueError('Resource sha256 value does not seem to be a valid sha256 hex string')

    return ('version https://git-lfs.github.com/spec/v1\n'
            'oid sha256:{}\n'
            'size {}\n').format(resource['sha256'], resource['bytes'])
