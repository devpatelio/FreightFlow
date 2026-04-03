"""Supabase service for the new multi-tenant schema.

All queries are scoped to an org_id passed by the caller (injected from JWT auth).
"""

import os
import json
from typing import List, Dict, Optional, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise ValueError('SUPABASE_URL and SUPABASE_KEY must be set')
        _client = create_client(url, key)
    return _client


# ── Organizations ──────────────────────────────────────────────────────────

def create_organization(name: str, slug: str) -> Dict:
    result = _get_client().table('organizations').insert({
        'name': name, 'slug': slug,
    }).execute()
    return result.data[0]


def get_organization(org_id: str) -> Optional[Dict]:
    result = _get_client().table('organizations') \
        .select('*').eq('id', org_id).execute()
    return result.data[0] if result.data else None


def update_organization(org_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('organizations') \
        .update(data).eq('id', org_id).execute()
    return result.data[0] if result.data else None


def add_org_member(org_id: str, user_id: str, role: str = 'owner') -> Dict:
    result = _get_client().table('org_members').insert({
        'org_id': org_id, 'user_id': user_id, 'role': role,
    }).execute()
    return result.data[0]


def list_org_members(org_id: str) -> List[Dict]:
    return _get_client().table('org_members') \
        .select('*').eq('org_id', org_id).order('created_at').execute().data or []


def update_org_member(org_id: str, member_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('org_members') \
        .update(data).eq('id', member_id).eq('org_id', org_id).execute()
    return result.data[0] if result.data else None


def remove_org_member(org_id: str, member_id: str) -> None:
    _get_client().table('org_members') \
        .delete().eq('id', member_id).eq('org_id', org_id).execute()


def create_invitation(org_id: str, email: str, role: str, invited_by: str) -> Dict:
    from datetime import datetime, timedelta
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    result = _get_client().table('org_invitations').insert({
        'org_id': org_id, 'email': email, 'role': role,
        'invited_by': invited_by, 'expires_at': expires_at,
    }).execute()
    return result.data[0]


def list_invitations(org_id: str) -> List[Dict]:
    return _get_client().table('org_invitations') \
        .select('*').eq('org_id', org_id).is_('accepted_at', 'null') \
        .order('created_at', desc=True).execute().data or []


def get_pending_invitations_for_email(email: str) -> List[Dict]:
    return _get_client().table('org_invitations') \
        .select('*, organizations(name, slug)') \
        .eq('email', email).is_('accepted_at', 'null') \
        .execute().data or []


def accept_invitation(invitation_id: str, user_id: str) -> Dict:
    from datetime import datetime
    inv = _get_client().table('org_invitations') \
        .select('*').eq('id', invitation_id).is_('accepted_at', 'null').execute()
    if not inv.data:
        raise ValueError('Invitation not found or already accepted')
    invitation = inv.data[0]

    add_org_member(invitation['org_id'], user_id, invitation['role'])

    _get_client().table('org_invitations') \
        .update({'accepted_at': datetime.utcnow().isoformat()}) \
        .eq('id', invitation_id).execute()

    return invitation


def delete_invitation(org_id: str, invitation_id: str) -> None:
    _get_client().table('org_invitations') \
        .delete().eq('id', invitation_id).eq('org_id', org_id).execute()


# ── User Profiles ─────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> Optional[Dict]:
    result = _get_client().table('user_profiles') \
        .select('*').eq('user_id', user_id).execute()
    return result.data[0] if result.data else None


def upsert_user_profile(user_id: str, data: Dict) -> Dict:
    data['user_id'] = user_id
    result = _get_client().table('user_profiles') \
        .upsert(data, on_conflict='user_id').execute()
    return result.data[0]


def get_user_profiles_by_ids(user_ids: List[str]) -> List[Dict]:
    if not user_ids:
        return []
    result = _get_client().table('user_profiles') \
        .select('*').in_('user_id', user_ids).execute()
    return result.data or []


# ── Customers ──────────────────────────────────────────────────────────────

def list_customers(org_id: str) -> List[Dict]:
    return _get_client().table('customers') \
        .select('*').eq('org_id', org_id).order('company_name').execute().data or []


def get_customer(org_id: str, customer_id: str) -> Optional[Dict]:
    result = _get_client().table('customers') \
        .select('*').eq('org_id', org_id).eq('id', customer_id).execute()
    return result.data[0] if result.data else None


def create_customer(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('customers').insert(data).execute()
    return result.data[0]


def update_customer(org_id: str, customer_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('customers') \
        .update(data).eq('org_id', org_id).eq('id', customer_id).execute()
    return result.data[0] if result.data else None


def delete_customer(org_id: str, customer_id: str) -> bool:
    result = _get_client().table('customers') \
        .delete().eq('org_id', org_id).eq('id', customer_id).execute()
    return bool(result.data)


# ── Contacts ───────────────────────────────────────────────────────────────

def list_contacts(org_id: str, customer_id: str) -> List[Dict]:
    return _get_client().table('contacts') \
        .select('*').eq('org_id', org_id).eq('customer_id', customer_id).order('name').execute().data or []


def create_contact(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('contacts').insert(data).execute()
    return result.data[0]


def delete_contact(org_id: str, contact_id: str) -> bool:
    result = _get_client().table('contacts') \
        .delete().eq('org_id', org_id).eq('id', contact_id).execute()
    return bool(result.data)


# ── Addresses ──────────────────────────────────────────────────────────────

def list_addresses(org_id: str, customer_id: Optional[str] = None) -> List[Dict]:
    query = _get_client().table('addresses').select('*').eq('org_id', org_id)
    if customer_id:
        query = query.eq('customer_id', customer_id)
    return query.order('name').execute().data or []


def get_address(org_id: str, address_id: str) -> Optional[Dict]:
    result = _get_client().table('addresses') \
        .select('*').eq('org_id', org_id).eq('id', address_id).execute()
    return result.data[0] if result.data else None


def create_address(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('addresses').insert(data).execute()
    return result.data[0]


def update_address(org_id: str, address_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('addresses') \
        .update(data).eq('org_id', org_id).eq('id', address_id).execute()
    return result.data[0] if result.data else None


def delete_address(org_id: str, address_id: str) -> bool:
    result = _get_client().table('addresses') \
        .delete().eq('org_id', org_id).eq('id', address_id).execute()
    return bool(result.data)


# ── Seller Profiles ────────────────────────────────────────────────────────

def list_seller_profiles(org_id: str) -> List[Dict]:
    return _get_client().table('seller_profiles') \
        .select('*').eq('org_id', org_id).order('company_name').execute().data or []


def get_seller_profile(org_id: str, seller_id: str) -> Optional[Dict]:
    result = _get_client().table('seller_profiles') \
        .select('*').eq('id', seller_id).eq('org_id', org_id).execute()
    return result.data[0] if result.data else None


def get_default_seller_profile(org_id: str) -> Optional[Dict]:
    result = _get_client().table('seller_profiles') \
        .select('*').eq('org_id', org_id).eq('is_default', True).execute()
    if result.data:
        return result.data[0]
    result = _get_client().table('seller_profiles') \
        .select('*').eq('org_id', org_id).limit(1).execute()
    return result.data[0] if result.data else None


def create_seller_profile(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('seller_profiles').insert(data).execute()
    return result.data[0]


def update_seller_profile(org_id: str, profile_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('seller_profiles') \
        .update(data).eq('org_id', org_id).eq('id', profile_id).execute()
    return result.data[0] if result.data else None


def delete_seller_profile(org_id: str, profile_id: str) -> bool:
    result = _get_client().table('seller_profiles') \
        .delete().eq('org_id', org_id).eq('id', profile_id).execute()
    return bool(result.data)


# ── Products ───────────────────────────────────────────────────────────────

def list_products(org_id: str) -> List[Dict]:
    return _get_client().table('products') \
        .select('*').eq('org_id', org_id).order('name').execute().data or []


def get_product(org_id: str, product_id: str) -> Optional[Dict]:
    result = _get_client().table('products') \
        .select('*').eq('org_id', org_id).eq('id', product_id).execute()
    return result.data[0] if result.data else None


def create_product(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('products').insert(data).execute()
    return result.data[0]


def update_product(org_id: str, product_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('products') \
        .update(data).eq('org_id', org_id).eq('id', product_id).execute()
    return result.data[0] if result.data else None


def delete_product(org_id: str, product_id: str) -> bool:
    result = _get_client().table('products') \
        .delete().eq('org_id', org_id).eq('id', product_id).execute()
    return bool(result.data)


# ── Documents ──────────────────────────────────────────────────────────────

def list_documents(org_id: str, document_type: Optional[str] = None, customer_id: Optional[str] = None) -> List[Dict]:
    query = _get_client().table('documents').select('*').eq('org_id', org_id)
    if document_type:
        query = query.eq('document_type', document_type)
    if customer_id:
        query = query.eq('customer_id', customer_id)
    return query.order('created_at', desc=True).execute().data or []


def get_document(org_id: str, document_id: str) -> Optional[Dict]:
    result = _get_client().table('documents') \
        .select('*').eq('org_id', org_id).eq('id', document_id).execute()
    return result.data[0] if result.data else None


def create_document(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('documents').insert(data).execute()
    return result.data[0]


def update_document(org_id: str, document_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('documents') \
        .update(data).eq('org_id', org_id).eq('id', document_id).execute()
    return result.data[0] if result.data else None


def link_documents(po_document_id: str, generated_document_id: str, relationship_type: str) -> Dict:
    data = {
        'po_document_id': po_document_id,
        'generated_document_id': generated_document_id,
        'relationship_type': relationship_type
    }
    result = _get_client().table('document_relationships').insert(data).execute()
    return result.data[0]


def get_related_documents(po_document_id: str) -> List[Dict]:
    result = _get_client().table('document_relationships') \
        .select('*, documents!document_relationships_generated_document_id_fkey(*)') \
        .eq('po_document_id', po_document_id).execute()
    return result.data or []


# ── API Keys ───────────────────────────────────────────────────────────────

def get_org_api_key(org_id: str, provider: str) -> Optional[str]:
    """Get the decrypted API key for a provider. Returns the encrypted_key field
    (decrypt with pgcrypto at the DB level or app-level decryption)."""
    result = _get_client().table('org_api_keys') \
        .select('encrypted_key').eq('org_id', org_id).eq('provider', provider).execute()
    if result.data:
        return result.data[0]['encrypted_key']
    return None


def upsert_api_key(org_id: str, provider: str, encrypted_key: str, key_hint: str, user_id: str) -> Dict:
    data = {
        'org_id': org_id,
        'provider': provider,
        'encrypted_key': encrypted_key,
        'key_hint': key_hint,
        'added_by': user_id
    }
    result = _get_client().table('org_api_keys') \
        .upsert(data, on_conflict='org_id,provider').execute()
    return result.data[0] if result.data else data


def list_api_keys(org_id: str) -> List[Dict]:
    """List API keys (without the actual key values)."""
    result = _get_client().table('org_api_keys') \
        .select('id, provider, key_hint, last_used_at, created_at') \
        .eq('org_id', org_id).execute()
    return result.data or []


# ── Form Schemas ───────────────────────────────────────────────────────────

def get_form_schema(org_id: str, template_name: str) -> Optional[Dict]:
    result = _get_client().table('form_schemas') \
        .select('*').eq('org_id', org_id).eq('template_name', template_name).execute()
    if result.data:
        schema_data = result.data[0]
        if isinstance(schema_data.get('schema'), str):
            schema_data['schema'] = json.loads(schema_data['schema'])
        return schema_data
    return None


def save_form_schema(org_id: str, template_name: str, schema: Any, **kwargs) -> Dict:
    data = {
        'org_id': org_id,
        'template_name': template_name,
        'schema': json.dumps(schema) if not isinstance(schema, str) else schema,
        'num_fields': len(schema) if isinstance(schema, list) else None,
        'template_file_id': kwargs.get('template_file_id'),
        'description': kwargs.get('description')
    }
    result = _get_client().table('form_schemas') \
        .upsert(data, on_conflict='org_id,template_name').execute()
    return result.data[0] if result.data else data


def get_form_schema_by_id(org_id: str, schema_id: str) -> Optional[Dict]:
    result = _get_client().table('form_schemas') \
        .select('*').eq('org_id', org_id).eq('id', schema_id).execute()
    if result.data:
        schema_data = result.data[0]
        if isinstance(schema_data.get('schema'), str):
            schema_data['schema'] = json.loads(schema_data['schema'])
        return schema_data
    return None


def list_form_schemas(org_id: str) -> List[Dict]:
    result = _get_client().table('form_schemas') \
        .select('*').eq('org_id', org_id).order('template_name').execute()
    schemas = result.data or []
    for s in schemas:
        if isinstance(s.get('schema'), str):
            s['schema'] = json.loads(s['schema'])
    return schemas


# ── Templates ──────────────────────────────────────────────────────────────

def list_templates(org_id: str) -> List[Dict]:
    return _get_client().table('document_templates') \
        .select('*').eq('org_id', org_id).eq('is_active', True).order('name').execute().data or []


def get_template(org_id: str, name: str) -> Optional[Dict]:
    result = _get_client().table('document_templates') \
        .select('*').eq('org_id', org_id).eq('name', name).eq('is_active', True) \
        .order('version', desc=True).limit(1).execute()
    return result.data[0] if result.data else None


def get_template_by_id(org_id: str, template_id: str) -> Optional[Dict]:
    result = _get_client().table('document_templates') \
        .select('*').eq('id', template_id).eq('org_id', org_id).execute()
    return result.data[0] if result.data else None


def get_pdf_templates(org_id: str) -> List[Dict]:
    return _get_client().table('document_templates') \
        .select('*').eq('org_id', org_id).eq('template_type', 'pdf').eq('is_active', True) \
        .order('name').execute().data or []


def get_generation_config(org_id: str) -> Optional[Dict]:
    result = _get_client().table('generation_configs') \
        .select('*').eq('org_id', org_id).execute()
    return result.data[0] if result.data else None


def create_template(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('document_templates').insert(data).execute()
    return result.data[0]


def update_template(org_id: str, template_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('document_templates') \
        .update(data).eq('id', template_id).eq('org_id', org_id).execute()
    return result.data[0] if result.data else None


def delete_template(org_id: str, template_id: str) -> bool:
    _get_client().table('document_templates') \
        .delete().eq('id', template_id).eq('org_id', org_id).execute()
    return True


def create_form_schema(org_id: str, data: Dict) -> Dict:
    data['org_id'] = org_id
    result = _get_client().table('form_schemas').insert(data).execute()
    return result.data[0]


def update_form_schema(org_id: str, schema_id: str, data: Dict) -> Optional[Dict]:
    result = _get_client().table('form_schemas') \
        .update(data).eq('id', schema_id).eq('org_id', org_id).execute()
    return result.data[0] if result.data else None


def delete_form_schema(org_id: str, schema_id: str) -> bool:
    _get_client().table('form_schemas') \
        .delete().eq('id', schema_id).eq('org_id', org_id).execute()
    return True


# ── Statistics ─────────────────────────────────────────────────────────────

def get_statistics(org_id: str) -> Dict[str, int]:
    client = _get_client()
    stats = {}

    customers = client.table('customers').select('id', count='exact').eq('org_id', org_id).execute()
    stats['total_customers'] = customers.count or 0

    products = client.table('products').select('id', count='exact').eq('org_id', org_id).execute()
    stats['total_products'] = products.count or 0

    docs = client.table('documents').select('id', count='exact').eq('org_id', org_id).execute()
    stats['total_documents'] = docs.count or 0

    pos = client.table('documents').select('id', count='exact') \
        .eq('org_id', org_id).eq('document_type', 'PO').execute()
    stats['total_pos'] = pos.count or 0

    bols = client.table('documents').select('id', count='exact') \
        .eq('org_id', org_id).eq('document_type', 'BOL').execute()
    stats['total_bols'] = bols.count or 0

    packing_slips = client.table('documents').select('id', count='exact') \
        .eq('org_id', org_id).eq('document_type', 'PACKING_SLIP').execute()
    stats['total_packing_slips'] = packing_slips.count or 0

    return stats


# ── Storage ────────────────────────────────────────────────────────────────

BUCKET_UPLOADS = 'document-uploads'
BUCKET_GENERATED = 'generated-documents'
BUCKET_TEMPLATES = 'templates'


def upload_file(bucket: str, file_path: str, file_data: bytes, content_type: str = 'application/pdf') -> str:
    client = _get_client()
    client.storage.from_(bucket).upload(file_path, file_data, {'content-type': content_type, 'upsert': 'false'})
    return client.storage.from_(bucket).get_public_url(file_path)


def delete_document(org_id: str, document_id: str) -> None:
    _get_client().table('document_relationships') \
        .delete().or_(f"po_document_id.eq.{document_id},generated_document_id.eq.{document_id}").execute()
    _get_client().table('documents') \
        .delete().eq('org_id', org_id).eq('id', document_id).execute()


def download_file(bucket: str, file_path: str) -> bytes:
    return _get_client().storage.from_(bucket).download(file_path)


def delete_file(bucket: str, file_path: str) -> None:
    _get_client().storage.from_(bucket).remove([file_path])


def create_signed_url(bucket: str, file_path: str, expires_in: int = 3600) -> str:
    result = _get_client().storage.from_(bucket).create_signed_url(file_path, expires_in)
    return result.get('signedURL') or result.get('signedUrl', '')
