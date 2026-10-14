import json

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.strip()
    if not key:
        raise RuntimeError("ENCRYPTION_KEY must be configured before using encrypted patient data.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("ENCRYPTION_KEY must be a valid Fernet key.") from exc


def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Encrypted patient data could not be decrypted with ENCRYPTION_KEY.") from exc


class EncryptedText(TypeDecorator[str]):
    """Transparent Fernet encryption for patient strings stored as text."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_text(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return decrypt_text(value)


class EncryptedJSONList(TypeDecorator[list[str]]):
    """Encrypt a JSON list as opaque text at rest."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: list[str] | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")))

    def process_result_value(self, value: str | None, dialect) -> list[str] | None:
        if value is None:
            return None
        try:
            decoded = json.loads(decrypt_text(value))
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("Encrypted allergy data is not a valid JSON list.") from exc
        if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
            raise RuntimeError("Encrypted allergy data must contain a list of strings.")
        return decoded
