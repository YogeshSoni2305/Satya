"""
Clerk JWT verification.

Verifies Clerk-issued JWTs without Clerk SDK.
Uses PyJWT + JWKS for RS256 verification.
"""

from functools import lru_cache

import jwt
import requests

from backend.utils.logger import logger


@lru_cache(maxsize=1)
def _fetch_jwks(jwks_url: str) -> dict:
    """Fetch and cache the Clerk JWKS (JSON Web Key Set)."""
    try:
        resp = requests.get(jwks_url, timeout=10)
        resp.raise_for_status()
        logger.debug("Successfully fetched JWKS from {}", jwks_url)
        return resp.json()
    except Exception as e:
        logger.error("Failed to fetch Clerk JWKS from {}: {}", jwks_url, e)
        raise ValueError(f"Cannot fetch JWKS: {e}") from e


def verify_clerk_token(token: str, jwks_url: str) -> dict:
    """
    Verify a Clerk JWT and return decoded payload.

    Returns dict with at minimum: sub, exp, iat.
    Raises jwt.InvalidTokenError on verification failure.
    """
    jwks_data = _fetch_jwks(jwks_url)

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        logger.warning("Token header missing 'kid'")
        raise jwt.InvalidTokenError("Token header missing 'kid'")

    # Find matching key, retry once on cache miss
    matching_key = _find_key(jwks_data, kid)
    if not matching_key:
        _fetch_jwks.cache_clear()
        jwks_data = _fetch_jwks(jwks_url)
        matching_key = _find_key(jwks_data, kid)

    if not matching_key:
        logger.warning("No matching key found for kid={} in JWKS", kid)
        raise jwt.InvalidTokenError(f"No matching key found for kid={kid}")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(matching_key)

    return jwt.decode(
        token, public_key, algorithms=["RS256"],
        options={"verify_exp": True, "verify_iat": True, "require": ["sub", "exp", "iat"]},
    )


def _find_key(jwks_data: dict, kid: str) -> dict | None:
    """Find a key in JWKS by key ID."""
    for key in jwks_data.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None
