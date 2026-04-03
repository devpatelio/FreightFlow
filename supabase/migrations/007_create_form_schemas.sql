-- 007: Form schemas and generation configs

CREATE TABLE form_schemas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  template_name TEXT NOT NULL,
  schema JSONB NOT NULL,
  num_fields INTEGER,
  template_file_id TEXT,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(org_id, template_name)
);

CREATE INDEX idx_form_schemas_org ON form_schemas(org_id);

CREATE TRIGGER trg_form_schemas_updated_at
  BEFORE UPDATE ON form_schemas
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE generation_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
  default_model TEXT NOT NULL DEFAULT 'gpt-5.4',
  temperature NUMERIC(3,2) NOT NULL DEFAULT 0.0,
  enable_few_shot BOOLEAN NOT NULL DEFAULT true,
  max_few_shot_examples INTEGER NOT NULL DEFAULT 3,
  default_edit_options JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_generation_configs_updated_at
  BEFORE UPDATE ON generation_configs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
