"""Github Storage Backend implementation
"""
# TODO: Refactor; Copied from ckanext-gitdatahub
import json
import logging

from github import Github, UnknownObjectException

from . import StorageBackend

log = logging.getLogger(__name__)


class GitHubStorage(StorageBackend):

    def __init__(self, **config):
        self.config = config


class CKANGitClient:
    def __init__(self, token, pkg_dict):
        g = Github(token)
        self.auth_user = g.get_user()
        self.pkg_dict = pkg_dict

        repo_name = pkg_dict['name']
        # TODO: Review this key
        repo_notes = pkg_dict['notes']

        self.repo = self.get_or_create_repo(repo_name, repo_notes)

    def get_or_create_repo(self, name, notes):
        try:
            repo = self.auth_user.get_repo(name)

        except UnknownObjectException as e:
            repo = self.auth_user.create_repo(name, notes)

        return repo

    def create_datapackage(self):
        body = converter.dataset_to_datapackage(self.pkg_dict)
        self.repo.create_file(
            'datapackage.json',
            'Create datapackage.json',
            json.dumps(body, indent=2)
            )

    def create_gitattributes(self):
        self.repo.create_file(
        '.gitattributes',
        'Create .gitattributes',
        'data/* filter=lfs diff=lfs merge=lfs -text\n'
        )

    def create_lfsconfig(self, git_lfs_server_url):
        repoUrl = '{}/{}/{}'.format(git_lfs_server_url,self.auth_user.html_url.split('/')[-1],self.pkg_dict['name'])
        self.repo.create_file(
            '.lfsconfig',
            'Create .lfsconfig',
            '[remote "origin"]\n\tlfsurl = ' + repoUrl
            )

    def update_datapackage(self):
        contents = self.repo.get_contents("datapackage.json")
        body = converter.dataset_to_datapackage(self.pkg_dict)
        self.repo.update_file(
            contents.path,
            "Update datapackage.json",
            json.dumps(body, indent=2),
            contents.sha
            )

    def create_or_update_lfspointerfile(self):
        try:
            # TODO: Refactor this using LFSPointer objects
            lfs_pointers = [obj.name for obj in self.repo.get_contents("data")]
            lfs_pointers = {obj:self.get_sha256(obj) for obj in lfs_pointers}

        except UnknownObjectException as e:
            lfs_pointers = dict()

        for obj in self.pkg_dict['resources']:
            if obj['url_type'] == 'upload':
                if obj['name'] not in lfs_pointers.keys():
                    self.create_lfspointerfile(obj)

                elif obj['sha256'] != lfs_pointers[obj['name']]:
                    self.update_lfspointerfile(obj)

    def get_sha256(self, lfspointerfile):
        file_path = "data/{}".format(lfspointerfile)
        file_content = self.repo.get_contents(file_path).decoded_content
        return str(file_content).split('\n')[1].split(':')[-1]

    def create_lfspointerfile(self, obj):
        sha256 = obj['sha256']
        size = obj['size']
        lfs_pointer_body = 'version https://git-lfs.github.com/spec/v1\noid sha256:{}\nsize {}\n'.format(sha256, size)

        self.repo.create_file(
        "data/{}".format(obj['name']),
        "Create LfsPointerFile",
        lfs_pointer_body,
        )

    def update_lfspointerfile(self, obj):
        contents = self.repo.get_contents("data/{}".format(obj['name']))
        sha256 = obj['sha256']
        size = obj['size']
        lfs_pointer_body = 'version https://git-lfs.github.com/spec/v1\noid sha256:{}\nsize {}\n'.format(sha256, size)

        self.repo.update_file(
            contents.path,
            "Update LfsPointerFile",
            lfs_pointer_body,
            contents.sha
            )

    def delete_lfspointerfile(self, resource_name):
        try:
            contents = self.repo.get_contents("data/{}".format(resource_name))
            self.repo.delete_file(
                contents.path,
                "remove lfspointerfile",
                contents.sha)
            log.info("{} lfspointer is deleted.".format(resource_name))
            return True

        except Exception as e:
            return False

    def check_after_delete(self, resources):
        try:
            contents = self.repo.get_contents("data/")

        except UnknownObjectException as e:
            contents = []

        if len(resources) > len(contents):
            contents_name = [obj.name for obj in contents]
            for obj in resources:
                if obj['name'] not in contents_name:
                    self.create_lfspointerfile(obj)
            return True
        return False

    def delete_repo(self):
        try:
            self.repo.delete()
            log.info("{} repository deleted.".format(self.repo.name))
            return True

        except Exception as e:
            return False
