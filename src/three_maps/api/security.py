from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import os

from fastapi import HTTPException, Request

MAX_REQUESTED_MAPS = 3
ALLOWED_MAPS = frozenset({'ASTROLOGY', 'NUMEROLOGY', 'PALMISTRY'})
MAX_NAME_LENGTH = 200
MAX_ANALYSIS_ID_LENGTH = 64

@dataclass(frozen=True)
class SecurityPolicy:
    max_body_bytes: int = 1_000_000
    max_name_length: int = MAX_NAME_LENGTH
    max_requested_maps: int = MAX_REQUESTED_MAPS
    auth_required: bool = True


def validate_requested_maps(values: Iterable[str], policy: SecurityPolicy = SecurityPolicy()) -> list[str]:
    normalized = [str(v).upper() for v in values]
    if len(normalized) > policy.max_requested_maps:
        raise HTTPException(status_code=422, detail='Too many requested maps')
    if len(set(normalized)) != len(normalized):
        raise HTTPException(status_code=422, detail='Duplicate requested maps are not allowed')
    unknown = sorted(set(normalized) - ALLOWED_MAPS)
    if unknown:
        raise HTTPException(status_code=422, detail=f'Unsupported map: {unknown[0]}')
    return normalized


def validate_name(name: str | None, policy: SecurityPolicy = SecurityPolicy()) -> str | None:
    if name is None:
        return None
    if len(name) > policy.max_name_length:
        raise HTTPException(status_code=422, detail='Name exceeds maximum length')
    return name


def validate_analysis_id(analysis_id: str) -> str:
    if len(analysis_id) > MAX_ANALYSIS_ID_LENGTH or not analysis_id.startswith('ANL-'):
        raise HTTPException(status_code=400, detail='Invalid analysis identifier')
    return analysis_id


def _configured_tokens() -> dict[str, str]:
    raw = os.getenv('THE_THREE_MAPS_AUTH_TOKENS', '')
    # Format: token=user_id,token2=user_id2
    result: dict[str, str] = {}
    for item in raw.split(','):
        if '=' in item:
            token, user = item.split('=', 1)
            if token and user:
                result[token] = user
    # Convenience for single-instance deployments (e.g. a Render blueprint's
    # generated secret): one bearer token, mapped to a single principal.
    # Deliberately additive to, never a replacement for, THE_THREE_MAPS_AUTH_TOKENS.
    web_token = os.getenv('THE_THREE_MAPS_WEB_TOKEN', '').strip()
    if web_token:
        result[web_token] = 'web-user'
    return result


def authenticate_request(request: Request) -> str:
    """Resolve a principal from a configured bearer token.

    This is intentionally a provider-neutral boundary. Production deployments
    should place an identity provider in front of this boundary or populate the
    token registry through a secure secret mechanism; tokens are never logged.
    """
    header = request.headers.get('authorization', '')
    if not header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    token = header[7:].strip()
    if not token or len(token) > 4096:
        raise HTTPException(status_code=401, detail='Invalid authentication credentials', headers={'WWW-Authenticate': 'Bearer'})
    configured = _configured_tokens()
    user_id = configured.get(token)
    # Local-only convenience: when running the bundled development server with
    # no configured token registry, accept the documented local development
    # token. This branch is deliberately disabled as soon as any token registry
    # is configured and is never used in production.
    environment = os.getenv('THE_THREE_MAPS_ENV', 'development').lower()
    if user_id is None and not configured and environment == 'development' and token == 'local-dev-token':
        return 'local-dev-user'
    if user_id is None:
        raise HTTPException(status_code=401, detail='Invalid authentication credentials', headers={'WWW-Authenticate': 'Bearer'})
    return user_id
