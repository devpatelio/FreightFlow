from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError

from ..auth import require_auth
from ..models.types import SellerProfileCreate, SellerProfileUpdate
from ..services import supabase_service as db

bp = Blueprint('sellers', __name__, url_prefix='/api/sellers')


@bp.route('', methods=['GET'])
@require_auth
def list_seller_profiles():
    profiles = db.list_seller_profiles(g.org_id)
    return jsonify(profiles)


@bp.route('/default', methods=['GET'])
@require_auth
def get_default_seller():
    profile = db.get_default_seller_profile(g.org_id)
    if not profile:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'No seller profile found'}}), 404
    return jsonify(profile)


@bp.route('', methods=['POST'])
@require_auth
def create_seller_profile():
    try:
        body = SellerProfileCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    profile = db.create_seller_profile(g.org_id, body.model_dump(exclude_none=True))
    return jsonify(profile), 201


@bp.route('/<profile_id>', methods=['PATCH'])
@require_auth
def update_seller_profile(profile_id: str):
    try:
        body = SellerProfileUpdate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No fields to update'}}), 400

    profile = db.update_seller_profile(g.org_id, profile_id, updates)
    if not profile:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Seller profile not found'}}), 404
    return jsonify(profile)


@bp.route('/<profile_id>', methods=['DELETE'])
@require_auth
def delete_seller_profile(profile_id: str):
    if not db.delete_seller_profile(g.org_id, profile_id):
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Seller profile not found'}}), 404
    return jsonify({'message': 'Seller profile deleted'}), 200
