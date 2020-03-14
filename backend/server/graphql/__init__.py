"""Module for GraphQL schema and related queries and types."""

import graphene
from .schema import Query

schema = graphene.Schema(query=Query)
