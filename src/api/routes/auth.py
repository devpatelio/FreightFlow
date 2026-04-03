"""Auth utility routes (password reset, etc.)"""

import os
from flask import Blueprint, jsonify, request
from ..services import supabase_service as db

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/reset-password', methods=['POST'])
def request_password_reset():
    """Send a password reset email with the correct production redirect URL."""
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'Email is required'}}), 400

    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    redirect_to = f"{frontend_url}/auth/callback?next=/reset-password"

    try:
        db._get_client().auth.reset_password_for_email(email, options={'redirect_to': redirect_to})
    except Exception:
        # Don't leak whether the email exists — always return success
        pass

    # Always return success so we don't reveal whether the email exists
    return jsonify({'ok': True})
