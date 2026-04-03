export interface Organization {
  id: string
  name: string
  slug: string
  settings: Record<string, unknown>
  onboarding_completed_at: string | null
  created_at: string
}

export interface Customer {
  id: string
  org_id: string
  company_name: string
  customer_code: string | null
  default_payment_terms: string
  default_delivery_terms: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Contact {
  id: string
  customer_id: string
  name: string
  email: string | null
  phone: string | null
  role: string | null
  is_primary: boolean
  created_at: string
}

export interface Address {
  id: string
  org_id: string
  customer_id: string | null
  name: string
  label: string | null
  address_line: string
  city: string
  state: string
  zip_code: string
  country: string
  phone: string | null
  email: string | null
  address_type: 'shipping' | 'billing' | 'warehouse' | 'office'
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface SellerProfile {
  id: string
  org_id: string
  company_name: string
  display_name: string | null
  default_salesperson: string | null
  phone: string | null
  email: string | null
  context_text: string | null
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface Product {
  id: string
  org_id: string
  name: string
  description: string | null
  item_number: string | null
  un_code: string | null
  default_unit_type: string
  default_handling_unit_type: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  org_id: string
  customer_id: string | null
  document_type: 'PO' | 'BOL' | 'PACKING_SLIP'
  document_name: string
  status: string
  file_path: string | null
  file_url: string | null
  parsed_data: unknown
  generated_data: unknown
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface UserProfile {
  user_id: string
  display_name: string | null
  avatar_url: string | null
}

export interface ApiKey {
  id: string
  provider: 'openai' | 'reducto'
  key_hint: string | null
  last_used_at: string | null
  created_at: string
}

export interface OrgStats {
  total_customers: number
  total_products: number
  total_documents: number
  total_pos: number
  total_bols: number
  total_packing_slips: number
}
