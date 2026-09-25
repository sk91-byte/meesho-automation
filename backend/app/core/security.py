import os
import base64
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import jwt, JWTError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash (truncated to 72 bytes max for bcrypt safety)."""
    if not plain_password or not hashed_password:
        return False
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create a JWT access token with expiration and claims."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc)
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def get_encryption_key_bytes() -> bytes:
    """Derive or parse 32-byte key for AES-256-GCM encryption."""
    raw_key = settings.ENCRYPTION_KEY
    if len(raw_key) == 64:  # Hex-encoded 32 bytes
        return bytes.fromhex(raw_key)
    key_bytes = raw_key.encode("utf-8")
    if len(key_bytes) < 32:
        return key_bytes.ljust(32, b"0")
    return key_bytes[:32]


def encrypt_token(plain_token: str) -> str:
    """Encrypt sensitive tokens (e.g., Meta Access Tokens) using AES-256-GCM."""
    if not plain_token:
        return ""
    key = get_encryption_key_bytes()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plain_token.encode("utf-8"), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt AES-256-GCM encrypted tokens."""
    if not encrypted_token:
        return ""
    try:
        key = get_encryption_key_bytes()
        aesgcm = AESGCM(key)
        combined = base64.b64decode(encrypted_token.encode("utf-8"))
        nonce = combined[:12]
        ciphertext = combined[12:]
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        raise ValueError("Failed to decrypt token: Invalid key or corrupted payload") from e
