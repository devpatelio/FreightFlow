import json
from flask import Blueprint, jsonify, request, g

from ..auth import require_auth
from ..services import supabase_service as db

bp = Blueprint('schemas', __name__, url_prefix='/api/schemas')


@bp.route('', methods=['GET'])
@require_auth
def list_schemas():
    schemas = db.list_form_schemas(g.org_id)
    return jsonify(schemas)


@bp.route('/by-name/<template_name>', methods=['GET'])
@require_auth
def get_schema_by_name(template_name: str):
    schema = db.get_form_schema(g.org_id, template_name)
    if not schema:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Schema not found'}}), 404
    return jsonify(schema)


@bp.route('/<schema_id>', methods=['GET'])
@require_auth
def get_schema(schema_id: str):
    schema = db.get_form_schema_by_id(g.org_id, schema_id)
    if not schema:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Schema not found'}}), 404

    # Resolve the linked template's PDF URL if available
    template_name = schema.get('template_name', '')
    templates = db.get_pdf_templates(g.org_id)
    pdf_url = None
    for t in templates:
        if t.get('name') == template_name and t.get('storage_path'):
            try:
                pdf_url = db.create_signed_url(db.BUCKET_TEMPLATES, t['storage_path'])
            except Exception:
                pass
            break

    result = {**schema, 'pdf_url': pdf_url}
    return jsonify(result)


@bp.route('', methods=['POST'])
@require_auth
def create_schema():
    data = request.get_json()

    template_name = data.get('template_name')
    schema_fields = data.get('schema')
    if not template_name or not schema_fields:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'template_name and schema are required'}}), 400

    if isinstance(schema_fields, str):
        try:
            schema_fields = json.loads(schema_fields)
        except json.JSONDecodeError:
            return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'schema must be valid JSON'}}), 400

    payload = {
        'template_name': template_name,
        'schema': schema_fields,
        'num_fields': len(schema_fields) if isinstance(schema_fields, list) else None,
        'description': data.get('description'),
    }

    schema = db.create_form_schema(g.org_id, payload)
    return jsonify(schema), 201


@bp.route('/<schema_id>', methods=['PATCH'])
@require_auth
def update_schema(schema_id: str):
    data = request.get_json()
    allowed = {'schema', 'description', 'template_name'}
    updates = {k: v for k, v in data.items() if k in allowed}

    if 'schema' in updates:
        if isinstance(updates['schema'], str):
            try:
                updates['schema'] = json.loads(updates['schema'])
            except json.JSONDecodeError:
                return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'schema must be valid JSON'}}), 400
        if isinstance(updates['schema'], list):
            updates['num_fields'] = len(updates['schema'])

    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No valid fields to update'}}), 400

    schema = db.update_form_schema(g.org_id, schema_id, updates)
    if not schema:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Schema not found'}}), 404
    return jsonify(schema)


@bp.route('/<schema_id>', methods=['DELETE'])
@require_auth
def delete_schema(schema_id: str):
    db.delete_form_schema(g.org_id, schema_id)
    return jsonify({'ok': True})
