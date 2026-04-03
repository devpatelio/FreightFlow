from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError

from ..auth import require_auth
from ..models.types import CustomerCreate, CustomerUpdate
from ..services import supabase_service as db

bp = Blueprint('customers', __name__, url_prefix='/api/customers')


@bp.route('', methods=['GET'])
@require_auth
def list_customers():
    customers = db.list_customers(g.org_id)
    return jsonify(customers)


@bp.route('/<customer_id>', methods=['GET'])
@require_auth
def get_customer(customer_id: str):
    customer = db.get_customer(g.org_id, customer_id)
    if not customer:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Customer not found'}}), 404
    return jsonify(customer)


@bp.route('', methods=['POST'])
@require_auth
def create_customer():
    try:
        body = CustomerCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    customer = db.create_customer(g.org_id, body.model_dump(exclude_none=True))
    return jsonify(customer), 201


@bp.route('/<customer_id>', methods=['PATCH'])
@require_auth
def update_customer(customer_id: str):
    try:
        body = CustomerUpdate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No fields to update'}}), 400

    customer = db.update_customer(g.org_id, customer_id, updates)
    if not customer:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Customer not found'}}), 404
    return jsonify(customer)


@bp.route('/<customer_id>', methods=['DELETE'])
@require_auth
def delete_customer(customer_id: str):
    if not db.delete_customer(g.org_id, customer_id):
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Customer not found'}}), 404
    return jsonify({'message': 'Customer deleted'}), 200


@bp.route('/<customer_id>/contacts', methods=['GET'])
@require_auth
def list_contacts(customer_id: str):
    contacts = db.list_contacts(g.org_id, customer_id)
    return jsonify(contacts)


@bp.route('/<customer_id>/contacts', methods=['POST'])
@require_auth
def create_contact(customer_id: str):
    from ..models.types import ContactCreate
    try:
        data = request.get_json()
        data['customer_id'] = customer_id
        body = ContactCreate(**data)
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    contact = db.create_contact(g.org_id, body.model_dump(exclude_none=True))
    return jsonify(contact), 201
