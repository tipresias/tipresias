# sqlalchemy-fauna

A Fauna dialect for SQLAlchemy

## Known Issues & Limitations

- Primary keys of models have to use the `Integer` type in order to leverage the `autoincrement` param (`True` by default) to allow for auto-generated `id`s. However, Fauna returns `id` values as numeric strings. Coercing them to integers breaks `alembic`, which actually expects its numeric strings to remain strings, so I left it as is.
  - Possible solution: the PostGres dialect has a `UUID` data type for string primary keys. I couldn't use it directly, but I might be able to copy it for use with Fauna.

- Alembic's `autogenerate` option for creating migrations doesn't work very well, because it includes a whole bunch of changes that already exist in the schema. I think this has to do with bugs in how the dialect responds to `INFORMATION_SCHEMA` queries. However, the auto-generated migrations include all the desired changes: you just have to delete the undesired ones.
  - Possible solution: investigate what alembic does with the `INFORMATION_SCHEMA` data and maybe fix those responses to match what the equivalent SQL queries return.

- Many valid SQL queries are not supported due to a combination of their being really difficult to make work in Fauna and their use cases not having come up in my own projects. These, in theory, could be supported eventually, and I've tried to mark as many of them as possible with `NotSupported` errors and unit tests.

## TODO

For keeping track of next steps for extending SQL support. Not meant to be comprehensive.

- Support `ON DELETE` strategies for foreign keys (currently is just `SET NULL` I suppose since the ref no longer exists)
- Support `GROUP BY`
