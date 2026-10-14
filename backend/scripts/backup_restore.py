"""Encrypted PostgreSQL and Redis backup/restore commands used by platform wrappers."""

import argparse
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
BACKUP_PREFIX = "naviora-backup-"
RETENTION_DAYS = 30


class BackupRestoreError(RuntimeError):
    """Safe-to-display operational error that never contains connection secrets."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise BackupRestoreError(f"Required environment variable {name} is not configured.")
    return value


def postgres_connection(url: str) -> tuple[str, dict[str, str]]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise BackupRestoreError("Database URL is invalid; check its host and port format.") from exc
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg2"}:
        raise BackupRestoreError("Database URL must use a PostgreSQL scheme.")
    if not parsed.hostname or not parsed.path.strip("/"):
        raise BackupRestoreError("Database URL must include a host and database name.")

    connection_env = {
        "PGHOST": parsed.hostname,
        "PGPORT": str(port or 5432),
        "PGDATABASE": unquote(parsed.path.strip("/")),
    }
    if parsed.username:
        connection_env["PGUSER"] = unquote(parsed.username)
    if parsed.password:
        connection_env["PGPASSWORD"] = unquote(parsed.password)
    query = parse_qs(parsed.query)
    for query_name, env_name in (("sslmode", "PGSSLMODE"), ("connect_timeout", "PGCONNECT_TIMEOUT")):
        if query.get(query_name):
            connection_env[env_name] = query[query_name][0]
    return connection_env["PGDATABASE"], connection_env


def redis_connection(url: str) -> tuple[list[str], dict[str, str]]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise BackupRestoreError("Redis URL is invalid; check its host and port format.") from exc
    if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
        raise BackupRestoreError("Redis URL must use redis:// or rediss:// and include a host.")
    try:
        database = int(parsed.path.strip("/") or "0")
    except ValueError as exc:
        raise BackupRestoreError("Redis URL database number must be an integer.") from exc
    if database < 0:
        raise BackupRestoreError("Redis URL database number cannot be negative.")

    args = ["--host", parsed.hostname, "--port", str(port or 6379), "-n", str(database)]
    if parsed.scheme == "rediss":
        args.append("--tls")
    if parsed.username:
        args.extend(["--user", unquote(parsed.username)])
    child_env = {"REDISCLI_AUTH": unquote(parsed.password or "")}
    return args, child_env


def _backup_key() -> bytes:
    key = _required_env("BACKUP_ENCRYPTION_KEY")
    try:
        return key.encode("ascii")
    except (ValueError, UnicodeEncodeError) as exc:
        raise BackupRestoreError("BACKUP_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def _backup_cipher() -> Fernet:
    try:
        return Fernet(_backup_key())
    except ValueError as exc:
        raise BackupRestoreError("BACKUP_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def encrypt_archive(archive_bytes: bytes, key: bytes) -> bytes:
    try:
        return Fernet(key).encrypt(archive_bytes)
    except (ValueError, TypeError) as exc:
        raise BackupRestoreError("Backup encryption key is invalid.") from exc


def decrypt_archive(encrypted_bytes: bytes, key: bytes) -> bytes:
    try:
        return Fernet(key).decrypt(encrypted_bytes)
    except (ValueError, InvalidToken) as exc:
        raise BackupRestoreError("Backup could not be decrypted; verify the archive and backup key.") from exc


def _utility(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise BackupRestoreError(f"Required utility '{name}' is unavailable; install it and retry.")
    return path


def _run(args: list[str], operation: str, env: dict[str, str] | None = None) -> str:
    child_env = os.environ.copy()
    if env:
        if "PGHOST" in env:
            for key in tuple(child_env):
                if key.startswith("PG"):
                    child_env.pop(key, None)
        child_env.update(env)
    try:
        result = subprocess.run(args, env=child_env, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise BackupRestoreError(f"{operation} could not start; verify the required utility is installed.") from exc
    if result.returncode != 0:
        # Do not echo CLI stderr: provider clients can include credentials or connection details.
        raise BackupRestoreError(f"{operation} failed (exit code {result.returncode}); output was suppressed to protect secrets.")
    return result.stdout.strip()


def _database_env(url_name: str) -> tuple[str, dict[str, str]]:
    return postgres_connection(_required_env(url_name))


def _users_count(db_name: str, connection_env: dict[str, str]) -> int:
    output = _run(
        [
            _utility("psql"), "--no-psqlrc", "--tuples-only", "--no-align",
            "--dbname", db_name, "--command", "SELECT count(*) FROM public.users;",
        ],
        "PostgreSQL users row-count query",
        connection_env,
    )
    try:
        return int(output)
    except ValueError as exc:
        raise BackupRestoreError("PostgreSQL users row-count query returned an invalid result.") from exc


def _redis_args(url_name: str = "REDIS_URL") -> tuple[list[str], dict[str, str]]:
    return redis_connection(_required_env(url_name))


def _local_backup_directory() -> Path:
    configured = os.environ.get("BACKUP_DIR", "").strip()
    path = Path(configured).expanduser() if configured else BACKEND_DIR / "backups"
    return path.resolve()


def _backup_s3_uri(filename: str) -> str:
    bucket = _required_env("BACKUP_S3_BUCKET").strip("/")
    prefix = os.environ.get("BACKUP_S3_PREFIX", "").strip("/")
    key = "/".join(part for part in (prefix, filename) if part)
    return f"s3://{bucket}/{key}"


def _prune_local(directory: Path, now: datetime) -> None:
    cutoff = now.timestamp() - RETENTION_DAYS * 86400
    for candidate in directory.glob(f"{BACKUP_PREFIX}*.tar.gz.enc"):
        if candidate.is_file() and candidate.stat().st_mtime < cutoff:
            candidate.unlink()


def _prune_s3(uri: str, now: datetime) -> None:
    listing = _run([_utility("aws"), "s3", "ls", uri], "S3 backup retention listing")
    cutoff = now.astimezone(timezone.utc) - timedelta(days=RETENTION_DAYS)
    base = uri.rstrip("/") + "/"
    for line in listing.splitlines():
        fields = line.split(maxsplit=3)
        if len(fields) != 4 or not fields[2].isdigit():
            continue
        try:
            created = datetime.strptime(f"{fields[0]} {fields[1]}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        key = fields[3]
        if key.startswith(BACKUP_PREFIX) and key.endswith(".tar.gz.enc") and created < cutoff:
            _run([_utility("aws"), "s3", "rm", base + key], "S3 old-backup removal")


def backup() -> str:
    key = _backup_key()
    cipher = _backup_cipher()
    pg_dump = _utility("pg_dump")
    psql = _utility("psql")
    redis_cli = _utility("redis-cli")
    database_name, database_env = _database_env("DATABASE_URL")
    redis_args, redis_env = _redis_args("REDIS_URL")
    now = datetime.now(timezone.utc)
    filename = f"{BACKUP_PREFIX}{now.strftime('%Y%m%dT%H%M%SZ')}.tar.gz.enc"

    with tempfile.TemporaryDirectory(prefix="naviora-backup-") as temp_dir:
        work = Path(temp_dir)
        dump_path = work / "postgres.sql"
        redis_path = work / "redis.rdb"
        tar_path = work / "backup.tar.gz"
        encrypted_path = work / filename

        _run(
            [pg_dump, "--no-owner", "--no-acl", "--format=plain", "--file", str(dump_path), "--dbname", database_name],
            "PostgreSQL backup",
            database_env,
        )
        _run([redis_cli, *redis_args, "--rdb", str(redis_path)], "Redis RDB backup", redis_env)
        if not redis_path.is_file() or redis_path.stat().st_size == 0:
            raise BackupRestoreError("Redis RDB export completed without producing a non-empty snapshot.")
        users_count = _users_count(database_name, database_env)
        manifest = {
            "format_version": 1,
            "created_at_utc": now.isoformat(),
            "database_row_count": {"table": "public.users", "count": users_count},
            "redis_rdb_bytes": redis_path.stat().st_size,
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with tarfile.open(tar_path, "w:gz") as archive:
            for item in (dump_path, redis_path, work / "manifest.json"):
                archive.add(item, arcname=item.name)
        encrypted_path.write_bytes(encrypt_archive(tar_path.read_bytes(), key))

        if os.environ.get("AWS_ACCESS_KEY_ID", "").strip():
            destination = _backup_s3_uri(filename)
            aws_args = [_utility("aws"), "s3", "cp", str(encrypted_path), destination, "--only-show-errors"]
            kms_key = os.environ.get("BACKUP_S3_SSE_KMS_KEY_ID", "").strip()
            if kms_key:
                aws_args.extend(["--sse", "aws:kms", "--sse-kms-key-id", kms_key])
            else:
                aws_args.extend(["--sse", "AES256"])
            _run(aws_args, "S3 backup upload")
            _prune_s3(destination.rsplit("/", 1)[0], now)
            return destination

        destination_dir = _local_backup_directory()
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = destination_dir / filename
        shutil.copy2(encrypted_path, destination_path)
        _prune_local(destination_dir, now)
        return str(destination_path)


def _read_archive(archive_path: Path, key: bytes, work: Path) -> tuple[Path, Path, dict[str, object]]:
    try:
        tar_bytes = decrypt_archive(archive_path.read_bytes(), key)
    except OSError as exc:
        raise BackupRestoreError("Backup archive could not be read.") from exc
    work.mkdir(parents=True, exist_ok=True)
    tar_path = work / "backup.tar.gz"
    tar_path.write_bytes(tar_bytes)
    try:
        with tarfile.open(tar_path, "r:gz") as archive:
            required = {"postgres.sql", "redis.rdb", "manifest.json"}
            members = {Path(member.name).name: member for member in archive.getmembers() if member.isfile()}
            if not required.issubset(members):
                raise BackupRestoreError("Backup archive is missing required PostgreSQL, Redis, or manifest data.")
            postgres_path = work / "postgres.sql"
            redis_path = work / "redis.rdb"
            for name, target in (("postgres.sql", postgres_path), ("redis.rdb", redis_path)):
                stream = archive.extractfile(members[name])
                if stream is None:
                    raise BackupRestoreError(f"Could not read {name} from the backup archive.")
                target.write_bytes(stream.read())
            manifest_stream = archive.extractfile(members["manifest.json"])
            if manifest_stream is None:
                raise BackupRestoreError("Backup manifest could not be read.")
            manifest = json.loads(manifest_stream.read())
    except (OSError, tarfile.TarError, json.JSONDecodeError) as exc:
        raise BackupRestoreError("Backup archive is invalid or damaged.") from exc

    if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
        raise BackupRestoreError("Backup format version is unsupported.")
    row_count = manifest.get("database_row_count")
    if not isinstance(row_count, dict) or row_count.get("table") != "public.users" or not isinstance(row_count.get("count"), int):
        raise BackupRestoreError("Backup manifest has no valid PostgreSQL users row count.")
    return postgres_path, redis_path, manifest


def _ensure_local_redis_stopped(redis_cli: str) -> None:
    url = os.environ.get("REDIS_RESTORE_URL", "redis://127.0.0.1:6379/0")
    args, child_env = redis_connection(url)
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if host != "localhost":
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise BackupRestoreError("Redis restore is local-file-only; REDIS_RESTORE_URL must be loopback.")
        except ValueError as exc:
            raise BackupRestoreError("Redis restore is local-file-only; REDIS_RESTORE_URL must be loopback.") from exc
    command = subprocess.run(
        [redis_cli, *args, "PING"],
        env={**os.environ, **child_env},
        capture_output=True,
        text=True,
        check=False,
    )
    if command.returncode == 0:
        raise BackupRestoreError("Stop the local Redis server before replacing its RDB file.")
    failure = f"{command.stdout}\n{command.stderr}".lower()
    if not any(message in failure for message in ("could not connect to redis", "connection refused", "actively refused")):
        raise BackupRestoreError("Could not confirm local Redis is stopped; refusing to replace the RDB file.")


def _ensure_scratch_database_target(db_name: str, connection_env: dict[str, str]) -> None:
    host = connection_env.get("PGHOST", "")
    try:
        is_loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback and os.environ.get("RESTORE_ALLOW_REMOTE", "").strip() != "YES":
        raise BackupRestoreError(
            "Remote restore targets are disabled by default; use a local scratch DB or explicitly set RESTORE_ALLOW_REMOTE=YES."
        )
    if db_name.lower() in {"postgres", "template0", "template1"}:
        raise BackupRestoreError("Refusing to restore into a PostgreSQL system database.")


def restore(archive_argument: str) -> tuple[int, Path]:
    key = _backup_key()
    _backup_cipher()
    psql = _utility("psql")
    redis_cli = _utility("redis-cli")
    redis_check = _utility("redis-check-rdb")
    database_name, database_env = _database_env("RESTORE_DATABASE_URL")
    _ensure_scratch_database_target(database_name, database_env)
    data_dir_value = _required_env("REDIS_DATA_DIR")
    data_dir = Path(data_dir_value).expanduser().resolve()
    if not data_dir.is_dir():
        raise BackupRestoreError("REDIS_DATA_DIR must point to an existing local Redis data directory.")
    dump_filename = os.environ.get("REDIS_DUMP_FILENAME", "dump.rdb").strip()
    if not dump_filename or Path(dump_filename).name != dump_filename or dump_filename in {".", ".."}:
        raise BackupRestoreError("REDIS_DUMP_FILENAME must be a file name within REDIS_DATA_DIR.")
    destination = (data_dir / dump_filename).resolve()
    if destination.parent != data_dir:
        raise BackupRestoreError("Redis RDB destination must remain inside REDIS_DATA_DIR.")
    try:
        probe = data_dir / f".naviora-restore-probe-{os.getpid()}"
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        raise BackupRestoreError("REDIS_DATA_DIR is not writable by this process.") from exc

    archive_path = Path(archive_argument).expanduser().resolve()
    if not archive_path.is_file():
        raise BackupRestoreError("Backup archive file does not exist.")
    with tempfile.TemporaryDirectory(prefix="naviora-restore-") as temp_dir:
        work = Path(temp_dir)
        postgres_path, redis_path, manifest = _read_archive(archive_path, key, work)
        _run([redis_check, str(redis_path)], "Redis RDB validation")
        _ensure_local_redis_stopped(redis_cli)

        existing_tables = _run(
            [
                psql, "--no-psqlrc", "--tuples-only", "--no-align", "--dbname", database_name,
                "--command", "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'spatial_ref_sys';",
            ],
            "Restore target database preflight",
            database_env,
        )
        if not existing_tables.isdigit() or int(existing_tables) != 0:
            raise BackupRestoreError("Restore target database is not empty; use a dedicated scratch database.")

        _run(
            [psql, "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "--dbname", database_name, "--file", str(postgres_path)],
            "PostgreSQL restore",
            database_env,
        )
        restored_count = _users_count(database_name, database_env)
        expected_count = manifest["database_row_count"]["count"]  # validated by _read_archive
        if restored_count != expected_count:
            raise BackupRestoreError(
                f"PostgreSQL restore row-count verification failed (expected {expected_count}, found {restored_count})."
            )

        staged = data_dir / f".{dump_filename}.restore"
        try:
            shutil.copyfile(redis_path, staged)
            os.replace(staged, destination)
        finally:
            staged.unlink(missing_ok=True)
    return restored_count, destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or restore encrypted Naviora PostgreSQL/Redis backups.")
    parser.add_argument("operation", choices=("backup", "restore"))
    parser.add_argument("archive", nargs="?", help="encrypted backup archive to restore")
    args = parser.parse_args(argv)

    load_dotenv(BACKEND_DIR / ".env", override=False)
    try:
        if args.operation == "backup":
            if args.archive:
                raise BackupRestoreError("The backup operation does not accept an archive argument.")
            print(f"Encrypted backup created: {backup()}")
        else:
            if not args.archive:
                raise BackupRestoreError("Restore requires a local encrypted backup archive path.")
            count, redis_file = restore(args.archive)
            print(f"PostgreSQL restored; public.users row count verified: {count}.")
            print(f"Validated Redis RDB installed at {redis_file}; start Redis and verify service health.")
    except BackupRestoreError as exc:
        print(f"Backup/restore failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
