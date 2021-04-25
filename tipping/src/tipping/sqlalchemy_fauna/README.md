## Known Issues & Limitations

- There are a whole bunch of limitations with regards to what sorts of queries are supported (e.g. can only handle column value conditions for `WHERE` clauses), but I'll more as I go, so it's not really worth listing them all here

- Primary keys of models have to use the `Integer` type in order to leverage the `autoincrement` param (`True` by default) to allow for auto-generated `id`s. However, Fauna returns `id` values as numeric strings. Coercing them to integers breaks `alembic`, which actually expects its numeric strings to remain strings, so I left it as is.
  - Possible solution: the PostGres dialect has a `UUID` data type for string primary keys. I couldn't use it directly, but I might be able to copy it for use with Fauna.

- Alembic's `autogenerate` option for creating migrations doesn't work very well, because it includes a whole bunch of changes that already exist in the schema. I think this has to do with bugs in how the dialect responds to `INFORMATION_SCHEMA` queries. However, the auto-generated migrations include all the desired changes: you just have to delete the undesired ones.
