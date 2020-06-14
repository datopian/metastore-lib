"""Helpers around GitHub's GraphQL API
"""
import pkg_resources

from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from graphql import GraphQLSchema, build_ast_schema, parse

GITHUB_GQL_API_URL='https://api.github.com/graphql'


def load_schema():
    # type: () -> GraphQLSchema
    schema_path = pkg_resources.resource_filename(__name__, 'schema.public.graphql')
    with open(schema_path) as source:
        document = parse(source.read())

    return build_ast_schema(document)


GithubSchema = load_schema()


def get_client(token):
    transport = RequestsHTTPTransport(
        url=GITHUB_GQL_API_URL,
        headers={"Authorization": token}
    )
    return Client(schema=GithubSchema,
                  transport=transport)
