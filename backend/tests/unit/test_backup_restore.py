import json
import tarfile
from cryptography.fernet import Fernet
import pytest

from scripts.backup_restore import (
    BackupRestoreError,
    decrypt_archive,
    encrypt_archive,
    _ensure_scratch_database_target,
    _read_archive,
    postgres_connection,
    redis_connection,
)
from scripts import backup_restore


def test_postgres_url_is_converted_without_exposing_password_in_arguments():
    database, environment = postgres_connection(
        "postgresql+asyncpg://app-user:p%40ss%3Aword@db.example.invalid:6543/naviora?sslmode=require"
    )

    assert database == "naviora"
    assert environment["PGHOST"] == "db.example.invalid"
    assert environment["PGPORT"] == "6543"
    assert environment["PGUSER"] == "app-user"
    assert environment["PGPASSWORD"] == "p@ss:word"
    assert environment["PGSSLMODE"] == "require"


def test_postgres_url_rejects_non_postgresql_scheme():
    with pytest.raises(BackupRestoreError, match="PostgreSQL scheme"):
        postgres_connection("sqlite:///tmp/dev.db")


def test_remote_restore_target_requires_explicit_scratch_override(monkeypatch):
    with pytest.raises(BackupRestoreError, match="Remote restore targets are disabled"):
        _ensure_scratch_database_target("naviora_scratch", {"PGHOST": "db.example.invalid"})

    monkeypatch.setenv("RESTORE_ALLOW_REMOTE", "YES")
    _ensure_scratch_database_target("naviora_scratch", {"PGHOST": "db.example.invalid"})


def test_postgres_system_database_is_never_a_restore_target():
    with pytest.raises(BackupRestoreError, match="system database"):
        _ensure_scratch_database_target("postgres", {"PGHOST": "127.0.0.1"})


def test_redis_url_keeps_auth_out_of_command_arguments():
    args, environment = redis_connection("rediss://default:secret%40value@cache.example.invalid:6380/2")

    assert args == ["--host", "cache.example.invalid", "--port", "6380", "-n", "2", "--tls", "--user", "default"]
    assert "secret@value" not in " ".join(args)
    assert environment["REDISCLI_AUTH"] == "secret@value"


def test_encrypted_archive_round_trip_and_invalid_key_rejection():
    key = Fernet.generate_key()
    plaintext = b"sample archive bytes"

    encrypted = encrypt_archive(plaintext, key)

    assert encrypted != plaintext
    assert decrypt_archive(encrypted, key) == plaintext
    with pytest.raises(BackupRestoreError, match="could not be decrypted"):
        decrypt_archive(encrypted, Fernet.generate_key())


def test_archive_reader_validates_and_reads_expected_members(tmp_path):
    key = Fernet.generate_key()
    tar_path = tmp_path / "plain.tar.gz"
    files = {
        "postgres.sql": b"CREATE TABLE users (id integer);",
        "redis.rdb": b"REDIS0009",
        "manifest.json": json.dumps({
            "format_version": 1,
            "database_row_count": {"table": "public.users", "count": 4},
        }).encode(),
    }
    with tarfile.open(tar_path, "w:gz") as archive:
        for name, content in files.items():
            item = tmp_path / name
            item.write_bytes(content)
            archive.add(item, arcname=name)
    encrypted_path = tmp_path / "backup.tar.gz.enc"
    encrypted_path.write_bytes(encrypt_archive(tar_path.read_bytes(), key))

    postgres_path, redis_path, manifest = _read_archive(encrypted_path, key, tmp_path / "unpacked")

    assert postgres_path.read_bytes() == files["postgres.sql"]
    assert redis_path.read_bytes() == files["redis.rdb"]
    assert manifest["database_row_count"]["count"] == 4


def test_backup_cli_exits_nonzero_when_backup_operation_fails(monkeypatch, capsys):
    monkeypatch.setattr(backup_restore, "load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", Fernet.generate_key().decode())

    def fail_utility(name):
        raise BackupRestoreError(f"Required utility '{name}' is unavailable; install it and retry.")

    monkeypatch.setattr(backup_restore, "_utility", fail_utility)

    exit_code = backup_restore.main(["backup"])

    assert exit_code == 1
    assert "Backup/restore failed: Required utility 'pg_dump' is unavailable" in capsys.readouterr().err
