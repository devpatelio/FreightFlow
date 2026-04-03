from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError

from ..auth import require_auth
from ..models.types import AddressCreate, AddressUpdate
from ..services import supabase_service as db

bp = Blueprint('addresses', __name__, url_prefix='/api/addresses')


@bp.route('', methods=['GET'])
@require_auth
def list_addresses():
    customer_id = request.args.get('customer_id')
    addresses = db.list_addresses(g.org_id, customer_id=customer_id)
    return jsonify(addresses)


@bp.route('/<address_id>', methods=['GET'])
@require_auth
def get_address(address_id: str):
    address = db.get_address(g.org_id, address_id)
    if not address:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Address not found'}}), 404
    return jsonify(address)


@bp.route('', methods=['POST'])
@require_auth
def create_address():
    try:
        body = AddressCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    address = db.create_address(g.org_id, body.model_dump(exclude_none=True))
    return jsonify(address), 201


@bp.route('/<address_id>', methods=['PATCH'])
@require_auth
def update_address(address_id: str):
    try:
        body = AddressUpdate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No fields to update'}}), 400

    address = db.update_address(g.org_id, address_id, updates)
    if not address:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Address not found'}}), 404
    return jsonify(address)


@bp.route('/<address_id>', methods=['DELETE'])
@require_auth
def delete_address(address_id: str):
    if not db.delete_address(g.org_id, address_id):
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Address not found'}}), 404
    return jsonify({'message': 'Address deleted'}), 200
