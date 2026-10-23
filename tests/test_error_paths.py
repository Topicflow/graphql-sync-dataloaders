import pytest
from graphql import (
    GraphQLError,
    GraphQLField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    graphql_sync,
)

from graphql_sync_dataloaders import DeferredExecutionContext, SyncDataLoader


@pytest.mark.parametrize(
    "deferred,required", [(False, False), (False, True), (True, False)]
)
@pytest.mark.parametrize("as_list", [False, True])
def test_error_paths_and_null_propagation(deferred, as_list, required):
    error = GraphQLError("Access denied", extensions={"code": "FORBIDDEN"})
    loader = SyncDataLoader(lambda keys: [error for key in keys])
    value_type = GraphQLNonNull(GraphQLString) if required else GraphQLString
    field_type = GraphQLList(value_type) if as_list else value_type

    def resolve_value(_source, _info):
        value = loader.load("value") if deferred else error
        return [value] if as_list else value

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            {"value": GraphQLField(field_type, resolve=resolve_value)},
        )
    )
    result = graphql_sync(
        schema, "{ alias: value }", execution_context_class=DeferredExecutionContext
    )

    assert result.data == (
        {"alias": [None]}
        if as_list and not required
        else None if required and not as_list else {"alias": None}
    )
    assert result.formatted["errors"] == [
        {
            "message": "Access denied",
            "locations": [{"line": 1, "column": 3}],
            "path": ["alias", 0] if as_list else ["alias"],
            "extensions": {"code": "FORBIDDEN"},
        }
    ]
