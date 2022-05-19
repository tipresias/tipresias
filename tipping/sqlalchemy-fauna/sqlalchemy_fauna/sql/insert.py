"""Parse INSERT SQL statements into general-purpose query objects."""

from sqlparse import sql as token_groups, tokens as token_types

from sqlalchemy_fauna import exceptions
from . import sql_table, common


def build_insert_table(statement: token_groups.Statement) -> sql_table.Table:
    """Build a Table object from an SQL INSERT query

    Params:
    -------
    statement: A parsed SQL query.

    Returns:
    --------
    A Table object with info on the record to be inserted.
    """
    principal_table = sql_table.Table.extract_principal(statement)

    _, function_group = statement.token_next_by(i=token_groups.Function)

    if function_group is None:
        raise exceptions.NotSupportedError(
            "INSERT INTO statements without column names are not currently supported."
        )

    _, column_name_group = function_group.token_next_by(i=token_groups.Parenthesis)
    _, column_name_identifiers = column_name_group.token_next_by(
        i=(token_groups.IdentifierList, token_groups.Identifier)
    )

    _, value_group = statement.token_next_by(i=token_groups.Values)
    val_idx, column_value_group = value_group.token_next_by(i=token_groups.Parenthesis)

    _, additional_parenthesis_group = value_group.token_next_by(
        i=token_groups.Parenthesis, idx=val_idx
    )
    if additional_parenthesis_group is not None:
        raise exceptions.NotSupportedError(
            "INSERT for multiple rows is not supported yet."
        )

    _, column_value_identifiers = column_value_group.token_next_by(
        i=(token_groups.IdentifierList, token_groups.Identifier),
    )
    # If there's just one value in the VALUES clause, it doesn't get wrapped in an Identifer
    column_value_identifiers = column_value_identifiers or column_value_group

    idx = -1
    columns = []

    for column in sql_table.Column.from_identifier_group(column_name_identifiers):
        idx, column_value = column_value_identifiers.token_next_by(
            t=[token_types.Literal, token_types.Keyword], idx=idx
        )

        if column_value is None:
            raise exceptions.NotSupportedError(
                "Assigning values dynamically is not supported. "
                "You must use literal values only in INSERT statements."
            )

        column.value = common.extract_value(column_value)
        columns.append(column)

    return sql_table.Table(principal_table.name, principal_table.alias, columns=columns)
