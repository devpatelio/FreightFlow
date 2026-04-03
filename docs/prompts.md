# Prompt Template Catalog

Reference for all AI prompt templates used in the document generation pipeline. In production, these are stored per-org in the `document_templates` table. The legacy versions live in `templates/*.txt`.

## BOL Extraction Prompt

**Template key**: `bol_extraction`
**Legacy file**: `templates/BOL_Template.txt`
**Model**: OpenAI (configurable, default gpt-5.4)
**Purpose**: Extract Bill of Lading data from a parsed Purchase Order

### Structure

The system prompt is composed of two parts concatenated:

1. **Org context** (from `seller_profiles.context_text`):
   - Company name and legal entity
   - Vendor address (default ship-from)
   - Shipper address (if different)
   - Default salesperson name and phone
   - General instructions about the company's role

2. **Extraction template** (from `document_templates` where `name='bol_extraction'`):
   - Field-by-field extraction instructions for 9 sections
   - JSON output schema with example
   - Type and unit rules (preventing column mix-ups)
   - Validation checklist

### Sections Extracted

| Section | Key Fields | Notes |
|---------|-----------|-------|
| BOL Identification | bol_number, bol_date | BOL number format: YYYYMMDDXX (date + sequence) |
| Ship From | name, address, city, state, zip_code, country, phone, email | Defaults to org's shipper address |
| Ship To | name, address, city, state, zip_code, country, phone, email | Extracted from PO |
| Third Party Bill To | Same as address fields | Only populated if explicitly specified |
| Carrier | carrier_name, trailer_number, seal_number | |
| Orders | customer_id, po_number, sales_order_number, material_name, num_packages, weight, weight_unit, country_of_origin | One entry per line item |
| Products | name, description, item_number, un_code, handling_unit, package, weight | One entry per product |
| Financial | cod_amount, freight_charges | Null if not applicable |
| Special Instructions | special_instructions, hazmat_info, temperature_requirements | Free text |

### Known Failure Modes

1. **Column swap**: `num_packages` (count) confused with `weight` (numeric). Mitigated by explicit type annotations in the prompt: "integer count only" vs "numeric only".
2. **Date in wrong field**: BOL number format (YYYYMMDD) mistakenly placed in a date field. Mitigated by the rule "BOL Number: digits only (no hyphens)".
3. **Missing ship-from**: The model sometimes omits ship_from when the PO only shows the buyer. Mitigated by the org context providing a default.
4. **Multiple PO line items merged**: When a PO has several products, the model occasionally merges them. Mitigated by "Create separate entries for each product/order".

### Improvement History

| Date | Change | Reason |
|------|--------|--------|
| 2024-12 | Added explicit type rules section | Frequent column swaps between counts and weights |
| 2025-01 | Added BOL number format rules | Dates appearing in BOL number field |
| 2025-01 | Added validation checklist | Model skipping validation |

---

## Packing Slip Extraction Prompt

**Template key**: `ps_extraction`
**Legacy file**: `templates/PackingSlip_Template.txt`
**Model**: OpenAI (configurable, default gpt-5.4)
**Purpose**: Extract Packing Slip data from a parsed Purchase Order

### Structure

Same two-part system prompt (org context + extraction template).

### Sections Extracted

| Section | Key Fields | Notes |
|---------|-----------|-------|
| Header | date, customer_id, salesperson | customer_id is the company name, not a code |
| Bill To | address fields | Left blank unless explicitly specified in PO |
| Ship To | name, address, city, state, zip_code, country | Delivery destination |
| Ship From | name, address, city, state, zip_code, country | Org's shipper address |
| Order Info | order_date, order_number, purchase_order_number, customer_contact | Critical fields — prompt emphasizes never returning null for these |
| Line Items | item_number, description, order_qty, ship_qty, total | One per product |

### Known Failure Modes

1. **Missing order info fields**: `order_date`, `purchase_order_number`, `customer_contact` returned as null even when present in PO. Mitigated by explicit "IMPORTANT (DO NOT MISS THESE)" section.
2. **Bill-to populated when it shouldn't be**: Model fills bill_to from the PO buyer address. Prompt says "Leave BLANK unless explicitly specified".
3. **customer_id as a code instead of name**: Model returns an abbreviated code. Prompt specifies "This is the customer/company NAME, not just an ID code".

---

## Company Context Prompt

**Template key**: `org_context` (stored in `seller_profiles.context_text`)
**Legacy file**: `templates/HansonChemicals.txt`
**Purpose**: Provide the AI with the org's identity for document generation

### Current Content (Hanson Chemicals)

```
You are a logistics support assistant that fills out import logistics forms
for my chemical distribution company Hanson Chemicals.
...
Vendor Address:
HANSON CHEMICALS (11418793 Canada Inc)
22 Xavier Court, BRAMPTON ON L6Y 5S1, CANADA

Shipper Address:
HANSON CHEMICALS
21177 TOWER DRIVE N 169 W, JACKSON WI 53037

Salesperson: Pan Patel
Phone Number: 4164578271
```

### Template for New Orgs

When a new org sets up their seller profile, the system generates a context prompt from structured data:

```
You are a logistics support assistant that fills out import logistics forms
for {company_name}.

Default Ship-From Address:
{seller_address}

Default Salesperson: {salesperson_name}
Phone: {phone}

Your job is to take Purchase Orders and fill in the relevant fields to generate
Bill of Lading and Packing Slip documents. Focus on accuracy and simplicity.
If unsure about information, use USER_FILL as a placeholder.
```

---

## Instruction Generation (Reducto Edit)

Not stored as templates — these are generated at runtime from the extracted JSON.

### BOL Instructions

Generated by `_bol_instructions()` in the AI service. Format:

```
Fill this Bill of Lading with the following information:

BOL NUMBER (digits only): {bol_number}
BOL DATE (YYYY-MM-DD): {bol_date}

SHIP FROM:
  Company: {ship_from.name}
  Address: {ship_from.address}
  City/State/Zip: {city} {state} {zip_code}

SHIP TO:
  ...

PRODUCTS (be strict about types: counts vs weights vs units):
  Product 1:
    Name (text): {name}
    Handling Unit Quantity (integer count only): {handling_unit.quantity}
    ...

ORDERS:
  Order 1:
    Customer ID (text): {customer_id}
    PO Number (text): {po_number}
    ...
```

Each field is annotated with its expected type to prevent Reducto's LLM from misplacing values.

### Packing Slip Instructions

Generated by `_packing_slip_instructions()`. Follows the same pattern with section headers matching the PDF layout:

- HEADER SECTION
- BILL TO SECTION
- SHIP FROM SECTION
- SHIP TO SECTION
- ORDER INFORMATION ROW
- LINE ITEMS TABLE

### Long Text Handling

Text longer than 60 characters is wrapped via `_wrap_text()` to fit PDF form field widths.

---

## Versioning Strategy

Prompt templates are versioned in `document_templates.version`:

1. When modifying a prompt, increment the version number
2. The previous version remains in the table (with `is_active = false`)
3. Pipeline definitions reference templates by `name` (always uses the latest active version)
4. Pipeline run logs capture which template version was used (via `pipeline_step_runs` metadata)

This allows:
- Rolling back to a previous prompt version
- Comparing extraction quality across prompt versions
- Auditing what prompts produced a specific document
