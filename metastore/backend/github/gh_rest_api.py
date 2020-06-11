"""Wrapper around the PyGithub imports to resolve name collisions and clean up calling code a little bit
"""

from github import (AuthenticatedUser, GitCommit, Github, GithubException, GitTag, InputGitTreeElement, Organization,
                    PaginatedList, UnknownObjectException)
from github.Commit import Commit
from github.GithubObject import NotSet
from github.GitRef import GitRef
from github.InputGitAuthor import InputGitAuthor
from github.Repository import Repository

__all__ = ['AuthenticatedUser', 'Commit', 'GitCommit', 'Github', 'GithubException', 'GitTag', 'InputGitTreeElement',
           'Organization', 'PaginatedList', 'Repository', 'UnknownObjectException', 'GitRef', 'NotSet',
           'InputGitAuthor']
