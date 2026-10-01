import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from app.core.config import settings

class AESEncryption:
    """
    Enterprise-grade AES-256 encryption for PII (Personally Identifiable Information).
    """
    def __init__(self):
        # In production, this should be a 32-byte key from a secure vault
        key_str = settings.SECRET_KEY[:32].ljust(32, '0')
        self.key = key_str.encode()
        self.backend = default_backend()

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()

        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        if not ciphertext_b64:
            return ""
        data = base64.b64decode(ciphertext_b64)
        iv = data[:16]
        ciphertext = data[16:]

        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()

        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()

        plaintext = unpadder.update(padded_data) + unpadder.finalize()
        return plaintext.decode()

aes_encryption = AESEncryption()
