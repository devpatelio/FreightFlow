"""Pipeline definition and run management routes."""

from flask import Blueprint, jsonify, request, g

from ..auth import require_auth
from ..services import supabase_service as db

bp = Blueprint('pipelines', __name__, url_prefix='/api/pipelines')


@bp.route('/definitions', methods=['GET'])
@require_auth
def list_definitions():
    """List pipeline definitions for the org (includes system defaults where org_id IS NULL)."""
    client = db._get_client()
    result = client.table('pipeline_definitions') \
        .select('*') \
        .or_(f'org_id.eq.{g.org_id},org_id.is.null') \
        .order('name') \
        .execute()
    return jsonify(result.data or [])


@bp.route('/definitions', methods=['POST'])
@require_auth
def create_definition():
    """Create a new pipeline definition for this org."""
    data = request.get_json()
    required = ['name', 'document_type', 'steps']
    for field in required:
        if field not in data:
            return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': f'{field} is required'}}), 400

    data['org_id'] = g.org_id
    client = db._get_client()
    result = client.table('pipeline_definitions').insert(data).execute()
    return jsonify(result.data[0] if result.data else {}), 201


@bp.route('/definitions/<definition_id>', methods=['PATCH'])
@require_auth
def update_definition(definition_id: str):
    data = request.get_json()
    client = db._get_client()
    result = client.table('pipeline_definitions') \
        .update(data) \
        .eq('id', definition_id) \
        .eq('org_id', g.org_id) \
        .execute()
    if not result.data:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Pipeline definition not found'}}), 404
    return jsonify(result.data[0])


@bp.route('/definitions/<definition_id>', methods=['DELETE'])
@require_auth
def delete_definition(definition_id: str):
    client = db._get_client()
    result = client.table('pipeline_definitions') \
        .delete() \
        .eq('id', definition_id) \
        .eq('org_id', g.org_id) \
        .execute()
    if not result.data:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Pipeline definition not found'}}), 404
    return jsonify({'message': 'Pipeline definition deleted'})


@bp.route('/runs', methods=['GET'])
@require_auth
def list_runs():
    """List recent pipeline runs for this org."""
    limit = request.args.get('limit', 50, type=int)
    client = db._get_client()
    result = client.table('pipeline_runs') \
        .select('*, pipeline_definitions(name, document_type)') \
        .eq('org_id', g.org_id) \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()
    return jsonify(result.data or [])


@bp.route('/runs/<run_id>/steps', methods=['GET'])
@require_auth
def get_run_steps(run_id: str):
    """Get step details for a specific pipeline run."""
    client = db._get_client()
    result = client.table('pipeline_step_runs') \
        .select('*') \
        .eq('pipeline_run_id', run_id) \
        .order('created_at') \
        .execute()
    return jsonify(result.data or [])


@bp.route('/config', methods=['GET'])
@require_auth
def get_generation_config():
    """Get the org's generation config."""
    client = db._get_client()
    result = client.table('generation_configs') \
        .select('*') \
        .eq('org_id', g.org_id) \
        .execute()
    if not result.data:
        return jsonify({
            'default_model': 'gpt-5.4',
            'temperature': 0.0,
            'enable_few_shot': True,
            'max_few_shot_examples': 3,
            'default_edit_options': {}
        })
    return jsonify(result.data[0])


@bp.route('/config', methods=['PATCH'])
@require_auth
def update_generation_config():
    """Update the org's generation config."""
    data = request.get_json()
    client = db._get_client()

    existing = client.table('generation_configs') \
        .select('id') \
        .eq('org_id', g.org_id) \
        .execute()

    if existing.data:
        result = client.table('generation_configs') \
            .update(data) \
            .eq('org_id', g.org_id) \
            .execute()
    else:
        data['org_id'] = g.org_id
        result = client.table('generation_configs') \
            .insert(data) \
            .execute()

    return jsonify(result.data[0] if result.data else data)
