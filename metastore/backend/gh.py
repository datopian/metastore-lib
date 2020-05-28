# coding=utf-8
"""Github Storage Backend implementation

TODO: Implement me; Original code copied from ckanext-gitdatahub
"""
import json
from typing import List, Tuple, Union

from github import (AuthenticatedUser, Commit, GitCommit, Github, GithubException, InputGitTreeElement, Organization,
                    Repository, UnknownObjectException)
from metastore.types import PackageRevisionInfo

from . import StorageBackend, exc


class GitHubStorage(StorageBackend):
    """GitHub based metadata storage
    """

    DEFAULT_README = ('# ¯\\_(ツ)_/¯\n'
                      'This is a datapackage repository created by '
                      '[`metastore-lib`](https://github.com/datopian/metastore-lib)')

    DEFAULT_BRANCH = 'master'
    
    DEFAULT_COMMIT_MESSAGE = 'Datapackage updated'

    def __init__(self, github_options, default_owner=None, default_branch=DEFAULT_BRANCH, 
                 default_commit_message=DEFAULT_COMMIT_MESSAGE):
        self.gh = Github(**github_options)
        self._default_owner = default_owner
        self._default_branch = default_branch
        self._default_commit_message = default_commit_message
        self._user = None

    def create(self, package_id, metadata, change_desc=None):
        owner, repo_name = self._parse_id(package_id)

        try:
            repo = self._get_owner(owner).create_repo(repo_name)
        except GithubException as e:
            if e.status == 422 and e.data['errors'][0]['message'] == 'name already exists on this account':
                raise exc.Conflict("Datapackage with the same ID already exists")
            raise

        if change_desc is None:
            change_desc = 'Initial datapackage commit'

        try:
            datapackage = self._create_file('datapackage.json', json.dumps(metadata).encode('utf8'))

            # Create an initial README.md file so we can start using the low-level Git API
            repo.create_file('README.md', 'Initialize data repository', self.DEFAULT_README)
            head = repo.get_branch(self._default_branch)
            commit = self._create_commit(repo, [datapackage], head.commit, change_desc)

            # TODO: handle resources / Git LFS config and pointer files

        except Exception:
            self.delete(package_id)
            raise

        return PackageRevisionInfo(package_id, commit.sha, commit.author.date, change_desc, metadata)

    def fetch(self, package_id, revision_ref=None):
        owner, repo_name = self._parse_id(package_id)

        try:
            repo = self._get_owner(owner).get_repo(repo_name)
            if not revision_ref:
                ref = repo.get_git_ref('heads/{}'.format(self._default_branch))
                assert ref.object.type == 'commit'
                revision_ref = ref.object.sha
            elif not _is_sha(revision_ref):  # TODO: this may not work for tags
                ref = repo.get_git_ref('heads/{}'.format(revision_ref))
                assert ref.object.type == 'commit'
                revision_ref = ref.object.sha

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

        return PackageRevisionInfo(package_id, commit.sha, commit.author.date, commit.message, datapackage)

    def update(self, package_id, metadata, partial=False, base_revision_ref=None, update_description=None):
        parent = self.fetch(package_id, base_revision_ref)
        owner, repo_name = self._parse_id(package_id)

        if update_description is None:
            update_description = self._default_commit_message

        if partial:
            parent.package.update(metadata)
            metadata = parent.package

        # TODO: handle resources / Git LFS config and pointer files
        datapackage = self._create_file('datapackage.json', json.dumps(metadata).encode('utf8'))
        repo = self._get_owner(owner).get_repo(repo_name)
        head = repo.get_branch(self._default_branch)
        commit = self._create_commit(repo, [datapackage], head.commit, update_description)
        return PackageRevisionInfo(package_id, commit.sha, commit.author.date, update_description, metadata)

    def delete(self, package_id):
        owner, repo_name = self._parse_id(package_id)
        try:
            repo = self._get_owner(owner).get_repo(repo_name)
        except UnknownObjectException:
            raise exc.NotFound('Could not find package {}', package_id)
        repo.delete()

    def revision_list(self, package_id):
        pass

    def revision_fetch(self, package_id, revision_ref):
        pass

    def tag_create(self, package_id, revision_ref, name, description=None):
        pass

    def tag_list(self, package_id):
        pass

    def tag_fetch(self, package_id, tag):
        pass

    def tag_update(self, package_id, tag, new_name=None, new_description=None):
        pass

    def tag_delete(self, package_id, tag):
        pass

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

    def _create_commit(self, repo, files, parent_commit, message):
        # type: (Repository, List[InputGitTreeElement], Commit, str) -> GitCommit
        """Create a git Commit
        """
        # Create tree
        tree = repo.create_git_tree(files, parent_commit.commit.tree)
        # Create commit
        commit = repo.create_git_commit(message, tree, [parent_commit.commit])
        # Update refs
        ref = repo.get_git_ref('heads/{}'.format(self._default_branch))
        ref.edit(commit.sha)

        return commit

    @staticmethod
    def _create_file(path, content):
        # type: (str, bytes) -> InputGitTreeElement
        element = InputGitTreeElement(path, '100644', 'blob', content=content)
        return element

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
