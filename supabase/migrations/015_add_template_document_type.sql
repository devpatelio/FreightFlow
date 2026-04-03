-- 015: Add document_type to document_templates so PDF templates can be explicitly
-- tagged as BOL or PACKING_SLIP instead of relying on name matching.

ALTER TABLE document_templates
  ADD COLUMN IF NOT EXISTS document_type TEXT
    CHECK (document_type IS NULL OR document_type IN ('BOL', 'PACKING_SLIP'));

COMMENT ON COLUMN document_templates.document_type IS
  'Which output document this template produces. NULL for prompt templates.';
