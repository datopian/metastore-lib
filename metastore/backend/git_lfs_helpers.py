"""Git LFS Helpers used by all Git based backends that support Git-LFS
"""
from typing import List, Union

from six import string_types


def generate_gitattributes(track_files):
    # type: (Union[str, List[str]]) -> str
    """Create the contents of a .gitattributes file as required by Git LFS
    """
    if isinstance(track_files, string_types):
        track_files = [track_files]

    lines = ['{} filter=lfs diff=lfs merge=lfs -text\n'.format(p) for p in track_files]
    return ''.join(lines)
