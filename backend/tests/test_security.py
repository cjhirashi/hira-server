"""Tests unitarios para core/security.py — bcrypt y JWT (sin Redis)."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_SECONDS,
)
from fastapi import HTTPException


# ── Contraseñas ───────────────────────────────────────────────────────────────

def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("MiContraseña123!")
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    plain = "MiContraseña123!"
    assert verify_password(plain, hash_password(plain)) is True


def test_verify_password_wrong():
    assert verify_password("wrong", hash_password("correct")) is False


def test_hash_is_not_plain():
    plain = "MiContraseña123!"
    assert hash_password(plain) != plain


# ── Access token ──────────────────────────────────────────────────────────────

def test_create_access_token_decodable():
    token = create_access_token(user_id=1, email="admin@hira.local", role="Admin")
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert payload["email"] == "admin@hira.local"
    assert payload["role"] == "Admin"
    assert payload["type"] == "access"


def test_access_token_expiry_present():
    token = create_access_token(user_id=1, email="x@hira.local", role="Visor")
    payload = decode_token(token)
    assert "exp" in payload
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    delta = (exp - iat).total_seconds()
    assert abs(delta - ACCESS_TOKEN_EXPIRE_SECONDS) < 5


def test_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("token.invalido.aqui")
    assert exc_info.value.status_code == 401


def test_decode_tampered_token_raises_401():
    token = create_access_token(user_id=1, email="x@hira.local", role="Admin")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401
