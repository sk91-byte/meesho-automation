import pytest
from datetime import timedelta
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    encrypt_token,
    decrypt_token
)


def test_password_hashing_and_verification():
    raw_password = "SecretPassword123!"
    hashed = get_password_hash(raw_password)
    
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_generation_and_decoding():
    subject = "usr_123456"
    extra_claims = {"role": "OWNER", "email": "test@example.com"}
    
    token = create_access_token(subject=subject, extra_claims=extra_claims)
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == subject
    assert decoded["role"] == "OWNER"
    assert decoded["email"] == "test@example.com"


def test_jwt_invalid_token():
    assert decode_token("invalid_token_string") is None


def test_aes_gcm_token_encryption_and_decryption():
    raw_access_token = "IGQVJ...MetaInstagramAccessTokenString123456789"
    encrypted = encrypt_token(raw_access_token)
    
    assert encrypted != raw_access_token
    assert len(encrypted) > 0
    
    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_access_token


def test_aes_gcm_decryption_failure():
    with pytest.raises(ValueError):
        decrypt_token("corrupted_base64_payload==")
