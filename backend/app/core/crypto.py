"""Transparent at-rest encryption for sensitive columns using Postgres pgcrypto.

`EncryptedSecret` is a SQLAlchemy type that encrypts on write and decrypts on
read via `pgp_sym_encrypt` / `pgp_sym_decrypt`, keyed by `settings.ENCRYPTION_KEY`.

The ciphertext is base64-encoded and stored in a TEXT column, which keeps the
column portable (no bytea bind-type issues) and lets the type degrade to plain
storage when `ENCRYPTION_KEY` is unset (local dev / tests) — in that mode it
emits no pgcrypto SQL, so it also works on engines without pgcrypto (SQLite).

Requires the pgcrypto extension on PostgreSQL (created by migration 008).
"""
from sqlalchemy import Text, func
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


class EncryptedSecret(TypeDecorator):
    impl = Text
    cache_ok = True

    def bind_expression(self, bindvalue):
        if settings.ENCRYPTION_KEY:
            return func.encode(
                func.pgp_sym_encrypt(bindvalue, settings.ENCRYPTION_KEY), "base64"
            )
        return bindvalue

    def column_expression(self, col):
        if settings.ENCRYPTION_KEY:
            return func.pgp_sym_decrypt(func.decode(col, "base64"), settings.ENCRYPTION_KEY)
        return col
