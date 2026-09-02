from __future__ import annotations

from base64 import b64encode

from app.integrations.github.exceptions import GitHubError


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a secret with GitHub's libsodium sealed-box public key."""
    try:
        from nacl import encoding, public
    except ImportError as error:
        raise GitHubError("PyNaCl is required to encrypt GitHub secrets") from error
    key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(key)
    encrypted = sealed.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("ascii")
