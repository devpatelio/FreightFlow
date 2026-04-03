import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from pydantic import ValidationError

from ..auth import require_auth
from ..models.types import TemplateCreate
from ..services import supabase_service as db

bp = Blueprint('templates', __name__, url_prefix='/api/templates')


@bp.route('', methods=['GET'])
@require_auth
def list_templates():
    templates = db.list_templates(g.org_id)
    return jsonify(templates)


@bp.route('/<template_id>', methods=['GET'])
@require_auth
def get_template(template_id: str):
    template = db.get_template(g.org_id, template_id)
    if not template:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Template not found'}}), 404
    return jsonify(template)


@bp.route('', methods=['POST'])
@require_auth
def create_template():
    try:
        body = TemplateCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400

    template = db.create_template(g.org_id, body.model_dump(exclude_none=True))
    return jsonify(template), 201


@bp.route('/upload', methods=['POST'])
@require_auth
def upload_pdf_template():
    """Upload a PDF file as a template (BOL form, Packing Slip form, etc.)."""
    if 'file' not in request.files:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No file provided'}}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'File must be a PDF'}}), 400

    name = request.form.get('name', '').strip()
    if not name:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'name is required'}}), 400

    description = request.form.get('description', '').strip() or None
    linked_prompt_id = request.form.get('linked_prompt_id', '').strip() or None
    document_type = request.form.get('document_type', '').strip() or None

    unique_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    storage_path = f"{g.org_id}/templates/{unique_name}"

    file_data = file.read()
    db.upload_file(
        bucket=db.BUCKET_TEMPLATES,
        file_path=storage_path,
        file_data=file_data,
        content_type='application/pdf',
    )

    data = {
        'name': name,
        'template_type': 'pdf',
        'storage_path': storage_path,
        'description': description,
    }
    if linked_prompt_id:
        data['linked_prompt_id'] = linked_prompt_id
    if document_type:
        data['document_type'] = document_type

    template = db.create_template(g.org_id, data)
    return jsonify(template), 201


@bp.route('/<template_id>', methods=['PATCH'])
@require_auth
def update_template(template_id: str):
    data = request.get_json()
    allowed = {'name', 'content', 'description', 'is_active', 'linked_prompt_id', 'document_type'}
    updates = {k: v for k, v in data.items() if k in allowed}

    if not updates:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No valid fields to update'}}), 400

    template = db.update_template(g.org_id, template_id, updates)
    if not template:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Template not found'}}), 404
    return jsonify(template)


@bp.route('/<template_id>', methods=['DELETE'])
@require_auth
def delete_template(template_id: str):
    db.delete_template(g.org_id, template_id)
    return jsonify({'ok': True})
