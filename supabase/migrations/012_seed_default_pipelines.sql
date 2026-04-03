-- 012: Seed default pipeline definitions (system-wide, org_id = NULL)
-- These are the standard pipelines available to all organizations.
-- Orgs can clone and customize these.

INSERT INTO pipeline_definitions (org_id, name, document_type, steps, is_default, description)
VALUES
  (
    NULL,
    'default_bol',
    'BOL',
    '[
      {
        "name": "parse_po",
        "type": "reducto_parse",
        "config": {
          "table_output_format": "json"
        }
      },
      {
        "name": "extract_bol",
        "type": "openai_extract",
        "config": {
          "prompt_template_key": "bol_extraction",
          "include_few_shot": true,
          "max_few_shot_examples": 3
        }
      },
      {
        "name": "fill_bol_pdf",
        "type": "reducto_edit",
        "config": {
          "template_key": "BOL_Template.pdf",
          "use_form_schema": true,
          "enable_overflow_pages": false,
          "deterministic_prefill": false
        }
      }
    ]'::JSONB,
    true,
    'Standard Bill of Lading generation pipeline: parse PO, extract BOL data with OpenAI, fill BOL PDF template with Reducto'
  ),
  (
    NULL,
    'default_packing_slip',
    'PACKING_SLIP',
    '[
      {
        "name": "parse_po",
        "type": "reducto_parse",
        "config": {
          "table_output_format": "json"
        }
      },
      {
        "name": "extract_packing_slip",
        "type": "openai_extract",
        "config": {
          "prompt_template_key": "ps_extraction",
          "include_few_shot": true,
          "max_few_shot_examples": 3
        }
      },
      {
        "name": "fill_packing_slip_pdf",
        "type": "reducto_edit",
        "config": {
          "template_key": "PackingSlip_Template.pdf",
          "use_form_schema": true,
          "enable_overflow_pages": false,
          "deterministic_prefill": true
        }
      }
    ]'::JSONB,
    true,
    'Standard Packing Slip generation pipeline: parse PO, extract PS data with OpenAI, fill PS PDF template with Reducto (with deterministic prefill for header fields)'
  );
