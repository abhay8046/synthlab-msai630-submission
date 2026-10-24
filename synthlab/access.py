"""Minimal generation access check for both Streamlit Cloud and Railway.

Fail closed: with no configured password, every public app is read-only.
"""
from __future__ import annotations
import hmac

def can_generate(*, configured_password: str | None, supplied_password: str | None,
                 has_api_credentials: bool) -> bool:
    if not has_api_credentials:
        return False
    expected = (configured_password or "").strip()
    provided = supplied_password or ""
    if not expected or not provided:
        return False
    return hmac.compare_digest(expected, provided)
