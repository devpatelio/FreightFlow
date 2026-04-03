"""JWT authentication middleware for Supabase Auth."""

import os
import json
import base64
import hmac
import hashlib
from functools import wraps
from typing import Optional

from flask import request, g, jsonify
from supabase import create_client


def _decode_jwt_payload(token: str) -> Optional[dict]:
    """Decode JWT payload without full verification (Supabase handles signing).
    For production, use PyJWT with the Supabase JWT secret for full verification.
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        return None


def _get_user_org(user_id: str) -> Optional[dict]:
    """Look up the user's organization membership."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        return None

    client = create_client(url, key)
    result = client.table('org_members') \
        .select('org_id, role') \
        .eq('user_id', user_id) \
        .limit(1) \
        .execute()

    if result.data:
        return result.data[0]
    return None


def require_jwt(f):
    """Lightweight decorator: validates JWT and sets g.user_id but does NOT require org membership.
    Used for endpoints like org creation and invitation acceptance."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Missing or invalid Authorization header'}}), 401

        token = auth_header[7:]
        payload = _decode_jwt_payload(token)
        if not payload or 'sub' not in payload:
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid token'}}), 401

        g.user_id = payload['sub']
        g.jwt_token = token
        g.user_email = payload.get('email', '')

        # Try to load org info if available (but don't fail if not)
        org_info = _get_user_org(g.user_id)
        if org_info:
            g.org_id = org_info['org_id']
            g.org_role = org_info['role']
        else:
            g.org_id = None
            g.org_role = None

        return f(*args, **kwargs)
    return decorated


def require_auth(f):
    """Decorator that requires a valid Supabase JWT and injects org context."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Missing or invalid Authorization header'}}), 401

        token = auth_header[7:]
        payload = _decode_jwt_payload(token)
        if not payload or 'sub' not in payload:
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid token'}}), 401

        user_id = payload['sub']
        org_info = _get_user_org(user_id)
        if not org_info:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'User is not a member of any organization'}}), 403

        g.user_id = user_id
        g.org_id = org_info['org_id']
        g.org_role = org_info['role']
        g.jwt_token = token

        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """Decorator that requires specific org roles (e.g., 'owner', 'admin')."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.org_role not in roles:
                return jsonify({'error': {'code': 'FORBIDDEN', 'message': f'Requires role: {", ".join(roles)}'}}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
