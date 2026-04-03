from datetime import datetime

from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError

from ..auth import require_auth, require_jwt, require_role
from ..models.types import ApiKeyCreate, InvitationCreate, OrgCreate
from ..services import supabase_service as db

bp = Blueprint('organizations', __name__, url_prefix='/api/organizations')


# ── Org CRUD ──────────────────────────────────────────────────────────────

@bp.route('/me', methods=['GET'])
@require_jwt
def get_my_org():
    """Get the current user's org + role. Returns 200 with org_id=null if no membership."""
    if not g.org_id:
        return jsonify({'org_id': None, 'role': None, 'organization': None})

    org = db.get_organization(g.org_id)
    return jsonify({
        'org_id': g.org_id,
        'role': g.org_role,
        'organization': org,
    })


@bp.route('', methods=['POST'])
@require_jwt
def create_org():
    """Create a new organization. The current user becomes the owner."""
    if g.org_id:
        return jsonify({'error': {'code': 'CONFLICT', 'message': 'You already belong to an organization'}}), 409

    try:
        body = OrgCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    try:
        org = db.create_organization(body.name, body.slug)
        db.add_org_member(org['id'], g.user_id, 'owner')
        return jsonify(org), 201
    except Exception as e:
        msg = str(e)
        if 'duplicate' in msg.lower() or '23505' in msg:
            return jsonify({'error': {'code': 'CONFLICT', 'message': 'An organization with that slug already exists'}}), 409
        return jsonify({'error': {'code': 'CREATE_ERROR', 'message': msg}}), 500


@bp.route('', methods=['PATCH'])
@require_auth
@require_role('owner', 'admin')
def update_org():
    """Update org name/settings."""
    data = request.get_json()
    allowed = {'name', 'settings'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No valid fields'}}), 400

    org = db.update_organization(g.org_id, updates)
    return jsonify(org)


@bp.route('/complete-onboarding', methods=['POST'])
@require_auth
def complete_onboarding():
    """Mark onboarding as completed."""
    org = db.update_organization(g.org_id, {
        'onboarding_completed_at': datetime.utcnow().isoformat(),
    })
    return jsonify(org)


# ── Stats ─────────────────────────────────────────────────────────────────

@bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    stats = db.get_statistics(g.org_id)
    return jsonify(stats)


# ── Members ───────────────────────────────────────────────────────────────

@bp.route('/members', methods=['GET'])
@require_auth
def list_members():
    members = db.list_org_members(g.org_id)
    return jsonify(members)


@bp.route('/members/<member_id>', methods=['PATCH'])
@require_auth
@require_role('owner')
def update_member(member_id: str):
    """Change a member's role."""
    data = request.get_json()
    role = data.get('role')
    if role not in ('owner', 'admin', 'member'):
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'Invalid role'}}), 400

    updated = db.update_org_member(g.org_id, member_id, {'role': role})
    if not updated:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Member not found'}}), 404
    return jsonify(updated)


@bp.route('/members/<member_id>', methods=['DELETE'])
@require_auth
@require_role('owner')
def remove_member(member_id: str):
    db.remove_org_member(g.org_id, member_id)
    return jsonify({'ok': True})


# ── Invitations ───────────────────────────────────────────────────────────

@bp.route('/invitations', methods=['GET'])
@require_auth
def list_invitations():
    invitations = db.list_invitations(g.org_id)
    return jsonify(invitations)


@bp.route('/invitations/pending', methods=['GET'])
@require_jwt
def get_pending_invitations():
    """Get pending invitations for the current user's email (used during onboarding)."""
    invitations = db.get_pending_invitations_for_email(g.user_email)
    return jsonify(invitations)


@bp.route('/invitations', methods=['POST'])
@require_auth
@require_role('owner', 'admin')
def create_invitation():
    try:
        body = InvitationCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    try:
        invitation = db.create_invitation(g.org_id, body.email, body.role, g.user_id)
        return jsonify(invitation), 201
    except Exception as e:
        return jsonify({'error': {'code': 'INVITE_ERROR', 'message': str(e)}}), 500


@bp.route('/invitations/<invitation_id>/accept', methods=['POST'])
@require_jwt
def accept_invitation(invitation_id: str):
    """Accept a pending invitation. Creates org_members row."""
    try:
        invitation = db.accept_invitation(invitation_id, g.user_id)
        return jsonify({'ok': True, 'org_id': invitation['org_id']})
    except ValueError as e:
        return jsonify({'error': {'code': 'INVITE_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        msg = str(e)
        if 'duplicate' in msg.lower() or '23505' in msg:
            return jsonify({'error': {'code': 'CONFLICT', 'message': 'Already a member of this organization'}}), 409
        return jsonify({'error': {'code': 'INVITE_ERROR', 'message': msg}}), 500


@bp.route('/invitations/<invitation_id>', methods=['DELETE'])
@require_auth
@require_role('owner', 'admin')
def revoke_invitation(invitation_id: str):
    db.delete_invitation(g.org_id, invitation_id)
    return jsonify({'ok': True})


# ── API Key Management ─────────────────────────────────────────────────────

@bp.route('/keys', methods=['GET'])
@require_auth
@require_role('owner', 'admin')
def list_api_keys():
    keys = db.list_api_keys(g.org_id)
    return jsonify(keys)


@bp.route('/keys', methods=['POST'])
@require_auth
@require_role('owner', 'admin')
def upsert_api_key():
    try:
        body = ApiKeyCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    key_hint = body.key[-4:]

    db.upsert_api_key(
        org_id=g.org_id,
        provider=body.provider,
        encrypted_key=body.key,
        key_hint=key_hint,
        user_id=g.user_id
    )

    return jsonify({
        'provider': body.provider,
        'key_hint': key_hint,
        'message': f'{body.provider} API key saved'
    }), 200


@bp.route('/keys/validate', methods=['POST'])
@require_auth
@require_role('owner', 'admin')
def validate_api_key():
    """Validate an API key by making a test API call."""
    try:
        body = ApiKeyCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    if body.provider == 'openai':
        try:
            from openai import OpenAI
            client = OpenAI(api_key=body.key)
            client.models.list()
            return jsonify({'valid': True, 'provider': 'openai'})
        except Exception as e:
            return jsonify({'valid': False, 'provider': 'openai', 'error': str(e)}), 400

    elif body.provider == 'reducto':
        try:
            from reducto import Reducto
            Reducto(api_key=body.key)
            return jsonify({'valid': True, 'provider': 'reducto'})
        except Exception as e:
            return jsonify({'valid': False, 'provider': 'reducto', 'error': str(e)}), 400

    return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': f'Unknown provider: {body.provider}'}}), 400
