from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text

from app.core.encryption import EncryptedJSONList, EncryptedText
from conftest import _engine


async def test_patient_pii_columns_are_encrypted_in_database():
    metadata = MetaData()
    table = Table(
        "pii_encryption_verification",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", EncryptedText(), nullable=False),
        Column("allergies", EncryptedJSONList(), nullable=False),
    )
    name = "Encryption verification"
    allergies = ["value stored only in the isolated test database"]

    async with _engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
        try:
            await connection.execute(
                insert(table).values(id=1, name=name, allergies=allergies)
            )
            stored_name = await connection.scalar(
                text("SELECT name FROM pii_encryption_verification WHERE id = 1")
            )
            stored_allergies = await connection.scalar(
                text("SELECT allergies FROM pii_encryption_verification WHERE id = 1")
            )
            decrypted = await connection.execute(
                select(table.c.name, table.c.allergies).where(table.c.id == 1)
            )
            decrypted_name, decrypted_allergies = decrypted.one()

            assert stored_name != name
            assert allergies[0] not in stored_allergies
            assert decrypted_name == name
            assert decrypted_allergies == allergies
        finally:
            await connection.run_sync(metadata.drop_all)
