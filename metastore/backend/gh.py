# coding=utf-8
"""Github Storage Backend implementation

This backend stores datasets as GitHub repositories, utilizing Git's built-in
revisions and tags. This implementation is based on GitHub's Web API, and will
not support other Git hosting services.
"""
import json
from typing import List, Optional, Tuple, Union

from github import (AuthenticatedUser, Commit, GitCommit, Github, GithubException, GitRef, GitTag, InputGitTreeElement,
                    Organization, PaginatedList, Repository, UnknownObjectException)
from github.GithubObject import NotSet
from github.InputGitAuthor import InputGitAuthor

from ..types import Author, PackageRevisionInfo, TagInfo
from . import StorageBackend, exc


class GitHubStorage(StorageBackend):
    """GitHub based metadata storage
    """

    DEFAULT_README = ('# ¯\\_(ツ)_/¯\n'
                      'This is a datapackage repository created by '
                      '[`metastore-lib`](https://github.com/datopian/metastore-lib)')

    DEFAULT_BRANCH = 'master'

    DEFAULT_COMMIT_MESSAGE = 'Datapackage updated'
    DEFAULT_TAG_MESSAGE = 'Tagging revision'

    def __init__(self, github_options, default_owner=None, default_author=None, default_branch=DEFAULT_BRANCH,
                 default_commit_message=DEFAULT_COMMIT_MESSAGE):
        self.gh = Github(**github_options)
        self._default_owner = default_owner
        self._default_author = default_author
        self._default_branch = default_branch
        self._default_commit_message = default_commit_message
        self._user = None

    def create(self, package_id, metadata, author=None, message=None):
        owner, repo_name = self._parse_id(package_id)

        try:
            repo = self._get_owner(owner).create_repo(repo_name)
        except GithubException as e:
            if e.status == 422 and e.data['errors'][0]['message'] == 'name already exists on this account':
                raise exc.Conflict("Datapackage with the same ID already exists")
            raise

        if message is None:
            message = 'Initial datapackage commit'

        try:
            datapackage = self._create_file('datapackage.json', json.dumps(metadata, indent=2))

            # Create an initial README.md file so we can start using the low-level Git API
            repo.create_file('README.md', 'Initialize data repository', self.DEFAULT_README)
            head = repo.get_branch(self._default_branch)
            commit = self._create_commit(repo, [datapackage], head.commit, author, message)

            # TODO: handle resources / Git LFS config and pointer files

        except Exception:
            self.delete(package_id)
            raise

        c_author = Author(commit.author.name, commit.author.email)
        return PackageRevisionInfo(package_id, commit.sha, commit.author.date, c_author, message, metadata)

    def fetch(self, package_id, revision_ref=None):
        repo = self._get_repo(package_id)
        try:
            if not revision_ref:
                ref = repo.get_git_ref('heads/{}'.format(self._default_branch))
                assert ref.object.type == 'commit'
                revision_ref = ref.object.sha
            elif not _is_sha(revision_ref):
                tag = self.tag_fetch(package_id, revision_ref)
                revision_ref = tag.revision_ref

            # Get the commit pointed by revision_ref
            commit = repo.get_git_commit(revision_ref)

        except UnknownObjectException:
            raise exc.NotFound('Could not find package {}@{}', package_id, revision_ref)

        # Get the blob for datapackage.json in that commit
        try:
            blob = repo.get_contents('datapackage.json', revision_ref)
            datapackage = json.loads(blob.decoded_content)
        except UnknownObjectException:
            raise exc.NotFound("datapackage.json file not found for {}@{}", package_id, revision_ref)
        except ValueError:
            raise ValueError("Unable to parse datapackage.json file in {}@{}".format(package_id, revision_ref))

        author = Author(commit.author.name, commit.author.email)
        return PackageRevisionInfo(package_id, commit.sha, commit.author.date, author, commit.message, datapackage)

    def update(self, package_id, metadata, author=None, partial=False, base_revision_ref=None, message=None):
        parent = self.fetch(package_id, base_revision_ref)
        owner, repo_name = self._parse_id(package_id)

        if message is None:
            message = self._default_commit_message

        if partial:
            parent.package.update(metadata)
            metadata = parent.package

        # TODO: handle resources / Git LFS config and pointer files
        datapackage = self._create_file('datapackage.json', json.dumps(metadata, indent=2))
        repo = self._get_owner(owner).get_repo(repo_name)
        head = repo.get_branch(self._default_branch)
        commit = self._create_commit(repo, [datapackage], head.commit, author, message)
        c_author = Author(commit.author.name, commit.author.email)
        return PackageRevisionInfo(package_id, commit.sha, commit.author.date, c_author, message, metadata)

    def delete(self, package_id):
        repo = self._get_repo(package_id)
        repo.delete()

    def revision_list(self, package_id):
        repo = self._get_repo(package_id)
        commits = repo.get_commits(path='datapackage.json')
        revisions = [_commit_to_revinfo(package_id, c) for c in commits]
        return revisions

    def revision_fetch(self, package_id, revision_ref):
        return self.fetch(package_id, revision_ref)

    def tag_create(self, package_id, revision_ref, name, author=None, description=None):
        repo = self._get_repo(package_id)
        revision = self.revision_fetch(package_id, revision_ref)
        if description is None:
            description = self.DEFAULT_TAG_MESSAGE

        git_tag = self._create_tag(repo, name, description, revision_ref, author)
        t_author = Author(git_tag.tagger.name, git_tag.tagger.email)
        return TagInfo(package_id, name, git_tag.tagger.date, revision_ref, t_author, revision, description)

    def tag_list(self, package_id):
        repo = self._get_repo(package_id)
        tag_refs = _get_git_matching_refs(repo, 'tags/')
        tags = []
        for ref in tag_refs:
            tags.append(self._tag_ref_to_taginfo(package_id, repo, ref))
        return tags

    def tag_fetch(self, package_id, tag):
        repo = self._get_repo(package_id)
        try:
            ref = repo.get_git_ref('tags/{}'.format(tag))
        except UnknownObjectException:
            raise exc.NotFound('Could not find tag {} for package {}', tag, package_id)
        return self._tag_ref_to_taginfo(package_id, repo, ref)

    def tag_update(self, package_id, tag, author=None, new_name=None, new_description=None):
        if new_name is None and new_description is None:
            raise ValueError("Expecting at least one of new_name or new_description to be specified")

        repo = self._get_repo(package_id)
        tag_info = self.tag_fetch(package_id, tag)
        name = new_name or tag_info.name
        description = new_description or tag_info.description

        if name == tag_info.name and description == tag_info.description:
            # Nothing to change here
            return tag_info
        elif name != tag_info.name:
            git_tag = self._create_tag(repo, name, description, tag_info.revision_ref, author)
            repo.get_git_ref('tags/{}'.format(tag_info.name)).delete()
        else:
            git_tag = repo.create_git_tag(name, description, tag_info.revision_ref, 'commit')
            repo.get_git_ref('tags/{}'.format(name)).edit(git_tag.sha)

        t_author = Author(git_tag.tagger.name, git_tag.tagger.email)
        return TagInfo(package_id, name, git_tag.tagger.date, tag_info.revision_ref, t_author, tag_info.revision,
                       description)

    def tag_delete(self, package_id, tag):
        repo = self._get_repo(package_id)
        try:
            ref = repo.get_git_ref('tags/{}'.format(tag))
            ref.delete()
        except UnknownObjectException:
            raise exc.NotFound('Could not find tag {} for package {}', tag, package_id)

    def _parse_id(self, package_id):
        # type: (str) -> Tuple(str, str)
        """Verify that the package ID looks like something we can work with and parse
        it into GitHub owner (user or org) and repo name
        """
        if '/' in package_id:
            return tuple(package_id.split('/', 1))
        elif self._default_owner:
            return self._default_owner, package_id
        else:
            raise ValueError('Invalid package ID for the GitHub backend: {}'.format(package_id))

    def _get_owner(self, owner):
        # type: (str) -> Union[AuthenticatedUser, Organization]
        if self._user is None:
            self._user = self.gh.get_user()
        if owner == self._user.name:
            return self._user
        else:
            return self.gh.get_organization(owner)

    def _get_repo(self, package_id):
        # type: (str) -> Repository
        """Get repository object for package_id, validating that it really
        exists
        """
        owner, repo_name = self._parse_id(package_id)
        try:
            return self._get_owner(owner).get_repo(repo_name)
        except UnknownObjectException:
            raise exc.NotFound('Could not find package {}', package_id)

    def _create_commit(self, repo, files, parent_commit, author, message):
        # type: (Repository, List[InputGitTreeElement], Commit, Optional[Author], str) -> GitCommit
        """Create a git Commit
        """
        # Create tree
        tree = repo.create_git_tree(files, parent_commit.commit.tree)
        # Create commit
        author = self._verify_author(author)
        commit = repo.create_git_commit(message, tree, [parent_commit.commit], author=author)
        # Update refs
        ref = repo.get_git_ref('heads/{}'.format(self._default_branch))
        ref.edit(commit.sha)

        return commit

    def _create_tag(self, repo, name, description, revision_ref, author):
        # type: (Repository.Repository, str, str, str, Optional[Author]) -> GitTag.GitTag
        """Low level operations for creating a git tag
        """
        author = self._verify_author(author)
        try:
            git_tag = repo.create_git_tag(name, description, revision_ref, 'commit', tagger=author)
            repo.create_git_ref('refs/tags/{}'.format(name), git_tag.sha)
        except GithubException as e:
            if e.status == 422:
                if e.data['message'] == 'Reference already exists':
                    raise exc.Conflict('Tag {} already exists'.format(name))
                # Assume invalid name error
                raise ValueError(e)
            raise

        return git_tag

    def _verify_author(self, author):
        # type: (Optional[Author]) -> Union[InputGitAuthor, NotSet]
        """Check we have an author and return something Git can use to set commit / tag author
        """
        if author and (author.name or author.email):
            return InputGitAuthor(author.name, author.email)
        elif self._default_author:
            return InputGitAuthor(self._default_author.name, self._default_author.email)
        else:
            return NotSet

    def _tag_ref_to_taginfo(self, package_id, repo, ref):
        # type: (str, Repository.Repository, GitRef.GitRef) -> TagInfo
        """Convert a GitRef for a tag into a TagInfo object
        """
        tag_obj = repo.get_git_tag(ref.object.sha)
        revision = self.revision_fetch(package_id, tag_obj.object.sha)
        author = Author(tag_obj.tagger.name, tag_obj.tagger.email)
        return TagInfo(package_id, tag_obj.tag, tag_obj.tagger.date, tag_obj.object.sha, author, revision,
                       tag_obj.message)

    @staticmethod
    def _create_file(path, content):
        # type: (str, bytes) -> InputGitTreeElement
        element = InputGitTreeElement(path, '100644', 'blob', content=content)
        return element


def _commit_to_revinfo(package_id, commit):
    # type: (Commit) -> PackageRevisionInfo
    """Convert a GitHub Commit object to a PackageRevisionInfo object
    """
    return PackageRevisionInfo(package_id,
                               commit.sha,
                               commit.commit.author.date,
                               Author(commit.commit.author.name, commit.commit.author.email),
                               commit.commit.message)


def _is_sha(ref, chars=40):
    # type: (str, int) -> bool
    """Check if a string is a revision SHA like string
    This will return True if the ref is a 40-character hex number
    """
    if len(ref) != chars:
        return False
    try:
        int(ref, 16)
    except ValueError:
        return False
    return True


def _get_git_matching_refs(repo, ref):
    """This is backported from PyGithub 1.51 to support Python 2.7 which is no
    longer supported for that version.

    If we ever drop Python 2.7 support, this code is no longer needed and
    :meth:``github.Repository.Repository.get_git_matching_refs`` can be called
    directly.
    """
    if hasattr(repo, 'get_git_matching_refs'):
        return repo.get_git_matching_refs(ref)

    assert isinstance(ref, str), ref
    return PaginatedList.PaginatedList(
        GitRef.GitRef,
        repo._requester,
        repo.url + "/git/matching-refs/" + ref,
        None,
    )


# class CKANGitClient(object):
#
#     def __init__(self, token, pkg_dict):
#         g = Github(token)
#         self.auth_user = g.get_user()
#         self.pkg_dict = pkg_dict
#
#         repo_name = pkg_dict['name']
#         # TODO: Review this key
#         repo_notes = pkg_dict['notes']
#
#         self.repo = self.get_or_create_repo(repo_name, repo_notes)
#
#     def get_or_create_repo(self, name, notes):
#         try:
#             repo = self.auth_user.get_repo(name)
#
#         except UnknownObjectException:
#             repo = self.auth_user.create_repo(name, notes)
#
#         return repo
#
#     def create_datapackage(self):
#         body = converter.dataset_to_datapackage(self.pkg_dict)
#         self.repo.create_file(
#             'datapackage.json',
#             'Create datapackage.json',
#             json.dumps(body, indent=2)
#             )
#
#     def create_gitattributes(self):
#         self.repo.create_file(
#         '.gitattributes',
#         'Create .gitattributes',
#         'data/* filter=lfs diff=lfs merge=lfs -text\n'
#         )
#
#     def create_lfsconfig(self, git_lfs_server_url):
#         repoUrl = '{}/{}/{}'.format(git_lfs_server_url,self.auth_user.html_url.split('/')[-1],self.pkg_dict['name'])
#         self.repo.create_file(
#             '.lfsconfig',
#             'Create .lfsconfig',
#             '[remote "origin"]\n\tlfsurl = ' + repoUrl
#             )
#
#     def update_datapackage(self):
#         contents = self.repo.get_contents("datapackage.json")
#         body = converter.dataset_to_datapackage(self.pkg_dict)
#         self.repo.update_file(
#             contents.path,
#             "Update datapackage.json",
#             json.dumps(body, indent=2),
#             contents.sha
#             )
#
#     def create_or_update_lfspointerfile(self):
#         try:
#             # TODO: Refactor this using LFSPointer objects
#             lfs_pointers = [obj.name for obj in self.repo.get_contents("data")]
#             lfs_pointers = {obj:self.get_sha256(obj) for obj in lfs_pointers}
#
#         except UnknownObjectException as e:
#             lfs_pointers = dict()
#
#         for obj in self.pkg_dict['resources']:
#             if obj['url_type'] == 'upload':
#                 if obj['name'] not in lfs_pointers.keys():
#                     self.create_lfspointerfile(obj)
#
#                 elif obj['sha256'] != lfs_pointers[obj['name']]:
#                     self.update_lfspointerfile(obj)
#
#     def get_sha256(self, lfspointerfile):
#         file_path = "data/{}".format(lfspointerfile)
#         file_content = self.repo.get_contents(file_path).decoded_content
#         return str(file_content).split('\n')[1].split(':')[-1]
#
#     def create_lfspointerfile(self, obj):
#         sha256 = obj['sha256']
#         size = obj['size']
#         lfs_pointer_body = 'version https://git-lfs.github.com/spec/v1\noid sha256:{}\nsize {}\n'.format(sha256, size)
#
#         self.repo.create_file(
#         "data/{}".format(obj['name']),
#         "Create LfsPointerFile",
#         lfs_pointer_body,
#         )
#
#     def update_lfspointerfile(self, obj):
#         contents = self.repo.get_contents("data/{}".format(obj['name']))
#         sha256 = obj['sha256']
#         size = obj['size']
#         lfs_pointer_body = 'version https://git-lfs.github.com/spec/v1\noid sha256:{}\nsize {}\n'.format(sha256, size)
#
#         self.repo.update_file(
#             contents.path,
#             "Update LfsPointerFile",
#             lfs_pointer_body,
#             contents.sha
#             )
#
#     def delete_lfspointerfile(self, resource_name):
#         try:
#             contents = self.repo.get_contents("data/{}".format(resource_name))
#             self.repo.delete_file(
#                 contents.path,
#                 "remove lfspointerfile",
#                 contents.sha)
#             log.info("{} lfspointer is deleted.".format(resource_name))
#             return True
#
#         except Exception as e:
#             return False
#
#     def check_after_delete(self, resources):
#         try:
#             contents = self.repo.get_contents("data/")
#
#         except UnknownObjectException as e:
#             contents = []
#
#         if len(resources) > len(contents):
#             contents_name = [obj.name for obj in contents]
#             for obj in resources:
#                 if obj['name'] not in contents_name:
#                     self.create_lfspointerfile(obj)
#             return True
#         return False
#
#     def delete_repo(self):
#         try:
#             self.repo.delete()
#             log.info("{} repository deleted.".format(self.repo.name))
#             return True
#
#         except Exception as e:
#             return False
