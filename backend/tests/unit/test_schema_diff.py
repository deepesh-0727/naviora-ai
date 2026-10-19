from sqlalchemy import Column, Integer, MetaData, Table

from app.db.schema_diff import compare_columns


def test_schema_diff_reports_missing_columns():
    metadata = MetaData()
    Table("appointments", metadata, Column("id", Integer), Column("cancelled_at", Integer))

    differences = compare_columns(
        metadata.tables,
        {"appointments": {"id": {"data_type": "integer", "character_maximum_length": None}}},
    )

    assert differences == ["appointments.cancelled_at: column missing from database"]


def test_schema_diff_reports_type_mismatches():
    metadata = MetaData()
    Table("audit_logs", metadata, Column("id", Integer))

    differences = compare_columns(
        metadata.tables,
        {"audit_logs": {"id": {"data_type": "bigint", "character_maximum_length": None}}},
    )

    assert differences == ["audit_logs.id: model expects integer, database has bigint"]
