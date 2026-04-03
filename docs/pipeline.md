# Document Generation Pipeline

End-to-end reference for how FreightFlow transforms a Purchase Order PDF into Bill of Lading and Packing Slip documents.

## Pipeline Overview

```
PO PDF ──▶ [Parse] ──▶ [Extract] ──▶ [Review/Edit] ──▶ [Fill PDF] ──▶ BOL PDF + PS PDF
            Reducto      OpenAI        User              Reducto
```

Each step is a discrete unit defined in `pipeline_definitions.steps` (JSONB). Steps can be swapped, configured per-org, and A/B tested.

## Step 1: Parse (Reducto)

**Purpose**: Extract structured text, tables, and layout from the PO PDF.

**API call**: `reducto.parse.run(input=upload, formatting={"table_output_format": "json"})`

**Input**: Raw PO PDF file (uploaded via `reducto.upload(file=path)`)

**Output**: `parsed_data` JSONB stored on the document record:
```json
{
  "job_id": "...",
  "duration": 5.2,
  "usage": { "num_pages": 2, "credits": 1.0 },
  "chunks": [
    {
      "content": "PURCHASE ORDER\nPO Number: 4535119724\n...",
      "blocks": [
        {
          "type": "Table",
          "content": "| Item | Qty | Unit Price |...",
          "bbox": { "page": 1, "left": 0.05, "top": 0.3, "width": 0.9, "height": 0.4 },
          "confidence": 0.95
        }
      ]
    }
  ],
  "studio_link": "https://..."
}
```

**Cost**: ~1 Reducto credit per page

**User intervention**: User can review parsed output and flag quality issues before proceeding.

## Step 2: Extract (OpenAI)

**Purpose**: Transform parsed PO text into structured BOL and Packing Slip JSON.

**API call**: `openai.chat.completions.create(model=..., messages=[...], response_format={"type": "json_object"})`

**Model**: Configurable per org in `generation_configs.default_model` (default: `gpt-5.4`)

### BOL Extraction

**System prompt** (concatenated):
1. **Org context** — From `seller_profiles.context_text` (legacy: `HansonChemicals.txt`)
   - Company name, addresses, salesperson, phone
   - Tells the model who the shipper is
2. **Extraction template** — From `document_templates` where `name='bol_extraction'` (legacy: `BOL_Template.txt`)
   - Field definitions for all BOL sections
   - JSON output schema with types and validation rules
   - Instructions for date formatting, BOL numbering, unit handling

**User prompt**:
```
CURRENT DATE INFORMATION (use this for BOL number generation):
- Today's Date: 2026-04-02
- BOL Number Format: 20260402XXX

Here is the Purchase Order data to process:

{extracted_text_from_chunks}

Please extract the information and return ONLY a valid JSON object...
```

**Output**: BOL JSON
```json
{
  "bol_number": "2026040201",
  "bol_date": "2026-04-02",
  "ship_from": { "name": "...", "address": "...", "city": "...", ... },
  "ship_to": { "name": "...", "address": "...", "city": "...", ... },
  "products": [{ "name": "...", "handling_unit": { "quantity": 2, "type": "IBC" }, ... }],
  "orders": [{ "customer_id": "...", "po_number": "...", "weight": 1000, ... }],
  "carrier_name": "...",
  "special_instructions": "..."
}
```

### Packing Slip Extraction

Same pattern but uses `PackingSlip_Template.txt` prompt template. Output is simpler:
```json
{
  "date": "2026-04-02",
  "customer_id": "Solenis LLC",
  "salesperson": "Pan Patel",
  "ship_to": { ... },
  "ship_from": { ... },
  "order_date": "2026-03-28",
  "purchase_order_number": "PO-4535119724",
  "items": [{ "item_number": "HC-1001", "description": "...", "order_qty": 2000, "ship_qty": 2000 }]
}
```

**Cost**: ~500-2000 input tokens + ~500-1000 output tokens per extraction

**Post-extraction overrides** (applied automatically):
- `ship_from` is overridden with the org's default seller address
- `salesperson` is overridden with the seller profile's default salesperson
- `bol_number` is overridden with a computed sequence number

**User intervention**: User can edit any field in the extracted JSON before proceeding to PDF fill.

## Step 3: Fill PDF (Reducto Edit)

**Purpose**: Map the structured JSON data onto a PDF template to produce the final document.

**API call**: `reducto.edit.run(document_url=template_id, edit_instructions=instructions, edit_options=options, form_schema=schema)`

### Instruction Generation

The JSON data is converted to natural-language instructions via `_bol_instructions()` or `_packing_slip_instructions()`. Example BOL instructions:

```
Fill this Bill of Lading with the following information:

BOL NUMBER (digits only): 2026040201
BOL DATE (YYYY-MM-DD): 2026-04-02

SHIP FROM:
  Company: Hanson Chemicals
  Address: 21177 Tower Drive N 169 W
  City/State/Zip: Jackson WI 53037

SHIP TO:
  Company: Solenis Plant - Burlington
  ...

PRODUCTS:
  Product 1:
    Name: Sodium Hydroxide 50%
    Handling Unit Quantity (integer count only): 2
    Handling Unit Type (IBC/Drum/Pallet/Box text only): IBC
    Package/Weight Quantity (numeric only): 1000
    Package/Weight Unit (kg/lb text only): kg
```

### Form Schema

Each PDF template has an associated form schema — an array of field definitions with bounding boxes:

```json
{
  "bbox": { "height": 0.016, "left": 0.169, "page": 1, "top": 0.202, "width": 0.198 },
  "description": "SHIP TO - Name. Enter the consignee/destination company name.",
  "type": "text",
  "fill": true,
  "value": null
}
```

Schemas are stored in `form_schemas` per org. On first run, if no schema exists, Reducto auto-detects fields and the schema is saved for subsequent runs.

### Deterministic Prefill (Packing Slip)

For the Packing Slip template, critical fields are prefilled deterministically (bypassing the LLM) via `_prefill_packing_slip_form_schema()`:

- Header fields: DATE, CUSTOMER ID, SALESPERSON
- Order info row: ORDER DATE, ORDER #, PURCHASE ORDER #, CUSTOMER CONTACT
- Address sections: SHIP FROM, SHIP TO, BILL TO (all subfields)
- Line items: ITEM #, DESCRIPTION, ORDER QTY, SHIP QTY (by row number)

This prevents LLM inconsistency on structured form fields where exact values are known.

### Edit Options

```python
edit_options = {
    "enable_overflow_pages": False,  # PDF only; True adds appendix for overflow
    "llm_provider_preference": "openai",
    "color": "#000000"  # Text color for filled fields
}
```

**Cost**: ~1-2 Reducto credits per fill

**Output**: URL to the filled PDF, downloaded to local filesystem then uploaded to Supabase Storage.

## Pipeline Run Logging

Every pipeline execution is logged in `pipeline_runs` and `pipeline_step_runs`:

```
pipeline_runs:
  id, org_id, pipeline_definition_id, document_id, status, duration_ms, total_cost

pipeline_step_runs (one per step):
  id, pipeline_run_id, step_name, step_type, provider, model,
  input_tokens, output_tokens, credits_used, duration_ms, status
```

This enables:
- Cost tracking per org, per customer, per document
- Performance monitoring (which steps are slow?)
- Error debugging (which step failed and why?)
- A/B test comparison across pipeline variants

## User Intervention Points

| Step | Intervention | Data Modified |
|------|-------------|---------------|
| After Parse | Review parsed text, flag quality issues | Re-parse or manual correction |
| After Extract | Edit any JSON field inline | `generated_data` JSONB on document |
| After Extract | Add custom instructions for re-extraction | Appended to user prompt |
| After Extract | Select/override addresses | `ship_from`, `ship_to` in JSON |
| After Fill | Preview filled PDF | — |
| After Fill | Edit fields in PDF viewer | PDF content (re-fill if needed) |
| After Fill | Approve or reject | Document status |

## Feedback Loop

When a user corrects a field after extraction, the correction is stored in `pipeline_feedback`:

```json
{
  "pipeline_run_id": "...",
  "step_name": "extract_bol",
  "field_path": "ship_to.name",
  "original_value": "Solenis Plant",
  "corrected_value": "Solenis Plant - Burlington"
}
```

When `generation_configs.enable_few_shot` is true, past corrections for the same customer are included as few-shot examples in subsequent extraction prompts, improving accuracy over time.
