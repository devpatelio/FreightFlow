-- 014: Add fill pipeline statuses to documents check constraint

ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_status_check;

ALTER TABLE documents ADD CONSTRAINT documents_status_check
  CHECK (status IN (
    'uploaded', 'parsing', 'parsed',
    'extracting', 'extracted',
    'filling', 'filled',
    'generating', 'generated',
    'completed', 'error'
  ));
