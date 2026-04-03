-- 013: Link prompt templates to PDF templates

ALTER TABLE document_templates
  ADD COLUMN linked_prompt_id UUID REFERENCES document_templates(id) ON DELETE SET NULL;

CREATE INDEX idx_document_templates_linked_prompt ON document_templates(linked_prompt_id);
