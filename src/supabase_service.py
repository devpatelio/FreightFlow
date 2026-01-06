"""
Supabase Service Module
Handles all database and storage operations with Supabase
"""

import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseService:
    """Service class for Supabase database and storage operations"""

    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables. "
                "Please create a .env file with these values."
            )

        self.client: Client = create_client(self.url, self.key)

        # Storage bucket names
        self.BUCKET_UPLOADS = 'document-uploads'
        self.BUCKET_GENERATED = 'generated-documents'
        self.BUCKET_TEMPLATES = 'templates'

    # ========================================================================
    # ACCOUNT (CUSTOMER) OPERATIONS
    # ========================================================================

    def create_account(self, company_name: str, customer_id: str, **kwargs) -> Dict[str, Any]:
        """Create a new account (customer)"""
        data = {
            'company_name': company_name,
            'customer_id': customer_id,
            'default_payment_terms': kwargs.get('default_payment_terms', 'NET 90 DAYS'),
            'default_delivery_terms': kwargs.get('default_delivery_terms', 'Free Carrier DESTINATION'),
            'notes': kwargs.get('notes')
        }

        result = self.client.table('accounts').insert(data).execute()
        return result.data[0] if result.data else None

    def get_account(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get account by customer_id"""
        result = self.client.table('accounts')\
            .select('*')\
            .eq('customer_id', customer_id)\
            .execute()

        return result.data[0] if result.data else None

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by UUID"""
        result = self.client.table('accounts')\
            .select('*')\
            .eq('id', account_id)\
            .execute()

        return result.data[0] if result.data else None

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all accounts"""
        result = self.client.table('accounts')\
            .select('*')\
            .order('company_name')\
            .execute()

        return result.data or []

    def update_account(self, customer_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an account"""
        result = self.client.table('accounts')\
            .update(data)\
            .eq('customer_id', customer_id)\
            .execute()

        return result.data[0] if result.data else None

    def delete_account(self, customer_id: str) -> bool:
        """Delete an account"""
        result = self.client.table('accounts')\
            .delete()\
            .eq('customer_id', customer_id)\
            .execute()

        return len(result.data) > 0 if result.data else False

    def get_account_with_documents(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get account with all associated documents, grouped by PO"""
        account = self.get_account(customer_id)
        if not account:
            print(f"⚠️ Account not found for customer_id: {customer_id}")
            return None

        account_uuid = account['id']
        print(f"✓ Found account: {account['company_name']} (UUID: {account_uuid})")

        # Get all documents for this account
        documents = self.client.table('documents')\
            .select('*')\
            .eq('account_id', account_uuid)\
            .order('created_at', desc=True)\
            .execute()

        account['documents'] = documents.data or []
        print(f"✓ Found {len(account['documents'])} total documents for this account")

        # Group documents by type
        pos = [d for d in account['documents'] if d['document_type'] == 'PO']
        all_bols = [d for d in account['documents'] if d['document_type'] == 'BOL']
        all_packing_slips = [d for d in account['documents'] if d['document_type'] == 'PACKING_SLIP']

        # For each PO, get its related documents (BOL and Packing Slip)
        pos_with_related = []
        for po in pos:
            related = self.get_related_documents(po['document_id'])
            po_with_related = {
                'po': po,
                'bols': related.get('bols', []),
                'packing_slips': related.get('packing_slips', [])
            }
            pos_with_related.append(po_with_related)

        account['pos_with_related'] = pos_with_related
        account['total_pos'] = len(pos)
        account['total_bols'] = len(all_bols)
        account['total_packing_slips'] = len(all_packing_slips)

        print(f"  - POs: {len(pos)}")
        print(f"  - BOLs: {len(all_bols)}")
        print(f"  - Packing Slips: {len(all_packing_slips)}")

        return account

    # ========================================================================
    # ADDRESS OPERATIONS
    # ========================================================================

    def create_address(self, name: str, address: str, city: str, state: str,
                      zip_code: str, country: str = "USA", **kwargs) -> Dict[str, Any]:
        """Create a new address"""
        data = {
            'name': name,
            'address': address,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'country': country,
            'phone': kwargs.get('phone'),
            'email': kwargs.get('email'),
            'address_type': kwargs.get('address_type', 'shipping'),  # shipping, billing, warehouse
            'account_id': kwargs.get('account_id'),  # Link to customer account (optional)
            'seller_company_id': kwargs.get('seller_company_id'),  # Link to seller company (optional)
            'is_default': kwargs.get('is_default', False),
            'label': kwargs.get('label')  # e.g., "Canadian Warehouse", "US Distribution Center"
        }

        result = self.client.table('addresses').insert(data).execute()
        return result.data[0] if result.data else None

    def get_address(self, address_id: str) -> Optional[Dict[str, Any]]:
        """Get address by ID"""
        result = self.client.table('addresses')\
            .select('*')\
            .eq('id', address_id)\
            .execute()

        return result.data[0] if result.data else None

    def list_addresses(self, account_id: Optional[str] = None, 
                       seller_company_id: Optional[str] = None,
                       address_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List addresses, optionally filtered"""
        query = self.client.table('addresses').select('*')

        if account_id:
            query = query.eq('account_id', account_id)
        if seller_company_id:
            query = query.eq('seller_company_id', seller_company_id)
        if address_type:
            query = query.eq('address_type', address_type)

        result = query.order('name').execute()
        return result.data or []

    def list_seller_addresses(self) -> List[Dict[str, Any]]:
        """List all addresses linked to seller companies"""
        result = self.client.table('addresses')\
            .select('*, seller_companies(*)')\
            .not_.is_('seller_company_id', 'null')\
            .order('name')\
            .execute()

        return result.data or []

    def list_customer_addresses(self, account_id: str) -> List[Dict[str, Any]]:
        """List all addresses for a specific customer"""
        result = self.client.table('addresses')\
            .select('*')\
            .eq('account_id', account_id)\
            .order('name')\
            .execute()

        return result.data or []

    def update_address(self, address_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an address"""
        result = self.client.table('addresses')\
            .update(data)\
            .eq('id', address_id)\
            .execute()

        return result.data[0] if result.data else None

    def delete_address(self, address_id: str) -> bool:
        """Delete an address"""
        result = self.client.table('addresses')\
            .delete()\
            .eq('id', address_id)\
            .execute()

        return len(result.data) > 0 if result.data else False

    # ========================================================================
    # SELLER COMPANY OPERATIONS
    # ========================================================================

    def create_seller_company(self, company_name: str, **kwargs) -> Dict[str, Any]:
        """Create a new seller company (replaces static HansonChemicals.txt)"""
        data = {
            'company_name': company_name,
            'default_salesperson': kwargs.get('default_salesperson'),
            'phone': kwargs.get('phone'),
            'email': kwargs.get('email'),
            'notes': kwargs.get('notes'),
            'is_default': kwargs.get('is_default', False)
        }

        result = self.client.table('seller_companies').insert(data).execute()
        return result.data[0] if result.data else None

    def get_seller_company(self, seller_id: str) -> Optional[Dict[str, Any]]:
        """Get seller company by ID with addresses"""
        result = self.client.table('seller_companies')\
            .select('*, addresses(*)')\
            .eq('id', seller_id)\
            .execute()

        return result.data[0] if result.data else None

    def get_default_seller_company(self) -> Optional[Dict[str, Any]]:
        """Get the default seller company with addresses"""
        result = self.client.table('seller_companies')\
            .select('*, addresses(*)')\
            .eq('is_default', True)\
            .execute()

        if result.data:
            return result.data[0]
        
        # If no default, return first seller company
        result = self.client.table('seller_companies')\
            .select('*, addresses(*)')\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    def list_seller_companies(self) -> List[Dict[str, Any]]:
        """List all seller companies with their addresses"""
        result = self.client.table('seller_companies')\
            .select('*, addresses(*)')\
            .order('company_name')\
            .execute()

        return result.data or []

    def update_seller_company(self, seller_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a seller company"""
        result = self.client.table('seller_companies')\
            .update(data)\
            .eq('id', seller_id)\
            .execute()

        return result.data[0] if result.data else None

    def delete_seller_company(self, seller_id: str) -> bool:
        """Delete a seller company"""
        result = self.client.table('seller_companies')\
            .delete()\
            .eq('id', seller_id)\
            .execute()

        return len(result.data) > 0 if result.data else False

    # ========================================================================
    # BOL NUMBER GENERATION
    # ========================================================================

    def get_next_bol_number(self, account_id: str) -> str:
        """
        Generate next BOL number for a customer: YYYYMMDD + sequence number
        Sequence is based on how many POs this customer has (1-indexed)
        """
        from datetime import datetime
        
        # Count POs for this customer
        result = self.client.table('documents')\
            .select('id', count='exact')\
            .eq('account_id', account_id)\
            .eq('document_type', 'PO')\
            .execute()

        po_count = (result.count or 0) + 1  # Next sequence number
        
        date_prefix = datetime.now().strftime('%Y%m%d')
        sequence = str(po_count).zfill(2)  # 01, 02, 03, etc.
        
        return f"{date_prefix}{sequence}"

    def get_customer_po_count(self, account_id: str) -> int:
        """Get count of POs for a customer"""
        result = self.client.table('documents')\
            .select('id', count='exact')\
            .eq('account_id', account_id)\
            .eq('document_type', 'PO')\
            .execute()

        return result.count or 0

    # ========================================================================
    # PRODUCT OPERATIONS
    # ========================================================================

    def create_product(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new product"""
        data = {
            'name': name,
            'description': kwargs.get('description'),
            'item_number': kwargs.get('item_number'),
            'un_code': kwargs.get('un_code'),
            'default_unit_type': kwargs.get('default_unit_type', 'kg'),
            'default_handling_unit_type': kwargs.get('default_handling_unit_type', 'IBC'),
            'notes': kwargs.get('notes')
        }

        result = self.client.table('products').insert(data).execute()
        return result.data[0] if result.data else None

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        result = self.client.table('products')\
            .select('*')\
            .eq('id', product_id)\
            .execute()

        return result.data[0] if result.data else None

    def list_products(self) -> List[Dict[str, Any]]:
        """List all products"""
        result = self.client.table('products')\
            .select('*')\
            .order('name')\
            .execute()

        return result.data or []

    def update_product(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a product"""
        result = self.client.table('products')\
            .update(data)\
            .eq('id', product_id)\
            .execute()

        return result.data[0] if result.data else None

    def delete_product(self, product_id: str) -> bool:
        """Delete a product"""
        result = self.client.table('products')\
            .delete()\
            .eq('id', product_id)\
            .execute()

        return len(result.data) > 0 if result.data else False

    # ========================================================================
    # DOCUMENT OPERATIONS
    # ========================================================================

    def create_document(self, document_id: int, document_type: str, document_name: str,
                       account_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a new document record"""
        data = {
            'document_id': document_id,
            'document_type': document_type,
            'document_name': document_name,
            'account_id': account_id,
            'file_path': kwargs.get('file_path'),
            'file_url': kwargs.get('file_url'),
            'parsed_data': kwargs.get('parsed_data'),
            'status': kwargs.get('status', 'processed')
        }

        result = self.client.table('documents').insert(data).execute()
        return result.data[0] if result.data else None

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document by document_id"""
        result = self.client.table('documents')\
            .select('*')\
            .eq('document_id', document_id)\
            .execute()

        return result.data[0] if result.data else None

    def list_documents(self, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all documents, optionally filtered by type"""
        query = self.client.table('documents').select('*')

        if document_type:
            query = query.eq('document_type', document_type)

        result = query.order('created_at', desc=True).execute()
        return result.data or []

    def update_document(self, document_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a document"""
        result = self.client.table('documents')\
            .update(data)\
            .eq('document_id', document_id)\
            .execute()

        return result.data[0] if result.data else None

    def store_generated_data(self, document_id: int, bol_data: Dict = None, packing_slip_data: Dict = None) -> Optional[Dict[str, Any]]:
        """Store generated BOL and Packing Slip data in the PO document"""
        data = {}
        
        if bol_data is not None:
            data['bol_data'] = json.dumps(bol_data)
        
        if packing_slip_data is not None:
            data['packing_slip_data'] = json.dumps(packing_slip_data)
        
        if not data:
            return None
        
        result = self.client.table('documents')\
            .update(data)\
            .eq('document_id', document_id)\
            .execute()
        
        return result.data[0] if result.data else None

    def get_generated_data(self, document_id: int) -> Dict[str, Any]:
        """Retrieve stored BOL and Packing Slip data from PO document"""
        doc = self.get_document(document_id)
        
        if not doc:
            return {}
        
        result = {}
        
        # Parse BOL data if it exists
        if doc.get('bol_data'):
            if isinstance(doc['bol_data'], str):
                result['bol_data'] = json.loads(doc['bol_data'])
            else:
                result['bol_data'] = doc['bol_data']
        
        # Parse Packing Slip data if it exists
        if doc.get('packing_slip_data'):
            if isinstance(doc['packing_slip_data'], str):
                result['packing_slip_data'] = json.loads(doc['packing_slip_data'])
            else:
                result['packing_slip_data'] = doc['packing_slip_data']
        
        return result

    def link_documents(self, po_document_id: int, generated_document_id: int, relationship_type: str):
        """Link a PO to a generated document (BOL or PACKING_SLIP)"""
        data = {
            'po_document_id': po_document_id,
            'generated_document_id': generated_document_id,
            'relationship_type': relationship_type
        }

        result = self.client.table('document_relationships').insert(data).execute()
        return result.data[0] if result.data else None

    def get_related_documents(self, po_document_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get all documents generated from a PO"""
        result = self.client.table('document_relationships')\
            .select('*, documents!document_relationships_generated_document_id_fkey(*)')\
            .eq('po_document_id', po_document_id)\
            .execute()

        related = {'bols': [], 'packing_slips': []}

        for rel in (result.data or []):
            if rel.get('documents'):
                doc = rel['documents']
                if rel['relationship_type'] == 'BOL':
                    related['bols'].append(doc)
                elif rel['relationship_type'] == 'PACKING_SLIP':
                    related['packing_slips'].append(doc)

        return related

    # ========================================================================
    # FORM SCHEMA OPERATIONS
    # ========================================================================

    def save_form_schema(self, template_name: str, schema: List[Dict], **kwargs) -> Dict[str, Any]:
        """Save or update form schema"""
        data = {
            'template_name': template_name,
            'schema': json.dumps(schema),
            'num_fields': len(schema),
            'template_file_id': kwargs.get('template_file_id'),
            'description': kwargs.get('description')
        }

        # Upsert on template_name (unique key). Without on_conflict, PostgREST may attempt an INSERT
        # and fail with duplicate key errors.
        table = self.client.table('form_schemas')
        try:
            result = table.upsert(data, on_conflict='template_name').execute()
        except TypeError:
            # Backwards compatibility for older supabase-py versions
            result = table.upsert(data).execute()

        return result.data[0] if result.data else None

    def get_form_schema(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get form schema by template name"""
        result = self.client.table('form_schemas')\
            .select('*')\
            .eq('template_name', template_name)\
            .execute()

        if result.data:
            schema_data = result.data[0]
            # Parse JSON schema if it's a string (Supabase JSONB columns auto-parse)
            if isinstance(schema_data['schema'], str):
                schema_data['schema'] = json.loads(schema_data['schema'])
            # If it's already a list/dict, use as-is
            return schema_data

        return None

    def list_form_schemas(self) -> List[Dict[str, Any]]:
        """List all form schemas"""
        result = self.client.table('form_schemas')\
            .select('*')\
            .order('template_name')\
            .execute()

        schemas = result.data or []

        # Parse JSON schemas if they're strings (Supabase JSONB columns auto-parse)
        for schema in schemas:
            if isinstance(schema['schema'], str):
                schema['schema'] = json.loads(schema['schema'])
            # If it's already a list/dict, use as-is

        return schemas

    def update_form_schema(self, template_name: str, description: str) -> Optional[Dict[str, Any]]:
        """Update form schema description"""
        data = {
            'description': description,
            'updated_at': datetime.now().isoformat()
        }
        
        result = self.client.table('form_schemas')\
            .update(data)\
            .eq('template_name', template_name)\
            .execute()
        
        return result.data[0] if result.data else None

    def delete_form_schema(self, template_name: str) -> bool:
        """Delete a form schema"""
        result = self.client.table('form_schemas')\
            .delete()\
            .eq('template_name', template_name)\
            .execute()

        return len(result.data) > 0 if result.data else False

    # ========================================================================
    # STORAGE OPERATIONS
    # ========================================================================

    def upload_file(self, bucket: str, file_path: str, file_data: bytes, content_type: str = 'application/pdf') -> str:
        """Upload a file to Supabase storage"""
        result = self.client.storage.from_(bucket).upload(
            file_path,
            file_data,
            {
                'content-type': content_type,
                'upsert': 'false'
            }
        )

        # Get public URL (or signed URL for private buckets)
        file_url = self.client.storage.from_(bucket).get_public_url(file_path)
        return file_url

    def download_file(self, bucket: str, file_path: str) -> bytes:
        """Download a file from Supabase storage"""
        result = self.client.storage.from_(bucket).download(file_path)
        return result

    def delete_file(self, bucket: str, file_path: str) -> bool:
        """Delete a file from Supabase storage"""
        result = self.client.storage.from_(bucket).remove([file_path])
        return len(result) > 0

    def get_signed_url(self, bucket: str, file_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for private file access"""
        result = self.client.storage.from_(bucket).create_signed_url(file_path, expires_in)
        return result.get('signedURL') if result else None

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_statistics(self) -> Dict[str, int]:
        """Get system statistics"""
        stats = {}

        # Count accounts
        accounts = self.client.table('accounts').select('id', count='exact').execute()
        stats['total_customers'] = accounts.count if accounts.count is not None else 0

        # Count products
        products = self.client.table('products').select('id', count='exact').execute()
        stats['total_products'] = products.count if products.count is not None else 0

        # Count documents by type
        all_docs = self.client.table('documents').select('id', count='exact').execute()
        stats['total_documents'] = all_docs.count if all_docs.count is not None else 0

        pos = self.client.table('documents').select('id', count='exact').eq('document_type', 'PO').execute()
        stats['total_pos'] = pos.count if pos.count is not None else 0

        bols = self.client.table('documents').select('id', count='exact').eq('document_type', 'BOL').execute()
        stats['total_bols'] = bols.count if bols.count is not None else 0

        slips = self.client.table('documents').select('id', count='exact').eq('document_type', 'PACKING_SLIP').execute()
        stats['total_packing_slips'] = slips.count if slips.count is not None else 0

        # Count form schemas
        schemas = self.client.table('form_schemas').select('id', count='exact').execute()
        stats['total_form_schemas'] = schemas.count if schemas.count is not None else 0

        return stats


# Global instance
_supabase_service = None

def get_supabase_service() -> SupabaseService:
    """Get or create the global Supabase service instance"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
