"""Pyfilesystem based versioned metadata storage

This is useful especially for testing and POC implementations
"""
import hashlib
import json
import re
import uuid
from datetime import datetime
from operator import attrgetter
from typing import Any, Dict, List, Optional

import pytz
import six
from dateutil.parser import isoparse
from fs import open_fs
from fs.errors import DirectoryExists, ResourceNotFound

from ..types import Author, PackageRevisionInfo, TagInfo
from ..util import is_hex_str
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
    REVISION_DB_FILE = 'revisions.jsonl'

    TAG_NAME_RE = re.compile(r'^[\w\-+.,]+\Z')

    def __init__(self, uri, default_author=None):
        # type: (str, Optional[Author]) -> None
        self._fs = open_fs(uri)
        self._default_author = default_author

    def create(self, package_id, metadata, author=None, message=None):
        try:
            package_dir = self._fs.makedirs(_get_package_path(package_id))
        except DirectoryExists:
            raise exc.Conflict("Package with id {} already exists".format(package_id))

        revision = _make_revision_id()
        with self._fs.lock():
            with package_dir.open(revision, 'wb') as f:
                f.write(json.dumps(metadata).encode('utf8'))
            rev_info = self._log_revision(package_id, revision, author, message)
        rev_info.package = metadata
        return rev_info

    def fetch(self, package_id, revision_ref=None):
        if not revision_ref:
            # Get the latest revision
            revision = self.revision_list(package_id)[0]
            revision_ref = revision.revision
        elif not is_hex_str(revision_ref, chars=32):
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

    def update(self, package_id, metadata, author=None, partial=False, base_revision_ref=None, message=None):
        current = self.fetch(package_id, base_revision_ref)

        if partial:
            current.package.update(metadata)
            metadata = current.package

        with self._fs.lock():
            revision = _make_revision_id()
            with self._fs.open(u'{}/{}'.format(_get_package_path(package_id), revision), 'wb') as f:
                f.write(json.dumps(metadata).encode('utf8'))
            rev_info = self._log_revision(package_id, revision, author, message)
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

    def tag_create(self, package_id, revision_ref, name, author=None, description=None):
        if not self._validate_tag_name(name):
            raise ValueError("Invalid tag name: {}".format(name))
        revision = self.revision_fetch(package_id, revision_ref)
        return self._log_tag(revision, name, author, description)

    def tag_list(self, package_id):
        tags = []
        tag_dir = self._open_tag_dir(package_id)
        if tag_dir is None:
            return []

        for tag_name in tag_dir.listdir('.'):
            with tag_dir.open(tag_name, 'r') as f:
                tag_line = json.load(f)
            tags.append(_tag_file_to_taginfo(package_id, tag_name, tag_line))

        return sorted(tags, key=attrgetter('created'))

    def tag_fetch(self, package_id, tag):
        if not self._validate_tag_name(tag):
            raise ValueError("Invalid tag name: {}".format(tag))

        tag_info = self._get_tag(package_id, tag)
        if not tag_info:
            raise exc.NotFound('Could not find tag {} for package {}', tag, package_id)

        tag_info.revision = self.revision_fetch(package_id, tag_info.revision_ref)
        return tag_info

    def tag_update(self, package_id, tag, author=None, new_name=None, new_description=None):
        if new_name is None and new_description is None:
            raise ValueError("Expecting at least one of new_name or new_description to be specified")
        elif new_name and not self._validate_tag_name(new_name):
            raise ValueError("Invalid tag name: {}".format(new_name))

        tag_info = self.tag_fetch(package_id, tag)
        name = new_name or tag_info.name
        description = new_description or tag_info.description or None
        overwrite = tag_info.name == name

        with self._fs.lock():
            tag_info = self._log_tag(tag_info.revision, name, author, description, allow_overwrite=overwrite)
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

    def _log_revision(self, package_id, revision, author, message=None):
        # type: (str, str, Optional[Author], Optional[str]) -> PackageRevisionInfo
        """Log a revision
        """
        db_file = u'{}/{}'.format(_get_package_path(package_id), self.REVISION_DB_FILE)
        now = datetime.now(tz=pytz.utc).isoformat()
        author = self._verify_author(author)

        with self._fs.open(db_file, 'ab') as f:
            rev_info = {"revision": revision,
                        "created": now,
                        "description": message,
                        "author_name": author.name,
                        "author_email": author.email}
            f.write('{}\n'.format(json.dumps(rev_info)).encode('utf8'))
        return PackageRevisionInfo(package_id, revision, now, author, message)

    def _get_revisions(self, package_id):
        # type: (str) -> List[PackageRevisionInfo]
        """Get list of revisions from DB file
        """
        db_file = u'{}/{}'.format(_get_package_path(package_id), self.REVISION_DB_FILE)
        with self._fs.open(db_file, 'r') as f:
            lines = [json.loads(line) for line in f]
            revisions = [_parse_rev_log(package_id, line) for line in reversed(lines)]
        return revisions

    def _get_revision(self, package_id, revision):
        # type: (str, str) -> PackageRevisionInfo
        """Get a specific revision from the revisions DB file

        If not found, will return None
        """
        db_file = u'{}/{}'.format(_get_package_path(package_id), self.REVISION_DB_FILE)
        with self._fs.open(db_file, 'r') as f:
            for line in f:
                rev_data = json.loads(line)
                if rev_data['revision'] == revision:
                    return _parse_rev_log(package_id, rev_data)

    def _validate_tag_name(self, name):
        # type: (str) -> bool
        """Validate a tag name
        """
        return bool(self.TAG_NAME_RE.match(name))

    def _log_tag(self, revision, tag_name, author, tag_description, allow_overwrite=False):
        # type: (PackageRevisionInfo, str, Optional[Author], str, bool) -> TagInfo
        """Log a new tag for an existing revision
        """
        tags_path = u'{}/{}'.format(_get_package_path(revision.package_id), 'tags')
        now = datetime.now(tz=pytz.utc)
        tags_dir = self._fs.makedirs(tags_path, recreate=True)
        author = self._verify_author(author)

        with tags_dir.lock():
            if not allow_overwrite and tags_dir.exists(tag_name):
                raise exc.Conflict('Tag already exists: {}'.format(tag_name))

            with tags_dir.open(tag_name, 'wb') as f:
                tag_info = {"created": now.isoformat(),
                            "revision": revision.revision,
                            "description": tag_description,
                            "author_name": author.name,
                            "author_email": author.email}
                f.write(json.dumps(tag_info).encode('utf8'))
        return TagInfo(revision.package_id, tag_name, now, revision.revision, author, revision,
                       description=tag_description)

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
                line = json.load(f)
        except ResourceNotFound:
            return None

        return _tag_file_to_taginfo(package_id, tag_name, line)

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

    def _verify_author(self, author):
        # type: (Optional[Author]) -> Author
        """Verify that we have a valid author object
        """
        if author:
            return author
        if self._default_author:
            return self._default_author
        return Author(None, None)


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


def _parse_rev_log(package_id, rev_data):
    # type: (str, Dict[str, Any]) -> PackageRevisionInfo
    """Parse a line from the revision log and return a RevisionInfo object
    """
    author = _get_author(rev_data)
    return PackageRevisionInfo(package_id=package_id,
                               revision=rev_data['revision'],
                               created=isoparse(rev_data['created']),
                               author=author,
                               description=rev_data['description'])


def _tag_file_to_taginfo(package_id, tag_name, tag_data):
    # type: (str, str, Dict[str, Any]) -> TagInfo
    author = _get_author(tag_data)
    return TagInfo(package_id=package_id,
                   name=tag_name,
                   created=isoparse(tag_data['created']),
                   revision_ref=tag_data['revision'],
                   description=tag_data['description'],
                   author=author)


def _get_author(record):
    # type: (Dict[str, Any]) -> Optional[Author]
    if 'author_name' in record or 'author_email' in record:
        author = Author(name=record.get('author_name'),
                        email=record.get('author_email'))
    else:
        author = None
    return author
