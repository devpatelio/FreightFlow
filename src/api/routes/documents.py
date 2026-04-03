"""Document routes: upload, list, review, and generate."""

from flask import Blueprint, jsonify, request, g
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename

from ..auth import require_auth
from ..config import Config
from ..services import supabase_service as db

bp = Blueprint('documents', __name__, url_prefix='/api/documents')


def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@bp.route('', methods=['GET'])
@require_auth
def list_documents():
    doc_type = request.args.get('type')
    customer_id = request.args.get('customer_id')
    docs = db.list_documents(g.org_id, document_type=doc_type, customer_id=customer_id)
    return jsonify(docs)


@bp.route('/<document_id>', methods=['GET'])
@require_auth
def get_document(document_id: str):
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404
    return jsonify(doc)


@bp.route('/<document_id>', methods=['DELETE'])
@require_auth
def delete_document(document_id: str):
    """Delete a document and its file from storage."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    # Try to delete file from storage
    file_path = doc.get('file_path')
    if file_path:
        bucket = db.BUCKET_GENERATED if doc['document_type'] in ('BOL', 'PACKING_SLIP') else db.BUCKET_UPLOADS
        try:
            db.delete_file(bucket, file_path)
        except Exception:
            pass

    db.delete_document(g.org_id, document_id)
    return jsonify({'ok': True})


@bp.route('/<document_id>/url', methods=['GET'])
@require_auth
def get_document_url(document_id: str):
    """Get a signed URL for viewing/downloading a document's PDF."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    file_path = doc.get('file_path')
    if not file_path:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'No file associated with this document'}}), 404

    bucket = db.BUCKET_GENERATED if doc['document_type'] in ('BOL', 'PACKING_SLIP') else db.BUCKET_UPLOADS
    try:
        signed_url = db.create_signed_url(bucket, file_path, expires_in=3600)
        return jsonify({'url': signed_url, 'filename': doc.get('document_name', 'document.pdf')})
    except Exception as e:
        return jsonify({'error': {'code': 'STORAGE_ERROR', 'message': str(e)}}), 500


@bp.route('/<document_id>/reupload', methods=['POST'])
@require_auth
def reupload_document(document_id: str):
    """Re-upload an edited PDF for an existing document."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    if 'file' not in request.files:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No file provided'}}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'File must be a PDF'}}), 400

    file_data = file.read()
    file_path = doc.get('file_path')
    if not file_path:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'No file path on document'}}), 404

    bucket = db.BUCKET_GENERATED if doc['document_type'] in ('BOL', 'PACKING_SLIP') else db.BUCKET_UPLOADS
    try:
        db.upload_file(bucket=bucket, file_path=file_path, file_data=file_data, content_type='application/pdf')
        db.update_document(g.org_id, document_id, {'updated_at': datetime.now().isoformat(), 'updated_by': g.user_id})
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': {'code': 'UPLOAD_ERROR', 'message': str(e)}}), 500


@bp.route('/upload', methods=['POST'])
@require_auth
def upload_document():
    """Upload a PO document for processing."""
    if 'file' not in request.files:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'No file provided'}}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'Invalid file type'}}), 400

    customer_id = request.form.get('customer_id')

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"

    Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    file_path = Config.UPLOAD_FOLDER / unique_filename
    file.save(str(file_path))

    try:
        # Upload to Supabase storage
        with open(file_path, 'rb') as f:
            file_data = f.read()

        storage_path = f"{g.org_id}/{datetime.now().strftime('%Y/%m')}/{unique_filename}"
        file_url = db.upload_file(
            bucket=db.BUCKET_UPLOADS,
            file_path=storage_path,
            file_data=file_data,
            content_type='application/pdf'
        )

        doc = db.create_document(g.org_id, {
            'document_type': 'PO',
            'document_name': unique_filename,
            'customer_id': customer_id,
            'file_path': storage_path,
            'file_url': file_url,
            'status': 'uploaded',
            'created_by': g.user_id,
            'updated_by': g.user_id,
        })

        return jsonify(doc), 201

    except Exception as e:
        return jsonify({'error': {'code': 'UPLOAD_ERROR', 'message': str(e)}}), 500
    finally:
        if file_path.exists():
            file_path.unlink()


@bp.route('/<document_id>/parse', methods=['POST'])
@require_auth
def parse_document(document_id: str):
    """Parse an uploaded PO document using Reducto."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    if doc['document_type'] != 'PO':
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'Only PO documents can be parsed'}}), 400

    # Get org's Reducto API key
    reducto_key = db.get_org_api_key(g.org_id, 'reducto')
    if not reducto_key:
        return jsonify({'error': {'code': 'CONFIG_ERROR', 'message': 'Reducto API key not configured. Add it in Organization Settings.'}}), 400

    try:
        db.update_document(g.org_id, document_id, {'status': 'parsing'})

        from reducto import Reducto
        client = Reducto(api_key=reducto_key)

        # Download file from storage and parse
        file_data = db.download_file(db.BUCKET_UPLOADS, doc['file_path'])

        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        tmp_path = Config.UPLOAD_FOLDER / f"parse_{document_id}.pdf"
        with open(tmp_path, 'wb') as f:
            f.write(file_data)

        upload = client.upload(file=tmp_path)
        result = client.parse.run(input=upload, formatting={"table_output_format": "json"})

        chunks_data = []
        for chunk in result.result.chunks:
            chunk_dict = {"content": chunk.content, "blocks": []}
            for block in chunk.blocks:
                block_dict = {
                    "type": block.type if hasattr(block, 'type') else None,
                    "content": block.content if hasattr(block, 'content') else None,
                    "bbox": {
                        "page": block.bbox.page, "left": block.bbox.left,
                        "top": block.bbox.top, "width": block.bbox.width,
                        "height": block.bbox.height
                    } if hasattr(block, 'bbox') and block.bbox else None,
                }
                chunk_dict["blocks"].append(block_dict)
            chunks_data.append(chunk_dict)

        parsed_data = {
            "job_id": result.job_id,
            "usage": {"num_pages": result.usage.num_pages, "credits": result.usage.credits},
            "chunks": chunks_data,
        }

        db.update_document(g.org_id, document_id, {
            'parsed_data': parsed_data,
            'status': 'parsed',
            'updated_by': g.user_id,
        })

        tmp_path.unlink(missing_ok=True)

        return jsonify({'status': 'parsed', 'parsed_data': parsed_data})

    except Exception as e:
        db.update_document(g.org_id, document_id, {'status': 'error'})
        return jsonify({'error': {'code': 'PARSE_ERROR', 'message': str(e)}}), 500


@bp.route('/<document_id>/extract', methods=['POST'])
@require_auth
def extract_document(document_id: str):
    """Extract structured BOL/PS JSON from a parsed PO using OpenAI."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    if not doc.get('parsed_data'):
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'Document has not been parsed yet'}}), 400

    openai_key = db.get_org_api_key(g.org_id, 'openai')
    if not openai_key:
        return jsonify({'error': {'code': 'CONFIG_ERROR', 'message': 'OpenAI API key not configured. Add it in Organization Settings.'}}), 400

    body = request.get_json() if request.is_json else {}
    document_type = body.get('document_type', 'BOL')

    # Optional overrides from the frontend
    address_id = body.get('address_id')
    seller_id = body.get('seller_id')

    try:
        db.update_document(g.org_id, document_id, {'status': 'extracting'})

        # --- Build org context ---
        seller = None
        if seller_id:
            seller = db.get_seller_profile(g.org_id, seller_id)
        if not seller:
            seller = db.get_default_seller_profile(g.org_id)
        company_context = seller.get('context_text', '') if seller else ''

        # Resolve address for ship_from
        override_addr = None
        if address_id:
            override_addr = db.get_address(g.org_id, address_id)
        if not override_addr:
            all_addrs = db.list_addresses(g.org_id)
            org_addrs = [a for a in all_addrs if a.get('customer_id') is None and a.get('is_default')]
            override_addr = org_addrs[0] if org_addrs else None

        # Build seller info string for the prompt
        seller_info_parts = []
        if seller:
            if seller.get('company_name'):
                seller_info_parts.append(f"Seller Company: {seller['company_name']}")
            if seller.get('default_salesperson'):
                seller_info_parts.append(f"Salesperson: {seller['default_salesperson']}")
            if seller.get('phone'):
                seller_info_parts.append(f"Phone: {seller['phone']}")
            if seller.get('email'):
                seller_info_parts.append(f"Email: {seller['email']}")
        if override_addr:
            seller_info_parts.append(f"Ship From Address: {override_addr.get('name', '')}, "
                                     f"{override_addr.get('address_line', '')}, "
                                     f"{override_addr.get('city', '')} {override_addr.get('state', '')} "
                                     f"{override_addr.get('zip_code', '')}, "
                                     f"{override_addr.get('country', 'USA')}")
        seller_context = "\n".join(seller_info_parts) if seller_info_parts else ''

        # --- Load prompt template ---
        template_prompt = ''
        pdf_template_id = body.get('template_id')
        if pdf_template_id:
            pdf_tpl = db.get_template_by_id(g.org_id, pdf_template_id)
            if pdf_tpl and pdf_tpl.get('linked_prompt_id'):
                prompt_tpl = db.get_template_by_id(g.org_id, pdf_tpl['linked_prompt_id'])
                if prompt_tpl:
                    template_prompt = prompt_tpl.get('content', '')

        if not template_prompt:
            template_key = 'bol_extraction' if document_type == 'BOL' else 'ps_extraction'
            template = db.get_template(g.org_id, template_key)
            template_prompt = template['content'] if template else ''

        # If still no prompt, use a built-in default based on document type
        if not template_prompt:
            template_prompt = _default_extraction_prompt(document_type)

        # --- Extract text from parsed data ---
        chunks = doc['parsed_data'].get('chunks', [])
        po_text = "\n\n".join(c.get('content', '') for c in chunks if c.get('content', '').strip())

        current_date = datetime.now()
        date_info = f"CURRENT DATE: {current_date.strftime('%Y-%m-%d')}\nDocument Number Format: {current_date.strftime('%Y%m%d')}XXX"

        system_parts = [p for p in [company_context, seller_context, template_prompt] if p]
        system_prompt = "\n\n".join(system_parts)

        gen_config = db.get_generation_config(g.org_id)
        model = gen_config.get('default_model', 'gpt-4o') if gen_config else 'gpt-4o'
        temperature = float(gen_config.get('temperature', 0.0)) if gen_config else 0.0

        import openai
        client = openai.OpenAI(api_key=openai_key)

        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{date_info}\n\nPurchase Order data:\n\n{po_text}\n\nReturn ONLY valid JSON for a {document_type}."}
            ],
            response_format={"type": "json_object"}
        )

        import json
        extracted = json.loads(response.choices[0].message.content)

        # Apply address overrides deterministically (for both BOL and PS)
        if override_addr:
            addr_dict = {
                'name': override_addr.get('name'), 'address': override_addr.get('address_line'),
                'city': override_addr.get('city'), 'state': override_addr.get('state'),
                'zip_code': override_addr.get('zip_code'), 'country': override_addr.get('country', 'USA'),
            }
            if document_type == 'BOL':
                extracted['ship_from'] = addr_dict
            elif document_type == 'PACKING_SLIP':
                extracted['ship_from'] = addr_dict

        # Apply salesperson for packing slips
        if seller and document_type == 'PACKING_SLIP':
            if seller.get('default_salesperson') and not extracted.get('salesperson'):
                extracted['salesperson'] = seller['default_salesperson']

        # Re-read fresh to avoid overwriting concurrent extractions
        data_key = 'bol' if document_type == 'BOL' else 'packing_slip'
        fresh_doc = db.get_document(g.org_id, document_id)
        existing_gen = (fresh_doc.get('generated_data') if fresh_doc else doc.get('generated_data')) or {}
        existing_gen[data_key] = extracted
        db.update_document(g.org_id, document_id, {
            'generated_data': existing_gen,
            'status': 'extracted',
            'updated_by': g.user_id,
        })

        return jsonify({'status': 'extracted', 'document_type': document_type, 'data': extracted})

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            db.update_document(g.org_id, document_id, {'status': 'error'})
        except Exception:
            pass
        return jsonify({'error': {'code': 'EXTRACT_ERROR', 'message': str(e)}}), 500


def _default_extraction_prompt(document_type: str) -> str:
    """Provide a built-in extraction prompt when no template is configured."""
    if document_type == 'BOL':
        return (
            "You are an expert logistics document processor. Extract Bill of Lading data from the "
            "purchase order. Return valid JSON with these top-level keys: bol_number, bol_date, "
            "ship_from (name, address, city, state, zip_code, country), "
            "ship_to (name, address, city, state, zip_code, country), "
            "bill_to (or null), carrier_name, products (array with name, description, item_number, "
            "un_code, handling_unit {quantity, type}, package {quantity, type}, weight), "
            "orders (array with customer_id, po_number, sales_order_number, material_name, "
            "num_packages, weight, weight_unit, country_of_origin, customer_po, additional_shipper_info), "
            "cod_amount, special_instructions. "
            "Use YYYY-MM-DD for dates. BOL number should be digits only."
        )
    else:
        return (
            "You are an expert logistics document processor. Extract Packing Slip data from the "
            "purchase order. Return valid JSON with these top-level keys: date, customer_id, "
            "salesperson, bill_to (name, address, city, state, zip_code, country), "
            "ship_from (name, address, city, state, zip_code, country), "
            "ship_to (name, address, city, state, zip_code, country), "
            "order_date, order_number, purchase_order_number, customer_contact, "
            "items (array with item_number, description, order_qty, ship_qty), total. "
            "Use YYYY-MM-DD for dates. Quantities should be numeric only."
        )


@bp.route('/<document_id>/fill', methods=['POST'])
@require_auth
def fill_document(document_id: str):
    """Fill a PDF template with extracted data using Reducto Edit."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    generated_data = doc.get('generated_data')
    if not generated_data:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': 'Document has not been extracted yet'}}), 400

    reducto_key = db.get_org_api_key(g.org_id, 'reducto')
    if not reducto_key:
        return jsonify({'error': {'code': 'CONFIG_ERROR', 'message': 'Reducto API key not configured. Add it in Settings > API Keys.'}}), 400

    body = request.get_json() or {}
    document_type = body.get('document_type', 'BOL')
    template_id = body.get('template_id')

    data_key = 'bol' if document_type.upper() == 'BOL' else 'packing_slip'
    fill_data = generated_data.get(data_key)
    if not fill_data:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': f'No extracted {document_type} data found (key: {data_key}). Run extraction first.'}}), 400

    # Allow user-edited overrides from the review page
    if body.get('data_overrides'):
        fill_data = {**fill_data, **body['data_overrides']}

    try:
        db.update_document(g.org_id, document_id, {'status': 'filling'})

        # Resolve PDF template
        pdf_template = None
        if template_id:
            pdf_template = db.get_template_by_id(g.org_id, template_id)
        else:
            pdf_templates = db.get_pdf_templates(g.org_id)
            doc_type_upper = document_type.upper()

            # 1st pass: match by explicit document_type tag (most reliable)
            for t in pdf_templates:
                if t.get('document_type') == doc_type_upper:
                    pdf_template = t
                    break

            # 2nd pass: fuzzy name match (normalize underscores/spaces)
            if not pdf_template:
                search_terms = {
                    'BOL': ['bol', 'bill of lading', 'billoflading'],
                    'PACKING_SLIP': ['packing slip', 'packing_slip', 'packingslip', 'ps'],
                }
                terms = search_terms.get(doc_type_upper, [doc_type_upper.lower().replace('_', ' ')])
                for t in pdf_templates:
                    name_lower = t.get('name', '').lower()
                    name_normalized = name_lower.replace('_', ' ')
                    if any(term in name_normalized for term in terms):
                        pdf_template = t
                        break

            if not pdf_template and pdf_templates:
                pdf_template = pdf_templates[0]

        if not pdf_template or not pdf_template.get('storage_path'):
            return jsonify({'error': {'code': 'CONFIG_ERROR', 'message': f'No PDF template found for {document_type}. Upload one in Templates.'}}), 400

        # Download the blank PDF template from storage
        template_file_data = db.download_file(db.BUCKET_TEMPLATES, pdf_template['storage_path'])

        # Load form schema if available
        template_name = pdf_template.get('name', '')
        schema_record = db.get_form_schema(g.org_id, template_name)
        form_schema = schema_record.get('schema') if schema_record else None

        is_packing_slip = document_type.upper() in ('PACKING_SLIP', 'PS')

        from ..services.fill_service import fill_pdf_template

        result = fill_pdf_template(
            reducto_api_key=reducto_key,
            template_file_data=template_file_data,
            fill_data=fill_data,
            form_schema=form_schema,
            is_packing_slip=is_packing_slip,
        )

        # If Reducto auto-generated a schema and we didn't have one, save it
        if result.get('generated_schema') and not form_schema:
            try:
                db.create_form_schema(g.org_id, {
                    'template_name': template_name,
                    'schema': result['generated_schema'],
                    'num_fields': len(result['generated_schema']),
                    'description': f'Auto-generated from first {document_type} fill',
                })
            except Exception:
                pass

        # Download the filled PDF from Reducto and save to our storage
        import requests as http_requests
        filled_resp = http_requests.get(result['document_url'])
        filled_resp.raise_for_status()
        filled_pdf_data = filled_resp.content

        import uuid
        filled_filename = f"{document_type}_{uuid.uuid4().hex[:8]}.pdf"
        filled_storage_path = f"{g.org_id}/{datetime.now().strftime('%Y/%m')}/{filled_filename}"

        db.upload_file(
            bucket=db.BUCKET_GENERATED,
            file_path=filled_storage_path,
            file_data=filled_pdf_data,
            content_type='application/pdf',
        )

        # Create a new document record for the generated BOL/PS
        generated_doc = db.create_document(g.org_id, {
            'document_type': document_type,
            'document_name': filled_filename,
            'file_path': filled_storage_path,
            'customer_id': doc.get('customer_id'),
            'status': 'generated',
            'generated_data': fill_data,
        })

        # Link generated doc to the source PO (relationship_type must be uppercase per check constraint)
        db.link_documents(document_id, generated_doc['id'], document_type.upper())

        db.update_document(g.org_id, document_id, {'status': 'filled', 'updated_by': g.user_id})

        return jsonify({
            'status': 'filled',
            'document_type': document_type,
            'generated_document_id': generated_doc['id'],
            'file_path': filled_storage_path,
        })

    except Exception as e:
        db.update_document(g.org_id, document_id, {'status': 'error'})
        return jsonify({'error': {'code': 'FILL_ERROR', 'message': str(e)}}), 500


PIPELINE_STAGES = ['uploaded', 'parsed', 'extracted', 'filled', 'generated']

RESET_MAP = {
    'uploaded': {'status': 'uploaded', 'clear': ['parsed_data', 'generated_data']},
    'parsed':   {'status': 'parsed',   'clear': ['generated_data']},
    'extracted': {'status': 'extracted', 'clear': []},
}


@bp.route('/<document_id>/reset', methods=['POST'])
@require_auth
def reset_document(document_id: str):
    """Reset a document back to a previous pipeline stage."""
    doc = db.get_document(g.org_id, document_id)
    if not doc:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Document not found'}}), 404

    body = request.get_json() or {}
    target = body.get('target_status', 'uploaded')

    if target not in RESET_MAP:
        return jsonify({'error': {
            'code': 'VALIDATION_ERROR',
            'message': f'Invalid target status. Must be one of: {", ".join(RESET_MAP.keys())}',
        }}), 400

    spec = RESET_MAP[target]
    updates: dict = {'status': spec['status'], 'updated_by': g.user_id}
    for field in spec['clear']:
        updates[field] = None

    db.update_document(g.org_id, document_id, updates)
    updated = db.get_document(g.org_id, document_id)
    return jsonify(updated)


@bp.route('/<document_id>/related', methods=['GET'])
@require_auth
def get_related_documents(document_id: str):
    related = db.get_related_documents(document_id)
    return jsonify(related)
