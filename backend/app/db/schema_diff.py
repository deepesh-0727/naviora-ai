"""Read-only comparison between model metadata and public PostgreSQL columns."""

import asyncpg
from sqlalchemy.dialects.postgresql import dialect

from app.core.config import settings
from app.db.base import Base


def _expected_type(column) -> tuple[str, int | None]:
    compiled = column.type.compile(dialect=dialect()).lower()
    length = getattr(column.type, "length", None)
    if compiled.startswith("varchar") or compiled.startswith("character varying"):
        return "character varying", length
    if compiled == "float":
        return "double precision", None
    aliases = {
        "int": "integer",
        "int4": "integer",
        "int8": "bigint",
        "bool": "boolean",
        "timestamp": "timestamp without time zone",
    }
    return aliases.get(compiled, compiled), None


def compare_columns(model_tables, database_columns) -> list[str]:
    """Return missing columns and incompatible types from schema metadata."""
    differences: list[str] = []
    for table_name, table in sorted(model_tables.items()):
        actual = database_columns.get(table_name)
        if actual is None:
            differences.append(f"{table_name}: table missing from public schema")
            continue
        for column in table.columns:
            row = actual.get(column.name)
            if row is None:
                differences.append(f"{table_name}.{column.name}: column missing from database")
                continue
            expected_type, expected_length = _expected_type(column)
            actual_type = row["data_type"].lower()
            actual_length = row["character_maximum_length"]
            compatible_types = {
                ("json", "jsonb"),
                ("jsonb", "json"),
                ("timestamp without time zone", "timestamp with time zone"),
                ("timestamp with time zone", "timestamp without time zone"),
            }
            if (actual_type != expected_type and (expected_type, actual_type) not in compatible_types) or (
                expected_length is not None and actual_length != expected_length
            ):
                expected = expected_type
                if expected_length is not None:
                    expected += f"({expected_length})"
                observed = actual_type
                if actual_length is not None:
                    observed += f"({actual_length})"
                differences.append(
                    f"{table_name}.{column.name}: model expects {expected}, database has {observed}"
                )
    return differences


async def inspect_database() -> list[str]:
    """Inspect public schema inside a read-only transaction."""
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(url, timeout=15)
    try:
        async with connection.transaction(readonly=True):
            rows = await connection.fetch(
                "SELECT table_name, column_name, data_type, character_maximum_length "
                "FROM information_schema.columns WHERE table_schema = 'public'"
            )
        database_columns: dict[str, dict[str, dict]] = {}
        for row in rows:
            database_columns.setdefault(row["table_name"], {})[row["column_name"]] = dict(row)
        return compare_columns(Base.metadata.tables, database_columns)
    finally:
        await connection.close()
