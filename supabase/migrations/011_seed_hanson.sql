-- 011: Seed Hanson Chemicals data into new schema
-- This migration copies data from the legacy single-tenant tables into the new multi-tenant schema.
-- It creates the Hanson Chemicals organization and maps all existing data to it.
--
-- IMPORTANT: This migration assumes the legacy tables (accounts, seller_companies, etc.) still exist.
-- Run this AFTER deploying migrations 001-010. The legacy tables are left untouched for rollback safety.

DO $$
DECLARE
  v_org_id UUID;
  v_seller_id UUID;
  v_legacy_account RECORD;
  v_new_customer_id UUID;
  v_legacy_address RECORD;
  v_legacy_product RECORD;
  v_legacy_doc RECORD;
  v_new_doc_id UUID;
  v_legacy_schema RECORD;
  v_doc_id_map JSONB := '{}';
BEGIN

  -- 1. Create the Hanson Chemicals organization
  INSERT INTO organizations (name, slug, onboarding_completed_at)
  VALUES ('Hanson Chemicals', 'hanson-chemicals', now())
  RETURNING id INTO v_org_id;

  RAISE NOTICE 'Created organization: % (id: %)', 'Hanson Chemicals', v_org_id;

  -- 2. Create seller profile from HansonChemicals.txt content
  INSERT INTO seller_profiles (
    org_id, company_name, display_name, default_salesperson, phone,
    context_text, is_default
  ) VALUES (
    v_org_id,
    'Hanson Chemicals (11418793 Canada Inc)',
    'Hanson Chemicals',
    'Pan Patel',
    '4164578271',
    E'You are a logistics support assistant that fills out import logistics forms for my chemical distribution company Hanson Chemicals.\nAs a chemical distribution company, we specialize in taking purchase orders from various customers and filling out Bill of Lading and Packing Slips.\n\nVendor Address (Use this Address unless it''s asking for specifically Shipper Address)\nHANSON CHEMICALS (11418793 Canada Inc)\n22 Xavier Court\nBRAMPTON ON L6Y 5S1\nCANADA\n\nShipper Address:\nHANSON CHEMICALS\n21177 TOWER DRIVE N 169 W\nJACKSON WI 53037\n\nSalesperson: Pan Patel\nPhone Number: 4164578271\n\nYour job is to take Purchase Orders and fill in the relevant fields to generate Bill of lading and packing slip documents. It is imperative you focus on accuracy, simplicity, and pass in all the necessary information without hallucinating. If you are unsure about some information, please don''t assume and simply just provide a USER_FILL as a response.',
    true
  ) RETURNING id INTO v_seller_id;

  -- 3. Create org warehouse addresses
  INSERT INTO addresses (org_id, name, label, address_line, city, state, zip_code, country, address_type, is_default)
  VALUES
    (v_org_id, 'Hanson Chemicals - Canada', 'Vendor Address', '22 Xavier Court', 'Brampton', 'ON', 'L6Y 5S1', 'Canada', 'office', false),
    (v_org_id, 'Hanson Chemicals - US', 'Shipper Address', '21177 Tower Drive N 169 W', 'Jackson', 'WI', '53037', 'USA', 'warehouse', true);

  -- 4. Copy accounts → customers
  FOR v_legacy_account IN
    SELECT * FROM accounts
  LOOP
    INSERT INTO customers (org_id, company_name, customer_code, default_payment_terms, default_delivery_terms, notes)
    VALUES (
      v_org_id,
      v_legacy_account.company_name,
      v_legacy_account.customer_id,
      COALESCE(v_legacy_account.default_payment_terms, 'NET 90 DAYS'),
      COALESCE(v_legacy_account.default_delivery_terms, 'Free Carrier DESTINATION'),
      v_legacy_account.notes
    ) RETURNING id INTO v_new_customer_id;

    -- Store mapping for document migration: legacy account UUID → new customer UUID
    v_doc_id_map := v_doc_id_map || jsonb_build_object(v_legacy_account.id::text, v_new_customer_id::text);
  END LOOP;

  -- 5. Copy legacy addresses linked to accounts
  FOR v_legacy_address IN
    SELECT a.* FROM addresses a WHERE a.account_id IS NOT NULL
  LOOP
    INSERT INTO addresses (
      org_id, customer_id, name, label, address_line, city, state, zip_code, country,
      phone, email, address_type, is_default
    ) VALUES (
      v_org_id,
      (v_doc_id_map->>v_legacy_address.account_id::text)::UUID,
      COALESCE(v_legacy_address.name, 'Address'),
      v_legacy_address.label,
      COALESCE(v_legacy_address.address, ''),
      COALESCE(v_legacy_address.city, ''),
      COALESCE(v_legacy_address.state, ''),
      COALESCE(v_legacy_address.zip_code, ''),
      COALESCE(v_legacy_address.country, 'USA'),
      v_legacy_address.phone,
      v_legacy_address.email,
      COALESCE(v_legacy_address.address_type, 'shipping'),
      COALESCE(v_legacy_address.is_default, false)
    );
  END LOOP;

  -- 6. Copy products
  FOR v_legacy_product IN
    SELECT * FROM products
  LOOP
    INSERT INTO products (org_id, name, description, item_number, un_code, default_unit_type, default_handling_unit_type, notes)
    VALUES (
      v_org_id,
      v_legacy_product.name,
      v_legacy_product.description,
      v_legacy_product.item_number,
      v_legacy_product.un_code,
      COALESCE(v_legacy_product.default_unit_type, 'kg'),
      COALESCE(v_legacy_product.default_handling_unit_type, 'IBC'),
      v_legacy_product.notes
    );
  END LOOP;

  -- 7. Copy form schemas
  FOR v_legacy_schema IN
    SELECT * FROM form_schemas
  LOOP
    INSERT INTO form_schemas (org_id, template_name, schema, num_fields, template_file_id, description)
    VALUES (
      v_org_id,
      v_legacy_schema.template_name,
      v_legacy_schema.schema::JSONB,
      v_legacy_schema.num_fields,
      v_legacy_schema.template_file_id,
      v_legacy_schema.description
    );
  END LOOP;

  -- 8. Create default generation config
  INSERT INTO generation_configs (org_id) VALUES (v_org_id);

  RAISE NOTICE 'Hanson Chemicals seed complete. Org ID: %', v_org_id;

END $$;
