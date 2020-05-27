"""Pyfilesystem based versioned metadata storage

This is useful especially for testing and POC implementations
"""
import base64
import hashlib
import json
import re
import uuid
from datetime import datetime
from operator import attrgetter
from typing import List, Optional

import pytz
import six
from dateutil.parser import isoparse
from fs import open_fs
from fs.errors import DirectoryExists, ResourceNotFound

from ..types import PackageRevisionInfo, TagInfo
from . import StorageBackend, exc


class FilesystemStorage(StorageBackend):
    """Abstract filesystem based storage based on PyFilesystem

    This storage backend is useful mostly in testing, especially with the
    'mem://' file system. You most likely shouldn't be using it in production,
    unless you know exactly what you are doing. This backend does not guarantee
    consistency of storage, and using it in concurrent environments may cause
    issues.

    See the PyFilesystem documentation for types of supported file systems.
    """
    REVISION_DB_FILE = 'revisions.csv'

    TAG_NAME_RE = re.compile(r'^[\w\-+.]+\Z')

    def __init__(self, uri):
        # type: (str) -> None
        self._fs = open_fs(uri)

    def create(self, package_id, metadata, revision_desc=None):
        try:
            package_dir = self._fs.makedirs(_get_package_path(package_id))
        except DirectoryExists:
            raise exc.Conflict("Package with id {} already exists".format(package_id))

        revision = _make_revision_id()
        with self._fs.lock():
            with package_dir.open(revision, 'wb') as f:
                f.write(json.dumps(metadata).encode('utf8'))
            rev_info = self._log_revision(package_id, revision, revision_desc)
        rev_info.package = metadata
        return rev_info

    def fetch(self, package_id, revision_ref=None):
        if not revision_ref:
            # Get the latest revision
            revision = self.revision_list(package_id)[0]
            revision_ref = revision.revision
        elif not _is_revision_like(revision_ref):
            tag = self.tag_fetch(package_id, revision_ref)
            revision_ref = tag.revision_ref
            revision = tag.revision
        else:
            revision = self.revision_fetch(package_id, revision_ref)

        package_path = u'{}/{}'.format(_get_package_path(package_id), revision_ref)
        try:
            with self._fs.open(package_path, 'r') as f:
                revision.package = json.load(f)
        except (ResourceNotFound, ValueError):
            raise exc.NotFound('Could not find package {}@{}', package_id, revision_ref)

        return revision

    def update(self, package_id, metadata, partial=False, base_revision_ref=None, update_description=None):
        current = self.fetch(package_id, base_revision_ref)

        if partial:
            current.package.update(metadata)
            metadata = current.package

        with self._fs.lock():
            revision = _make_revision_id()
            with self._fs.open(u'{}/{}'.format(_get_package_path(package_id), revision), 'wb') as f:
                f.write(json.dumps(metadata).encode('utf8'))
            rev_info = self._log_revision(package_id, revision, update_description)
        rev_info.package = metadata
        return rev_info

    def delete(self, package_id):
        path = _get_package_path(package_id)
        try:
            self._fs.removetree(path)
        except ResourceNotFound:
            raise exc.NotFound('Could not find package {}', package_id)

    def revision_list(self, package_id):
        try:
            revisions = self._get_revisions(package_id)
        except ResourceNotFound:
            raise exc.NotFound('Could not find package {}', package_id)
        return revisions

    def revision_fetch(self, package_id, revision_ref):
        try:
            revision = self._get_revision(package_id, revision_ref)
        except ResourceNotFound:
            raise exc.NotFound('Could not find package {}', package_id)
        if revision is None:
            raise exc.NotFound('Could not find package {}@{}', package_id, revision_ref)
        return revision

    def tag_create(self, package_id, revision_ref, name, description=None):
        if not self._validate_tag_name(name):
            raise ValueError("Invalid tag name: {}".format(name))
        revision = self.revision_fetch(package_id, revision_ref)
        return self._log_tag(revision, name, description)

    def tag_list(self, package_id):
        return self._get_tags(package_id)

    def tag_fetch(self, package_id, tag):
        if not self._validate_tag_name(tag):
            raise ValueError("Invalid tag name: {}".format(tag))

        tag_info = self._get_tag(package_id, tag)
        if not tag_info:
            raise exc.NotFound('Could not find tag {} for package {}', tag, package_id)

        tag_info.revision = self.revision_fetch(package_id, tag_info.revision_ref)
        return tag_info

    def tag_update(self, package_id, tag, new_name=None, new_description=None):
        if new_name is None and new_description is None:
            raise ValueError("Expecting at least one of new_name or new_description to be specified")
        elif new_name and not self._validate_tag_name(new_name):
            raise ValueError("Invalid tag name: {}".format(new_name))

        tag_info = self.tag_fetch(package_id, tag)
        name = new_name or tag_info.name
        description = new_description or tag_info.description or None
        overwrite = tag_info.name == name

        with self._fs.lock():
            tag_info = self._log_tag(tag_info.revision, name, description, allow_overwrite=overwrite)
            if not overwrite:
                self.tag_delete(package_id, tag)

        return tag_info

    def tag_delete(self, package_id, tag):
        with self._fs.lock():
            tags_dir = self._open_tag_dir(package_id)
            try:
                tags_dir.remove(tag)
            except ResourceNotFound:
                raise exc.NotFound('Could not find tag {} for package {}', tag, package_id)

    def _log_revision(self, package_id, revision, revision_desc=None):
        # type: (str, str, Optional[str]) -> PackageRevisionInfo
        """Log a revision
        """
        db_file = u'{}/{}'.format(_get_package_path(package_id), self.REVISION_DB_FILE)
        now = datetime.now(tz=pytz.utc).isoformat()
        with self._fs.open(db_file, 'ab') as f:
            encoded_desc = base64.b64encode(revision_desc.encode('utf8')) if revision_desc else b''
            line = '{},{},{}\n'.format(revision, now, encoded_desc.decode('utf8'))
            f.write(line.encode('utf8'))
        return PackageRevisionInfo(package_id, revision, now, revision_desc)

    def _get_revisions(self, package_id):
        # type: (str) -> List[PackageRevisionInfo]
        """Get list of revisions from DB file
        """
        db_file = u'{}/{}'.format(_get_package_path(package_id), self.REVISION_DB_FILE)
        with self._fs.open(db_file, 'r') as f:
            rev_data = [line.split(',', 2) for line in f]
        return [_parse_rev_log(package_id, r) for r in reversed(rev_data)]

    def _get_revision(self, package_id, revision):
        # type: (str, str) -> PackageRevisionInfo
        """Get a specific revision from the revisions DB file

        If not found, will return None
        """
        db_file = u'{}/{}'.format(_get_package_path(package_id), self.REVISION_DB_FILE)
        with self._fs.open(db_file, 'r') as f:
            for line in f:
                rev_data = line.split(',', 2)
                if rev_data[0] == revision:
                    return _parse_rev_log(package_id, rev_data)

    def _validate_tag_name(self, name):
        # type: (str) -> bool
        """Validate a tag name
        """
        return bool(self.TAG_NAME_RE.match(name))

    def _log_tag(self, revision, tag_name, tag_description, allow_overwrite=False):
        # type: (PackageRevisionInfo, str, str) -> TagInfo
        """Log a new tag for an existing revision
        """
        tags_path = u'{}/{}'.format(_get_package_path(revision.package_id), 'tags')
        now = datetime.now(tz=pytz.utc)
        tags_dir = self._fs.makedirs(tags_path, recreate=True)

        with tags_dir.lock():
            if not allow_overwrite and tags_dir.exists(tag_name):
                raise exc.Conflict('Tag already exists: {}'.format(tag_name))

            with tags_dir.open(tag_name, 'wb') as f:
                f.write('{},{},'.format(now.isoformat(), revision.revision).encode('utf8'))
                if tag_description:
                    f.write(base64.b64encode(tag_description.encode('utf8')))
        return TagInfo(revision.package_id, tag_name, now, revision.revision, revision, description=tag_description)

    def _get_tag(self, package_id, tag_name):
        # type: (str, str) -> Optional[TagInfo]
        """Get a specific tag from the tags DB file

        If not found, will return None
        """
        try:
            tag_dir = self._open_tag_dir(package_id)
            if not tag_dir:
                return None
            with tag_dir.open(tag_name, 'r') as f:
                line = f.read()
        except ResourceNotFound:
            return None

        return _parse_tag_file_content(package_id, tag_name, line)

    def _get_tags(self, package_id):
        # type: (str) -> List[TagInfo]
        """Get list of all tags from the tag DB file
        """
        tags = []
        tag_dir = self._open_tag_dir(package_id)
        if tag_dir is None:
            return []

        for tag_name in tag_dir.listdir('.'):
            with tag_dir.open(tag_name, 'r') as f:
                tag_line = f.read()
            tags.append(_parse_tag_file_content(package_id, tag_name, tag_line))

        return sorted(tags, key=attrgetter('created'))

    def _open_tag_dir(self, package_id):
        """Open a tag directory and return it
        """
        try:
            package_dir = self._fs.opendir(_get_package_path(package_id))
        except ResourceNotFound:
            raise exc.NotFound('Could not find package {}', package_id)

        try:
            return package_dir.opendir('tags')
        except ResourceNotFound:
            return None


def _get_package_path(package_id):
    # type: (str) -> six.text_type
    """Create a package path
    """
    return u'/p/{}'.format(hashlib.sha256(package_id.encode('utf8')).hexdigest())


def _make_revision_id():
    # type: () -> str
    """Generate a random unique revision ID
    """
    return uuid.uuid4().hex


def _is_revision_like(ref):
    # type: (str) -> bool
    """Check if a string is a revision-ref like string

    This will return True if the ref is a 32-character hex number
    """
    if len(ref) != 32:
        return False
    try:
        int(ref, 16)
    except ValueError:
        return False
    return True


def _parse_rev_log(package_id, rev_data):
    # type: (str, List[str]) -> PackageRevisionInfo
    """Parse a line from the revision log and return a RevisionInfo object
    """
    return PackageRevisionInfo(package_id, rev_data[0], isoparse(rev_data[1]),
                               description=_decode_text_blob(rev_data[2]))


def _parse_tag_file_content(package_id, tag_name, tag_line):
    # type: (str, str, str) -> TagInfo
    tag_data = tag_line.split(',', 2)
    return TagInfo(package_id, tag_name, isoparse(tag_data[0]), tag_data[1],
                   description=_decode_text_blob(tag_data[2]))


def _decode_text_blob(encoded_desc):
    # type: (str) -> Optional[str]
    """Decode a base64-encoded text blob saved in DB file for revision / tag
    """
    if encoded_desc:
        return base64.b64decode(encoded_desc).decode('utf8')
    return None
