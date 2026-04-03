"""User profile routes."""

from flask import Blueprint, jsonify, request, g

from ..auth import require_jwt
from ..services import supabase_service as db

bp = Blueprint('profiles', __name__, url_prefix='/api/profile')


@bp.route('/me', methods=['GET'])
@require_jwt
def get_my_profile():
    profile = db.get_user_profile(g.user_id)
    return jsonify(profile or {'user_id': g.user_id, 'display_name': None, 'avatar_url': None})


@bp.route('/me', methods=['PATCH'])
@require_jwt
def update_my_profile():
    data = request.get_json()
    allowed = {'display_name', 'avatar_url'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No valid fields'}}), 400

    profile = db.upsert_user_profile(g.user_id, updates)
    return jsonify(profile)


@bp.route('/resolve', methods=['POST'])
@require_jwt
def resolve_profiles():
    """Resolve a list of user_ids to display names and avatars."""
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({})

    profiles = db.get_user_profiles_by_ids(user_ids)
    result = {p['user_id']: p for p in profiles}
    return jsonify(result)
