from __future__ import annotations

import hashlib
import hmac
import os
from typing import Tuple


DEFAULT_ALGO = "sha256"


def _hash(password: str, salt: bytes, algo: str = DEFAULT_ALGO) -> str:
    h = hashlib.new(algo)
    h.update(salt)
    h.update(password.encode("utf-8"))
    return h.hexdigest()


def hash_password(password: str, *, algo: str = DEFAULT_ALGO, salt_bytes: int = 16) -> str:
    """Hash a password with a random salt. Format: "<algo>$<hex_salt>$<hex_hash>".

    This is a minimal implementation for demo/tests; not intended for production-grade security.
    """
    salt = os.urandom(salt_bytes)
    digest = _hash(password, salt, algo)
    return f"{algo}${salt.hex()}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, hex_salt, digest = password_hash.split("$")
        salt = bytes.fromhex(hex_salt)
    except Exception:
        return False
    actual = _hash(password, salt, algo)
    return hmac.compare_digest(actual, digest)
