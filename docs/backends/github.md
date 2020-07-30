# `github` - GitHub storage

The `github` storage uses [GitHub](https://github.com)'s API to store your 
metadata as a Git repository on GitHub. It uses Git revisions and tags to
keep track of changes, and will even automatically create Git LFS pointers
and configuration if applicable. 

## GitHub Credentials

Currently, `metastore-lib`'s GitHub backend supports authentication using 
a GitHub username and password (not recommended), or a Personal Access Token. 

In the future, we plan to add support for GitHub App based authentication. See
[this issue](https://github.com/datopian/metastore-lib/issues/18) for discussion
and progress details. 

### Username and Password Authentication

The following example demonstrates instantiating a GitHub storage backend with
username / password authentication:

```python
import metastore

# Using your user name and password to authenticate with GitHub 
config = {"github_options": {"login_or_token": "mr_username",
                             "password": "s0mena5tys3c4et!!1one"}}
backend = metastore.create_metastore('github', config) 
```

### Personal Access Token Authentication

To obtain a Personal Access Token, follow the instructions in 
[the relevant section in the GitHub Documentation](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).
The following permission scopes are required by `metastore-lib` and should be 
granted:

* `repo` and `repo:status` (other sub-scopes of repo are not required)
* `repo_delete`

If your GitHub organization requires SSO authentication, follow the steps
[described here](https://docs.github.com/en/github/authenticating-to-github/authorizing-a-personal-access-token-for-use-with-saml-single-sign-on)
after creating the token.

The following example demonstrates doing the same but using a personal access
token instead:

```python
import metastore

# Using a generated Personal Access Token to authenticate with GitHub 
config = {"github_options": {"login_or_token": "averylongtokenthatwasgeneratedespeciallyforthis"}}
backend = metastore.create_metastore('github', config) 
```
 
## Other Configuration Options

TBD 

## Git LFS Support

TBD