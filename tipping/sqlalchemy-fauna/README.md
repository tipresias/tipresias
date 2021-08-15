# sqlalchemy-fauna

A Fauna dialect for SQLAlchemy

## Known Issues & Limitations

- Primary keys of models have to use the `Integer` type in order to leverage the `autoincrement` param (`True` by default) to allow for auto-generated `id`s. However, Fauna returns `id` values as numeric strings. Coercing them to integers breaks `alembic`, which actually expects its numeric strings to remain strings, so I left it as is.
  - Possible solution: the PostGres dialect has a `UUID` data type for string primary keys. I couldn't use it directly, but I might be able to copy it for use with Fauna.

- Alembic's `autogenerate` option for creating migrations doesn't work very well, because it includes a whole bunch of changes that already exist in the schema. I think this has to do with bugs in how the dialect responds to `INFORMATION_SCHEMA` queries. However, the auto-generated migrations include all the desired changes: you just have to delete the undesired ones.
  - Possible solution: investigate what alembic does with the `INFORMATION_SCHEMA` data and maybe fix those responses to match what the equivalent SQL queries return.

- Queries that refer to multiple tables **must** use `JOIN`s to connect them (`SELECT <columns> FROM <table1>, <table2>` doesn't work, but `SELECT <columns> FROM <table1> JOIN <table2>` does). This includes any cross-table references in the selected columns, `WHERE` clauses, or `ORDER BY` clause.

- Due to how Fauna implements results sorting via matching on indices, there are some limitations on queries with an `ORDER BY` clause:
  - Can only sort by one column per query.
    - Sorting by multiple is probably possible, but would require such a massive increase in the number of Fauna indices as well as extra complication in the query logic, that it doesn't seem worth implementing for now.
  - Works fine for queries that only include one table (i.e. no `JOIN`s)
  - For queries with `JOIN`s, we can only sort by a column from the principal table (i.e. `FROM <table>`), not any of the tables included via `JOIN`s.
    - I'm not sure that sorting on any table in the query is even possible, but if it is, it would require completely changing how `JOIN` queries are implemented, and I had a difficult enough time figuring that out without this extra complexity.

- Many valid SQL queries are not supported due to a combination of their being really difficult to make work in Fauna and their use cases not having come up in my own projects. These, in theory, could be supported eventually, and I've tried to mark as many of them as possible with `NotSupported` errors and unit tests.

## TODO

For keeping track of next steps for extending SQL support. Not meant to be comprehensive.

- Support `LIMIT`
- Support `ON DELETE` strategies for foreign keys (currently is just `SET NULL` I suppose since the ref no longer exists)
- Support `GROUP BY`
