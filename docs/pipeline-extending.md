# Extending the Pipeline

How to add new document types, pipeline steps, model providers, and A/B test pipeline variants.

## Adding a New Document Type

Example: adding "Certificate of Analysis" (COA) generation from a PO.

### 1. Create the prompt template

Insert into `document_templates`:

```sql
INSERT INTO document_templates (org_id, name, template_type, content, description)
VALUES (
  '<org_id>',
  'coa_extraction',
  'prompt',
  'You are an expert logistics processor. Extract Certificate of Analysis data from the Purchase Order...
   ## OUTPUT FORMAT:
   Return JSON: { "certificate_number": "...", "product_name": "...", ... }',
  'AI prompt for COA extraction from PO'
);
```

### 2. Upload the PDF template

Upload the blank COA PDF template to Supabase Storage under `templates/<org_id>/COA_Template.pdf`, then register it:

```sql
INSERT INTO document_templates (org_id, name, template_type, storage_path, description)
VALUES (
  '<org_id>',
  'coa_template_pdf',
  'pdf',
  'templates/<org_id>/COA_Template.pdf',
  'Blank COA PDF template for Reducto fill'
);
```

### 3. Define the pipeline

Insert a pipeline definition with the ordered steps:

```sql
INSERT INTO pipeline_definitions (org_id, name, document_type, steps, is_default)
VALUES (
  '<org_id>',
  'default_coa',
  'COA',
  '[
    {
      "name": "parse_po",
      "type": "reducto_parse",
      "config": { "table_output_format": "json" }
    },
    {
      "name": "extract_coa",
      "type": "openai_extract",
      "config": {
        "prompt_template_key": "coa_extraction",
        "model": "gpt-5.4"
      }
    },
    {
      "name": "fill_coa_pdf",
      "type": "reducto_edit",
      "config": {
        "template_key": "coa_template_pdf",
        "use_form_schema": true,
        "deterministic_prefill": false
      }
    }
  ]',
  true
);
```

### 4. Add the document type to the enum

Update the `documents.document_type` CHECK constraint:

```sql
ALTER TABLE documents DROP CONSTRAINT documents_document_type_check;
ALTER TABLE documents ADD CONSTRAINT documents_document_type_check
  CHECK (document_type IN ('PO', 'BOL', 'PACKING_SLIP', 'COA'));
```

### 5. Add instruction builder

In the AI service, add a `_coa_instructions()` method that converts the extracted COA JSON to natural-language instructions for Reducto Edit, matching the format of the existing `_bol_instructions()` and `_packing_slip_instructions()`.

### 6. Generate form schema

Run the schema generation for the new template:

```python
POST /api/schemas/generate
{
  "template_name": "COA_Template.pdf",
  "sample_instructions": "Fill with: Certificate #: COA-001, Product: Sodium Hydroxide 50%..."
}
```

## Adding a New Pipeline Step

Steps are defined by `type` in the pipeline definition. The pipeline executor dispatches to the appropriate handler based on type.

### Supported step types

| Type | Handler | Description |
|------|---------|-------------|
| `reducto_parse` | `ReductoParseStep` | Parse a document with Reducto |
| `openai_extract` | `OpenAIExtractStep` | Extract structured JSON with OpenAI |
| `reducto_edit` | `ReductoEditStep` | Fill a PDF template with Reducto |

### Adding a custom step type

1. Create a new step handler class in `src/api/services/pipeline_steps/`:

```python
class CustomValidationStep:
    """Validates extracted data against business rules."""

    async def execute(self, context: PipelineContext) -> StepResult:
        extracted = context.get_step_output("extract_bol")
        errors = self.validate(extracted)

        if errors:
            return StepResult(status="failed", error=f"Validation failed: {errors}")

        return StepResult(status="completed", output=extracted)
```

2. Register the step type in the pipeline executor's dispatch table.

3. Add it to a pipeline definition:

```json
{
  "name": "validate_bol",
  "type": "custom_validation",
  "config": { "rules": ["required_fields", "address_format"] }
}
```

## A/B Testing Pipeline Variants

### Creating variants

Clone an existing pipeline and modify it:

```sql
INSERT INTO pipeline_definitions (org_id, name, document_type, steps, is_default)
SELECT org_id, 'experimental_bol_v2', document_type,
  jsonb_set(steps, '{1,config,model}', '"gpt-5-2025-08-07"'),
  false
FROM pipeline_definitions
WHERE name = 'default_bol' AND org_id = '<org_id>';
```

This creates a variant that uses GPT-5 instead of GPT-5.4 for extraction.

### Assigning variants

Pipeline selection can be:
- **Manual**: User selects a pipeline variant on the upload page
- **Per-customer**: A customer record can reference a preferred pipeline
- **Random**: The system randomly assigns between variants (true A/B test)

### Comparing results

Query pipeline runs to compare variants:

```sql
SELECT
  pd.name AS pipeline,
  COUNT(*) AS runs,
  AVG(pr.duration_ms) AS avg_duration_ms,
  AVG((pr.total_cost->>'openai')::numeric) AS avg_openai_cost,
  COUNT(pf.id)::float / NULLIF(COUNT(pr.id), 0) AS correction_rate
FROM pipeline_runs pr
JOIN pipeline_definitions pd ON pr.pipeline_definition_id = pd.id
LEFT JOIN pipeline_feedback pf ON pf.pipeline_run_id = pr.id
WHERE pr.org_id = '<org_id>'
  AND pr.created_at > now() - interval '30 days'
GROUP BY pd.name;
```

**Key metrics:**
- **Correction rate**: % of runs where the user had to edit fields (lower is better)
- **Average duration**: Total pipeline time in ms
- **Average cost**: OpenAI tokens + Reducto credits
- **Error rate**: % of runs that failed

### Promoting a variant

Once a variant proves better, set it as default:

```sql
UPDATE pipeline_definitions SET is_default = false WHERE org_id = '<org_id>' AND document_type = 'BOL';
UPDATE pipeline_definitions SET is_default = true WHERE id = '<winning_variant_id>';
```

## Adding a New Model Provider

To support a new LLM provider (e.g., Anthropic, Google) for extraction:

1. Add the provider to the `org_api_keys.provider` CHECK constraint
2. Create a new step handler (e.g., `AnthropicExtractStep`) in `src/api/services/pipeline_steps/`
3. Register the step type (e.g., `anthropic_extract`) in the pipeline executor
4. Add a new step type value in pipeline definitions
5. Update the BYOK UI in Org Settings to allow entering keys for the new provider

The extraction interface is the same regardless of provider — system prompt + user prompt in, structured JSON out. The pipeline abstraction makes provider swaps transparent.
