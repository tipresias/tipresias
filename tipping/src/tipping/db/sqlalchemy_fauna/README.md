## Known Issues & Limitations

- There are a whole bunch of limitations with regards to what sorts of queries are supported (e.g. can only handle column value conditions for `WHERE` clauses), but I'll more as I go, so it's not really worth listing them all here

- Primary keys of models have to use the `Integer` type in order to leverage the `autoincrement` param (`True` by default) to allow for auto-generated `id`s. However, Fauna returns `id` values as numeric strings. Coercing them to integers breaks `alembic`, which actually expects its numeric strings to remain strings, so I left it as is.
  - Possible solution: the PostGres dialect has a `UUID` data type for string primary keys. I couldn't use it directly, but I might be able to copy it for use with Fauna.

- We can't enforce uniqueness of column values. This depends on `INFORMATION_SCHEMA` queries that we don't support yet. It would also require information that isn't saved on `Collection` objects by default (i.e. they don't have fixed fields, because documents don't follow any schema).
  - Possible solution: The GraphQL interface for Fauna makes heavy use of custom metadata that can be added to collections. The metadata object is open and can contain any data in any shape. This could be used to define rules for valid fields that could then be checked when executing queries to enforce uniqueness, data types, etc.