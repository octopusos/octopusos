"""Feishu/Lark event crypto utilities (decrypt + signature verify).

Implements the official Feishu event encryption algorithm:
- Request JSON may contain {"encrypt": "<base64>"} when encryption is enabled.
- Decrypt: base64 decode -> iv(16) + ciphertext -> AES-256-CBC with key=SHA256(encrypt_key).

Signature verification:
- If X-Lark-Signature headers are present, validate with HMAC-SHA256 using key=SHA256(encrypt_key)
  over: timestamp + nonce + request_body (bytes) as defined by Feishu.

This module is intentionally narrow: it does not parse business events.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


def _sha256_bytes(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def decrypt_event_payload(*, encrypt_key: str, encrypt_b64: str) -> str:
    """Decrypt Feishu encrypted payload and return plaintext JSON string."""
    raw = base64.b64decode(encrypt_b64)
    if len(raw) < 17:
        raise ValueError("encrypt_payload_too_short")
    iv = raw[:16]
    ciphertext = raw[16:]
    key = _sha256_bytes(encrypt_key)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = dec.update(ciphertext) + dec.finalize()

    unpadder = PKCS7(algorithms.AES.block_size).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return plain.decode("utf-8")


def verify_request_signature(
    *,
    encrypt_key: str,
    timestamp: str,
    nonce: str,
    body_bytes: bytes,
    signature_hex: str,
) -> bool:
    """Verify Feishu X-Lark-Signature.

    Feishu signature: hex(HMAC_SHA256(key=SHA256(encrypt_key), msg=timestamp+nonce+body)).
    """
    key = _sha256_bytes(encrypt_key)
    msg = (timestamp + nonce).encode("utf-8") + body_bytes
    digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
    # constant-time compare
    return hmac.compare_digest(digest, signature_hex or "")


def maybe_verify_signature(
    *,
    encrypt_key: Optional[str],
    timestamp: Optional[str],
    nonce: Optional[str],
    signature_hex: Optional[str],
    body_bytes: bytes,
) -> bool:
    """Best-effort signature verify.

    Returns True if:
    - No signature headers present (can't verify; caller should still verify token), OR
    - Signature headers present and verification succeeds.
    """
    if not signature_hex:
        return True
    if not (encrypt_key and timestamp and nonce):
        return False
    return verify_request_signature(
        encrypt_key=encrypt_key,
        timestamp=str(timestamp),
        nonce=str(nonce),
        body_bytes=body_bytes,
        signature_hex=str(signature_hex),
    )

