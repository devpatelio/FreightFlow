"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-z0-9-]+$')


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    settings: dict = {}
    onboarding_completed_at: Optional[datetime] = None
    created_at: datetime


class OrgMemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    created_at: datetime


class InvitationCreate(BaseModel):
    email: str = Field(..., min_length=5)
    role: str = Field(default='member', pattern=r'^(owner|admin|member)$')


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

class ApiKeyCreate(BaseModel):
    provider: str = Field(..., pattern=r'^(openai|reducto)$')
    key: str = Field(..., min_length=10)


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    key_hint: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    customer_code: Optional[str] = Field(default=None, max_length=50)
    default_payment_terms: str = 'NET 90 DAYS'
    default_delivery_terms: str = 'Free Carrier DESTINATION'
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    customer_code: Optional[str] = Field(default=None, max_length=50)
    default_payment_terms: Optional[str] = None
    default_delivery_terms: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    org_id: str
    company_name: str
    customer_code: Optional[str] = None
    default_payment_terms: str
    default_delivery_terms: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

class ContactCreate(BaseModel):
    customer_id: str
    name: str = Field(..., min_length=1)
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_primary: bool = False


class ContactResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_primary: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

class AddressCreate(BaseModel):
    customer_id: Optional[str] = None
    name: str = Field(..., min_length=1)
    label: Optional[str] = None
    address_line: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    zip_code: str = Field(..., min_length=1)
    country: str = 'USA'
    phone: Optional[str] = None
    email: Optional[str] = None
    address_type: str = Field(default='shipping', pattern=r'^(shipping|billing|warehouse|office)$')
    is_default: bool = False


class AddressUpdate(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address_type: Optional[str] = None
    is_default: Optional[bool] = None


class AddressResponse(BaseModel):
    id: str
    org_id: str
    customer_id: Optional[str] = None
    name: str
    label: Optional[str] = None
    address_line: str
    city: str
    state: str
    zip_code: str
    country: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address_type: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Seller Profiles
# ---------------------------------------------------------------------------

class SellerProfileCreate(BaseModel):
    company_name: str = Field(..., min_length=1)
    display_name: Optional[str] = None
    default_salesperson: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    context_text: Optional[str] = None
    is_default: bool = False


class SellerProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    display_name: Optional[str] = None
    default_salesperson: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    context_text: Optional[str] = None
    is_default: Optional[bool] = None


class SellerProfileResponse(BaseModel):
    id: str
    org_id: str
    company_name: str
    display_name: Optional[str] = None
    default_salesperson: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    context_text: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    item_number: Optional[str] = None
    un_code: Optional[str] = None
    default_unit_type: str = 'kg'
    default_handling_unit_type: str = 'IBC'
    notes: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_number: Optional[str] = None
    un_code: Optional[str] = None
    default_unit_type: Optional[str] = None
    default_handling_unit_type: Optional[str] = None
    notes: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    item_number: Optional[str] = None
    un_code: Optional[str] = None
    default_unit_type: str
    default_handling_unit_type: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentUploadResponse(BaseModel):
    id: str
    document_type: str
    document_name: str
    status: str
    customer_id: Optional[str] = None
    created_at: datetime


class DocumentResponse(BaseModel):
    id: str
    org_id: str
    customer_id: Optional[str] = None
    document_type: str
    document_name: str
    status: str
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    parsed_data: Optional[Any] = None
    generated_data: Optional[Any] = None
    created_at: datetime
    updated_at: datetime


class GenerateRequest(BaseModel):
    ship_from_address_id: Optional[str] = None
    ship_to_address_id: Optional[str] = None
    use_schema: bool = True
    bol_number_override: Optional[str] = None
    custom_instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# Templates & Schemas
# ---------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    template_type: str = Field(..., pattern=r'^(prompt|pdf)$')
    content: Optional[str] = None
    storage_path: Optional[str] = None
    description: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    org_id: str
    name: str
    template_type: str
    content: Optional[str] = None
    storage_path: Optional[str] = None
    description: Optional[str] = None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SchemaResponse(BaseModel):
    id: str
    org_id: str
    template_name: str
    schema_data: Any = Field(alias='schema')
    num_fields: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: dict = Field(..., example={'code': 'VALIDATION_ERROR', 'message': 'Field is required'})


class SuccessResponse(BaseModel):
    message: str
    data: Optional[Any] = None
