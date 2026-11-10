"""API key storage: OS keychain via keyring, falling back to ANTHROPIC_API_KEY."""

from __future__ import annotations

import os

import keyring
from keyring.errors import KeyringError

from rewrite_en import APP_NAME

_USERNAME = "anthropic_api_key"
ENV_VAR = "ANTHROPIC_API_KEY"


class MissingAPIKey(RuntimeError):
    pass


def set_api_key(key: str) -> None:
    key = key.strip()
    if not key:
        raise ValueError("API key is empty")
    keyring.set_password(APP_NAME, _USERNAME, key)


def delete_api_key() -> None:
    try:
        keyring.delete_password(APP_NAME, _USERNAME)
    except KeyringError:
        pass


def get_api_key() -> str:
    """Keychain first, then the environment variable."""
    try:
        key = keyring.get_password(APP_NAME, _USERNAME)
    except KeyringError:
        key = None
    if key:
        return key
    key = os.environ.get(ENV_VAR, "").strip()
    if key:
        return key
    raise MissingAPIKey(
        f"No API key found. Run `rewrite-en set-key` or set {ENV_VAR}."
    )
