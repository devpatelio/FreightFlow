from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError

from ..auth import require_auth
from ..models.types import ProductCreate, ProductUpdate
from ..services import supabase_service as db

bp = Blueprint('products', __name__, url_prefix='/api/products')


@bp.route('', methods=['GET'])
@require_auth
def list_products():
    products = db.list_products(g.org_id)
    return jsonify(products)


@bp.route('/<product_id>', methods=['GET'])
@require_auth
def get_product(product_id: str):
    product = db.get_product(g.org_id, product_id)
    if not product:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Product not found'}}), 404
    return jsonify(product)


@bp.route('', methods=['POST'])
@require_auth
def create_product():
    try:
        body = ProductCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    product = db.create_product(g.org_id, body.model_dump(exclude_none=True))
    return jsonify(product), 201


@bp.route('/<product_id>', methods=['PATCH'])
@require_auth
def update_product(product_id: str):
    try:
        body = ProductUpdate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No fields to update'}}), 400

    product = db.update_product(g.org_id, product_id, updates)
    if not product:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Product not found'}}), 404
    return jsonify(product)


@bp.route('/<product_id>', methods=['DELETE'])
@require_auth
def delete_product(product_id: str):
    if not db.delete_product(g.org_id, product_id):
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Product not found'}}), 404
    return jsonify({'message': 'Product deleted'}), 200
