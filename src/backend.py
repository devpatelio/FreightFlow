import json
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from reducto import Reducto
from openai import OpenAI
import dotenv
import openai


class DocumentStore:
    
    def __init__(self, db_path: str = "db.json"):
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as f:
                json.dump({
                    "documents": [],
                    "form_schemas": {}
                }, f, indent=2)
    
    def _load_db(self) -> Dict:
        with open(self.db_path, 'r') as f:
            data = json.load(f)
            # Handle old format (list) and migrate to new format (dict)
            if isinstance(data, list):
                return {"documents": data, "form_schemas": {}}
            return data
    
    def _save_db(self, data: Dict):
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_document_by_name(self, document_name: str) -> Optional[Dict]:
        db = self._load_db()
        documents = db.get("documents", [])
        for doc in documents:
            if doc.get('document_name') == document_name:
                return doc
        return None
    
    def get_document_by_id(self, document_id: int) -> Optional[Dict]:
        db = self._load_db()
        documents = db.get("documents", [])
        for doc in documents:
            if doc.get('document_id') == document_id:
                return doc
        return None
    
    def add_document(self, document_name: str, file_id: str, result_json: Dict, 
                     studio_link: str = "", document_type: str = "PO") -> Dict:
        db = self._load_db()
        documents = db.get("documents", [])
        
        # Generate new document ID
        new_id = max([doc.get('document_id', 0) for doc in documents], default=0) + 1
        
        new_doc = {
            "document_id": new_id,
            "document_name": document_name,
            "file_id": file_id,
            "result_json": result_json,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "studio_link": studio_link,
            "document_type": document_type
        }
        
        documents.append(new_doc)
        db["documents"] = documents
        self._save_db(db)
        return new_doc
    
    def update_document(self, document_id: int, **kwargs) -> Optional[Dict]:
        db = self._load_db()
        documents = db.get("documents", [])
        
        for i, doc in enumerate(documents):
            if doc.get('document_id') == document_id:
                doc['updated_at'] = datetime.now().isoformat()
                for key, value in kwargs.items():
                    if key in doc:
                        doc[key] = value
                documents[i] = doc
                db["documents"] = documents
                self._save_db(db)
                return doc
        return None
    
    def list_all_documents(self) -> List[Dict]:
        db = self._load_db()
        return db.get("documents", [])
    
    def document_exists(self, document_name: str) -> bool:
        return self.get_document_by_name(document_name) is not None
    
    # ========================================================================
    # FORM SCHEMA OPERATIONS
    # ========================================================================
    
    def save_form_schema(self, template_name: str, schema: List[Dict], 
                         template_file_id: str = None, description: str = None) -> Dict:
        """Save a form schema for a template"""
        db = self._load_db()
        schemas = db.get("form_schemas", {})
        
        schema_data = {
            "template_name": template_name,
            "schema": schema,
            "template_file_id": template_file_id,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "num_fields": len(schema)
        }
        
        schemas[template_name] = schema_data
        db["form_schemas"] = schemas
        self._save_db(db)
        return schema_data
    
    def get_form_schema(self, template_name: str) -> Optional[Dict]:
        """Get form schema for a template"""
        db = self._load_db()
        schemas = db.get("form_schemas", {})
        return schemas.get(template_name)
    
    def list_form_schemas(self) -> List[Dict]:
        """List all form schemas"""
        db = self._load_db()
        schemas = db.get("form_schemas", {})
        return list(schemas.values())
    
    def delete_form_schema(self, template_name: str) -> bool:
        """Delete a form schema"""
        db = self._load_db()
        schemas = db.get("form_schemas", {})
        
        if template_name in schemas:
            del schemas[template_name]
            db["form_schemas"] = schemas
            self._save_db(db)
            return True
        return False


class Client:
    
    def __init__(self, reducto_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        dotenv.load_dotenv()
        self.reducto_api_key = reducto_api_key or os.getenv("REDUCTO_API_KEY")
        if not self.reducto_api_key:
            raise ValueError("REDUCTO_API_KEY not found in environment variables")
        self.client = Reducto(api_key=self.reducto_api_key)
        self.engine = openai.OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        if not self.engine:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.model = "gpt-5-2025-08-07"
    
    def upload_file(self, file_path: Path):
        try:
            upload = self.client.upload(file=file_path)
            print(f"✓ Uploaded: {file_path.name}")
            # The upload object is returned directly by Reducto
            # We'll extract file_id in process_document if needed
            return upload
        except Exception as e:
            print(f"✗ Error uploading {file_path.name}: {str(e)}")
            raise
            
    def fill_document_with_ai(self, template_path: str, parsed_po_data: Dict, 
                             document_type: str = "BOL") -> Dict:
        """
        Use AI to fill out a document template using parsed PO data
        
        Args:
            template_path: Path to the template file (BOL_Template.txt or PackingSlip_Template.txt)
            parsed_po_data: Parsed purchase order data containing chunks and blocks
            document_type: Type of document to generate ("BOL" or "PackingSlip")
        
        Returns:
            Dictionary with filled document data in JSON format
        """
        # Load the template prompt
        template_path = Path(template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r') as f:
            template_prompt = f.read()
        
        print(f"✓ Loaded template prompt from: {template_path}")
        print(f"  Template size: {len(template_prompt)} characters")
        
        # Load company context
        context_path = Path('templates/HansonChemicals.txt')
        if not context_path.exists():
            context_path = Path(__file__).parent.parent / 'templates' / 'HansonChemicals.txt'
        
        with open(context_path, 'r') as f:
            company_context = f.read()
        
        print(f"✓ Loaded company context from: {context_path}")
        print(f"  Context size: {len(company_context)} characters")
        
        # Extract text content from parsed PO
        po_text = self._extract_text_from_parsed_data(parsed_po_data)
        
        # Get current date for BOL number generation
        from datetime import datetime
        current_date = datetime.now()
        date_info = f"""
CURRENT DATE INFORMATION (use this for BOL number generation):
- Today's Date: {current_date.strftime('%Y-%m-%d')}
- BOL Number Format: {current_date.strftime('%Y%m%d')}XXX (where XXX is a 3-digit sequence starting from 001)
- Example BOL Number for today: {current_date.strftime('%Y%m%d')}001
"""
        
        # Construct the full prompt
        system_message = f"{company_context}\n\n{template_prompt}"
        user_message = f"""{date_info}

Here is the Purchase Order data to process:

{po_text}

Please extract the information and return ONLY a valid JSON object matching the {document_type} structure specified in the template. Do not include any explanatory text, markdown formatting, or code blocks - just the raw JSON."""
        
        # Call OpenAI API
        try:
            response = self.engine.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            print(f"✓ Successfully generated {document_type} using AI")
            return result_json
            
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing AI response as JSON: {str(e)}")
            print(f"Raw response: {result_text}")
            raise
        except Exception as e:
            print(f"✗ Error calling OpenAI API: {str(e)}")
            raise
    
    def _extract_text_from_parsed_data(self, parsed_data: Dict) -> str:
        """
        Extract readable text from parsed document data
        
        Args:
            parsed_data: Parsed document data with chunks and blocks
        
        Returns:
            Formatted text string
        """
        if not parsed_data or 'chunks' not in parsed_data:
            return ""
        
        text_parts = []
        for chunk in parsed_data.get('chunks', []):
            content = chunk.get('content', '')
            if content.strip():
                text_parts.append(content)
        
        return "\n\n".join(text_parts)
    
    def generate_form_schema(self, template_file_id: str, sample_instructions: str,
                           save_path: Optional[str] = None) -> List[Dict]:
        """
        Generate and optionally save a form schema from a template
        
        Args:
            template_file_id: Reducto file ID or URL of the template
            sample_instructions: Sample edit instructions to detect fields
            save_path: Optional path to save the schema JSON
        
        Returns:
            List of field definitions (form schema)
        """
        try:
            result = self.client.edit.run(
                document_url=template_file_id,
                edit_instructions=sample_instructions
            )
            
            # Convert Pydantic objects to dicts if needed
            if hasattr(result, 'form_schema'):
                schema_list = result.form_schema
                if schema_list and hasattr(schema_list[0], 'model_dump'):
                    schema_dicts = [field.model_dump() for field in schema_list]
                else:
                    schema_dicts = schema_list
            else:
                schema_dicts = []
            
            # Save schema if path provided
            if save_path and schema_dicts:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'w') as f:
                    json.dump(schema_dicts, f, indent=2)
                print(f"✓ Saved form schema to: {save_path}")
            
            return schema_dicts
            
        except Exception as e:
            print(f"✗ Error generating form schema: {str(e)}")
            raise
    
    def fill_template_document(self, template_file_id: str, fill_data: Dict,
                              form_schema: Optional[List[Dict]] = None,
                              save_path: Optional[str] = None,
                              enable_overflow_pages: bool = False,
                              template_name: Optional[str] = None) -> Dict:
        """
        Fill a template document with data using Reducto Edit

        Args:
            template_file_id: Reducto file ID or URL of the template
            fill_data: Dictionary containing the data to fill
            form_schema: Optional pre-generated form schema for faster processing
            save_path: Optional path to save the filled document
            enable_overflow_pages: Create appendix pages for long text (PDF only)
            template_name: Optional template name for saving generated schema

        Returns:
            Dictionary with document_url and optionally generated_schema
        """
        # Convert fill_data to natural language instructions
        instructions = self._data_to_instructions(fill_data)

        try:
            # Build edit options
            edit_options = {
                "enable_overflow_pages": enable_overflow_pages,
                "llm_provider_preference": "openai", 
                "color": "#000000"
            }

            # If caller didn't pass a schema but we have a template_name, try to load the saved schema
            # from Supabase. This prevents "No schema provided" runs which are inconsistent.
            if (not form_schema) and template_name:
                try:
                    from .supabase_service import get_supabase_service
                    supabase = get_supabase_service()
                    schema_data = supabase.get_form_schema(template_name)
                    if schema_data and schema_data.get("schema"):
                        form_schema = schema_data.get("schema")
                        print(f"✓ Loaded form schema from Supabase in fill_template_document ({schema_data.get('num_fields')} fields)")
                except Exception as e:
                    # Non-fatal; we'll fall back to detection
                    print(f"⚠ Could not load form schema from Supabase in fill_template_document: {e}")

            # Call Reducto Edit API
            if form_schema:
                # For Packing Slip: deterministically prefill schema values so critical header-row
                # fields (ORDER DATE / ORDER # / PURCHASE ORDER # / CUSTOMER CONTACT) never get dropped.
                # This avoids LLM inconsistency when mapping instructions to the blue order-info row.
                if template_name and template_name.lower() == "packingslip_template.pdf":
                    form_schema = self._prefill_packing_slip_form_schema(form_schema, fill_data)

                print(f"✓ Using existing form schema ({len(form_schema)} fields)")
                result = self.client.edit.run(
                    document_url=template_file_id,
                    edit_instructions=instructions,
                    edit_options=edit_options,
                    form_schema=form_schema
                )
                generated_schema = None
            else:
                print(f"⚠ No schema provided - Reducto will detect fields (slower)")
                result = self.client.edit.run(
                    document_url=template_file_id,
                    edit_instructions=instructions,
                    edit_options=edit_options
                )

                # Extract and convert schema from result
                generated_schema = None
                if hasattr(result, 'form_schema') and result.form_schema:
                    # Convert Pydantic objects to dicts
                    if hasattr(result.form_schema[0], 'model_dump'):
                        generated_schema = [field.model_dump() for field in result.form_schema]
                    else:
                        generated_schema = result.form_schema

                    print(f"✓ Generated form schema with {len(generated_schema)} fields")

                    # Save schema if template name provided
                    if template_name:
                        try:
                            from .supabase_service import get_supabase_service
                            supabase = get_supabase_service()
                            supabase.save_form_schema(
                                template_name=template_name,
                                schema=generated_schema,
                                template_file_id=template_file_id,
                                description=f"Auto-generated schema from first run"
                            )
                            print(f"✓ Saved form schema to Supabase: {template_name}")
                        except Exception as e:
                            print(f"⚠ Warning: Could not save form schema: {str(e)}")

            document_url = result.document_url
            print(f"✓ Document filled successfully")
            print(f"  Credits used: {result.usage.credits if hasattr(result, 'usage') else 'N/A'}")

            # Download and save if path provided
            if save_path and document_url:
                self._download_document(document_url, save_path)

            return {
                'document_url': document_url,
                'generated_schema': generated_schema,
                'used_existing_schema': form_schema is not None
            }

        except Exception as e:
            print(f"✗ Error filling template: {str(e)}")
            raise

    def _prefill_packing_slip_form_schema(self, form_schema: List[Dict], fill_data: Dict) -> List[Dict]:
        """
        Prefill Packing Slip schema fields by matching on schema 'description' prefixes.
        This makes critical fields deterministic (no LLM guessing), especially the blue order-info row.
        """
        import copy
        import re

        schema = copy.deepcopy(form_schema)

        def as_str(v):
            if v is None:
                return ""
            return str(v)

        # Canonical values (stringified)
        header_values = {
            "DATE": as_str(fill_data.get("date")),
            "CUSTOMER ID": as_str(fill_data.get("customer_id")),
            "SALESPERSON": as_str(fill_data.get("salesperson")),
        }

        order_info_values = {
            "ORDER DATE": as_str(fill_data.get("order_date")),
            "ORDER #": as_str(fill_data.get("order_number")),
            "PURCHASE ORDER #": as_str(fill_data.get("purchase_order_number")),
            "CUSTOMER CONTACT": as_str(fill_data.get("customer_contact")),
        }

        ship_from = fill_data.get("ship_from") or {}
        ship_to = fill_data.get("ship_to") or {}
        bill_to = fill_data.get("bill_to") or {}
        has_bill_to = isinstance(fill_data.get("bill_to"), dict) and any((fill_data.get("bill_to") or {}).values())

        ship_from_city_state_zip = " ".join(
            [as_str(ship_from.get("city")).strip(), as_str(ship_from.get("state")).strip(), as_str(ship_from.get("zip_code")).strip()]
        ).strip()
        ship_city_state_zip = " ".join(
            [as_str(ship_to.get("city")).strip(), as_str(ship_to.get("state")).strip(), as_str(ship_to.get("zip_code")).strip()]
        ).strip()
        bill_city_state_zip = " ".join(
            [as_str(bill_to.get("city")).strip(), as_str(bill_to.get("state")).strip(), as_str(bill_to.get("zip_code")).strip()]
        ).strip()

        items = fill_data.get("items") or []

        # Track whether we successfully matched critical order-row fields (debug)
        matched_order = {k: False for k in order_info_values.keys()}

        def extract_row_num(desc: str) -> int | None:
            # Examples: "(1st row shown)", "(2nd row shown)", "(12th row/last listed)"
            m = re.search(r"\((\d+)(st|nd|rd|th)\s+row", desc)
            if not m:
                return None
            try:
                return int(m.group(1))
            except Exception:
                return None

        def canonical_field_key(description: str) -> str:
            """
            Convert schema description into a canonical key for matching.
            Example: "ORDER DATE:. Date the order was placed..." -> "ORDER DATE"
                     "SHIP TO: Company Name:. ..." -> "SHIP TO: COMPANY NAME"
            """
            head = (description or "").strip().split(".", 1)[0].strip()
            # Remove trailing colon(s)
            head = re.sub(r":\s*$", "", head)
            # Normalize whitespace + uppercase
            head = re.sub(r"\s+", " ", head).upper()
            return head

        for field in schema:
            desc = (field.get("description") or "").strip()
            if not desc:
                continue

            key = canonical_field_key(desc)

            # Simple header fields
            if key in header_values:
                field["value"] = header_values[key]
                continue

            # Order info row (critical)
            if key in order_info_values:
                field["value"] = order_info_values[key]
                matched_order[key] = True
                continue

            # Address subfields
            if key.startswith("SHIP FROM:"):
                sub = key.replace("SHIP FROM:", "", 1).strip()
                if sub in ("COMPANY NAME", "COMPANY NAME:"):
                    field["value"] = as_str(ship_from.get("name"))
                elif sub in ("STREET ADDRESS", "STREET ADDRESS:"):
                    field["value"] = as_str(ship_from.get("address"))
                elif sub in ("CITY/STATE/ZIP CODE", "CITY/STATE/ZIP CODE:"):
                    field["value"] = ship_from_city_state_zip
                elif sub in ("COUNTRY", "COUNTRY:"):
                    field["value"] = as_str(ship_from.get("country"))
                continue

            if key.startswith("SHIP TO:"):
                sub = key.replace("SHIP TO:", "", 1).strip()
                if sub in ("COMPANY NAME", "COMPANY NAME:"):
                    field["value"] = as_str(ship_to.get("name"))
                elif sub in ("STREET ADDRESS", "STREET ADDRESS:"):
                    field["value"] = as_str(ship_to.get("address"))
                elif sub in ("CITY/STATE/ZIP CODE", "CITY/STATE/ZIP CODE:"):
                    field["value"] = ship_city_state_zip
                elif sub in ("COUNTRY", "COUNTRY:"):
                    field["value"] = as_str(ship_to.get("country"))
                continue

            if key.startswith("BILL TO:"):
                sub = key.replace("BILL TO:", "", 1).strip()
                if not has_bill_to:
                    field["value"] = ""
                    continue
                if sub in ("COMPANY NAME", "COMPANY NAME:"):
                    field["value"] = as_str(bill_to.get("name"))
                elif sub in ("STREET ADDRESS", "STREET ADDRESS:"):
                    field["value"] = as_str(bill_to.get("address"))
                elif sub in ("CITY/STATE/ZIP CODE", "CITY/STATE/ZIP CODE:"):
                    field["value"] = bill_city_state_zip
                elif sub in ("COUNTRY", "COUNTRY:"):
                    field["value"] = as_str(bill_to.get("country"))
                continue

            # Line items (row-specific)
            if key.startswith("ITEM # (LINE ITEM)") or key.startswith("DESCRIPTION (LINE ITEM)") or key.startswith("ORDER QTY (LINE ITEM)") or key.startswith("SHIP QTY (LINE ITEM)"):
                row_num = extract_row_num(desc)
                if not row_num:
                    continue
                idx = row_num - 1
                if idx < 0 or idx >= len(items):
                    field["value"] = ""
                    continue
                item = items[idx] or {}
                if key.startswith("ITEM # (LINE ITEM)"):
                    field["value"] = as_str(item.get("item_number"))
                elif key.startswith("DESCRIPTION (LINE ITEM)"):
                    field["value"] = as_str(item.get("description"))
                elif key.startswith("ORDER QTY (LINE ITEM)"):
                    field["value"] = as_str(item.get("order_qty"))
                elif key.startswith("SHIP QTY (LINE ITEM)"):
                    field["value"] = as_str(item.get("ship_qty"))

        # Debug: if schema didn't match those order-info fields, log it so we can fix schema text patterns.
        # This is the #1 reason they stay blank even though the data exists.
        missing = [k for k, ok in matched_order.items() if not ok and order_info_values.get(k)]
        if missing:
            print(f"⚠ PackingSlip schema prefill: could not match order-info fields in schema: {missing}")

        return schema
    
    def _wrap_text(self, text: str, width: int = 60) -> str:
        """
        Wrap text to fit within PDF form fields by adding line breaks

        Args:
            text: Text to wrap
            width: Maximum characters per line (default: 60)

        Returns:
            Text with line breaks added
        """
        if not text or len(str(text)) <= width:
            return str(text)

        import textwrap
        # Wrap text at word boundaries, preserving existing line breaks
        text = str(text)
        lines = text.split('\n')
        wrapped_lines = []

        for line in lines:
            if len(line) <= width:
                wrapped_lines.append(line)
            else:
                # Wrap long lines
                wrapped = textwrap.fill(line, width=width, break_long_words=False, break_on_hyphens=False)
                wrapped_lines.append(wrapped)

        return '\n'.join(wrapped_lines)

    def _data_to_instructions(self, data: Dict) -> str:
        """
        Convert structured data dictionary to natural language instructions
        
        Detects document type and uses specialized formatters for better accuracy
        """
        # Detect document type
        is_packing_slip = 'customer_id' in data or 'purchase_order_number' in data
        is_bol = 'bol_number' in data or 'bol_date' in data
        
        if is_packing_slip and not is_bol:
            return self._packing_slip_instructions(data)
        elif is_bol:
            return self._bol_instructions(data)
        else:
            return self._generic_instructions(data)
    
    def _packing_slip_instructions(self, data: Dict) -> str:
        """
        Generate instructions for Packing Slip that match the form schema exactly
        """
        instructions = []
        instructions.append("Fill this Packing Slip form with the following information:")
        instructions.append("")
        
        # HEADER SECTION - Match schema descriptions exactly
        instructions.append("HEADER SECTION (top right corner):")
        if data.get('date'):
            instructions.append(f"DATE field (date format): {data['date']}")
        
        if data.get('customer_id'):
            instructions.append(f"CUSTOMER ID field (text): {data['customer_id']}")
        
        if data.get('salesperson'):
            instructions.append(f"SALESPERSON field (text): {data['salesperson']}")
        
        instructions.append("")
        
        # BILL TO SECTION
        instructions.append("BILL TO SECTION:")
        bill_to = data.get('bill_to')
        if bill_to and isinstance(bill_to, dict) and any(bill_to.values()):
            if bill_to.get('name'):
                instructions.append(f"BILL TO: Company Name: {bill_to['name']}")
            if bill_to.get('address'):
                instructions.append(f"BILL TO: Street Address: {bill_to['address']}")
            city = bill_to.get('city', '')
            state = bill_to.get('state', '')
            zip_code = bill_to.get('zip_code', '')
            if city or state or zip_code:
                instructions.append(f"BILL TO: City/State/Zip Code: {city} {state} {zip_code}".strip())
            if bill_to.get('country'):
                instructions.append(f"BILL TO: Country: {bill_to['country']}")
        else:
            instructions.append("Leave all BILL TO fields blank")
        
        instructions.append("")
        
        # SHIP FROM SECTION
        instructions.append("SHIP FROM SECTION:")
        ship_from = data.get('ship_from')
        if ship_from and isinstance(ship_from, dict):
            if ship_from.get('name'):
                instructions.append(f"SHIP FROM: Company Name: {ship_from['name']}")
            if ship_from.get('address'):
                instructions.append(f"SHIP FROM: Street Address: {ship_from['address']}")
            city = ship_from.get('city', '')
            state = ship_from.get('state', '')
            zip_code = ship_from.get('zip_code', '')
            if city or state or zip_code:
                instructions.append(f"SHIP FROM: City/State/Zip Code: {city} {state} {zip_code}".strip())
            if ship_from.get('country'):
                instructions.append(f"SHIP FROM: Country: {ship_from['country']}")
        
        instructions.append("")
        
        # SHIP TO SECTION - This should always be filled
        instructions.append("SHIP TO SECTION:")
        ship_to = data.get('ship_to')
        if ship_to and isinstance(ship_to, dict):
            if ship_to.get('name'):
                instructions.append(f"SHIP TO: Company Name: {ship_to['name']}")
            if ship_to.get('address'):
                instructions.append(f"SHIP TO: Street Address: {ship_to['address']}")
            city = ship_to.get('city', '')
            state = ship_to.get('state', '')
            zip_code = ship_to.get('zip_code', '')
            if city or state or zip_code:
                instructions.append(f"SHIP TO: City/State/Zip Code: {city} {state} {zip_code}".strip())
            if ship_to.get('country'):
                instructions.append(f"SHIP TO: Country: {ship_to['country']}")
        
        instructions.append("")
        
        # ORDER INFORMATION ROW - Always include all fields explicitly
        instructions.append("ORDER INFORMATION ROW (below SHIP TO section):")
        
        # ORDER DATE field
        order_date = data.get('order_date', '')
        if order_date:
            instructions.append(f"Fill ORDER DATE field with: {order_date}")
        else:
            instructions.append(f"ORDER DATE: Leave blank")
        
        # ORDER # field
        order_number = data.get('order_number', '')
        if order_number:
            instructions.append(f"Fill ORDER # field with: {order_number}")
        else:
            instructions.append(f"ORDER #: Leave blank")
        
        # PURCHASE ORDER # field
        po_number = data.get('purchase_order_number', '')
        if po_number:
            instructions.append(f"Fill PURCHASE ORDER # field with: {po_number}")
        else:
            instructions.append(f"PURCHASE ORDER #: Leave blank")
        
        # CUSTOMER CONTACT field
        customer_contact = data.get('customer_contact', '')
        if customer_contact:
            instructions.append(f"Fill CUSTOMER CONTACT field with: {customer_contact}")
        else:
            instructions.append(f"CUSTOMER CONTACT: Leave blank")
        
        instructions.append("")
        
        # LINE ITEMS - Match schema row descriptions
        instructions.append("LINE ITEMS TABLE (columns: ITEM #, DESCRIPTION, ORDER QTY, SHIP QTY):")
        items = data.get('items', [])
        
        row_labels = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th']
        
        for idx, item in enumerate(items):
            if idx < len(row_labels):
                row_label = row_labels[idx]
            else:
                row_label = f"{idx + 1}th"
            
            instructions.append(f"Line item ({row_label} row):")
            
            if item.get('item_number'):
                instructions.append(f"  ITEM # (product code): {item['item_number']}")
            
            if item.get('description'):
                desc = self._wrap_text(item['description'], width=60)
                instructions.append(f"  DESCRIPTION (product name): {desc}")
            
            if item.get('order_qty') is not None:
                instructions.append(f"  ORDER QTY (numeric quantity only): {item['order_qty']}")
            
            if item.get('ship_qty') is not None:
                instructions.append(f"  SHIP QTY (numeric quantity only): {item['ship_qty']}")
            
            instructions.append("")
        
        # TOTAL
        if data.get('total'):
            instructions.append(f"TOTAL: {data['total']}")
        
        return "\n".join(instructions)
    
    def _bol_instructions(self, data: Dict) -> str:
        """
        Generate instructions for BOL
        """
        instructions = []
        instructions.append("Fill this Bill of Lading with the following information:")
        instructions.append("")
        
        # BOL Header
        if data.get('bol_number'):
            instructions.append(f"BOL NUMBER (digits only): {data['bol_number']}")
        if data.get('bol_date'):
            instructions.append(f"BOL DATE (YYYY-MM-DD): {data['bol_date']}")
        
        # Carrier
        if data.get('carrier_name'):
            instructions.append(f"CARRIER NAME: {data['carrier_name']}")
        
        # Ship From
        ship_from = data.get('ship_from')
        if ship_from:
            instructions.append("")
            instructions.append("SHIP FROM:")
            if ship_from.get('name'):
                instructions.append(f"  Company: {ship_from['name']}")
            if ship_from.get('address'):
                instructions.append(f"  Address: {ship_from['address']}")
            city_state_zip = f"{ship_from.get('city', '')} {ship_from.get('state', '')} {ship_from.get('zip_code', '')}".strip()
            if city_state_zip:
                instructions.append(f"  City/State/Zip: {city_state_zip}")
        
        # Ship To
        ship_to = data.get('ship_to')
        if ship_to:
            instructions.append("")
            instructions.append("SHIP TO:")
            if ship_to.get('name'):
                instructions.append(f"  Company: {ship_to['name']}")
            if ship_to.get('address'):
                instructions.append(f"  Address: {ship_to['address']}")
            city_state_zip = f"{ship_to.get('city', '')} {ship_to.get('state', '')} {ship_to.get('zip_code', '')}".strip()
            if city_state_zip:
                instructions.append(f"  City/State/Zip: {city_state_zip}")
        
        # Products
        products = data.get('products', [])
        if products:
            instructions.append("")
            instructions.append("PRODUCTS (be strict about types: counts vs weights vs units):")
            for i, product in enumerate(products, 1):
                instructions.append(f"  Product {i}:")
                if product.get('name'):
                    instructions.append(f"    Name (text): {product['name']}")
                if product.get('description'):
                    instructions.append(f"    Description (text): {self._wrap_text(product['description'], width=60)}")
                if product.get('item_number'):
                    instructions.append(f"    Item Number (text/code): {product['item_number']}")
                if product.get('un_code'):
                    instructions.append(f"    UN Code (text): {product['un_code']}")
                handling = product.get('handling_unit') or {}
                if isinstance(handling, dict):
                    if handling.get('quantity') is not None:
                        instructions.append(f"    Handling Unit Quantity (integer count only): {handling.get('quantity')}")
                    if handling.get('type'):
                        instructions.append(f"    Handling Unit Type (IBC/Drum/Pallet/Box text only): {handling.get('type')}")
                pkg = product.get('package') or {}
                if isinstance(pkg, dict):
                    if pkg.get('quantity') is not None:
                        instructions.append(f"    Package/Weight Quantity (numeric only): {pkg.get('quantity')}")
                    if pkg.get('type'):
                        instructions.append(f"    Package/Weight Unit (kg/lb text only): {pkg.get('type')}")
                if product.get('weight') is not None:
                    instructions.append(f"    Total Weight (numeric only): {product.get('weight')}")

        # Orders (table-like fields) — this is where column swaps usually happen
        orders = data.get('orders', [])
        if orders:
            instructions.append("")
            instructions.append("ORDERS (be strict: counts are integers; weights are numbers; units are separate):")
            for i, order in enumerate(orders, 1):
                instructions.append(f"  Order {i}:")
                if order.get('customer_id'):
                    instructions.append(f"    Customer ID (text): {order.get('customer_id')}")
                if order.get('po_number'):
                    instructions.append(f"    PO Number (text): {order.get('po_number')}")
                if order.get('sales_order_number'):
                    instructions.append(f"    Sales Order Number (digits/text): {order.get('sales_order_number')}")
                if order.get('material_name'):
                    instructions.append(f"    Material Name (text): {order.get('material_name')}")
                if order.get('num_packages') is not None:
                    instructions.append(f"    Number of Packages (integer count only): {order.get('num_packages')}")
                if order.get('weight') is not None:
                    instructions.append(f"    Weight (numeric only): {order.get('weight')}")
                if order.get('weight_unit'):
                    instructions.append(f"    Weight Unit (kg/lb text only): {order.get('weight_unit')}")
                if order.get('country_of_origin'):
                    instructions.append(f"    Country of Origin (text): {order.get('country_of_origin')}")
                if order.get('customer_po'):
                    instructions.append(f"    Customer PO (text): {order.get('customer_po')}")
                if order.get('additional_shipper_info'):
                    instructions.append(f"    Additional Shipper Info (text): {self._wrap_text(order.get('additional_shipper_info'), width=60)}")
        
        # Special Instructions
        if data.get('special_instructions'):
            instructions.append("")
            wrapped = self._wrap_text(data['special_instructions'], width=60)
            instructions.append(f"SPECIAL INSTRUCTIONS: {wrapped}")
        
        return "\n".join(instructions)
    
    def _generic_instructions(self, data: Dict) -> str:
        """
        Fallback generic instructions
        """
        instructions = []
        instructions.append("Fill this form with the following information:")
        instructions.append("")
        
        def process_dict(d, prefix=""):
            for key, value in d.items():
                field_name = key.replace('_', ' ').title()
                full_key = f"{prefix}{field_name}" if prefix else field_name
                
                if isinstance(value, dict):
                    process_dict(value, f"{full_key} - ")
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        for i, item in enumerate(value, 1):
                            process_dict(item, f"{full_key} {i} - ")
                    else:
                        value_str = ', '.join(str(v) for v in value) if value else ''
                        instructions.append(f"{full_key}: {value_str}")
                else:
                    if value is None:
                        instructions.append(f"{full_key}: [Leave blank]")
                    else:
                        instructions.append(f"{full_key}: {value}")
        
        process_dict(data)
        return "\n".join(instructions)
    
    def _download_document(self, url: str, save_path: str):
        """
        Download a document from URL and save to disk
        
        Args:
            url: URL of the document
            save_path: Local path to save the document
        """
        import requests
        
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.get(url)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✓ Downloaded document to: {save_path}")
            
        except Exception as e:
            print(f"✗ Error downloading document: {str(e)}")
            raise


    def parse_file(self, upload) -> Dict:
        try:
            result = self.client.parse.run(
                input=upload,
                formatting={
                    "table_output_format": "json"
                }
            )
            
            print(f"✓ Parsed document successfully")
            print(f"  Job ID: {result.job_id}")
            print(f"  Pages processed: {result.usage.num_pages}")
            print(f"  Credits used: {result.usage.credits}")
            print(f"  Number of chunks: {len(result.result.chunks)}")
            
            # Convert chunks to serializable format
            chunks_data = []
            for chunk in result.result.chunks:
                chunk_dict = {
                    "content": chunk.content,
                    "blocks": []
                }
                
                # Convert blocks to dicts
                for block in chunk.blocks:
                    # Access block attributes using dot notation (Reducto objects)
                    block_dict = {
                        "type": block.type if hasattr(block, 'type') else None,
                        "content": block.content if hasattr(block, 'content') else None,
                        "bbox": {
                            "page": block.bbox.page,
                            "left": block.bbox.left,
                            "top": block.bbox.top,
                            "width": block.bbox.width,
                            "height": block.bbox.height
                        } if hasattr(block, 'bbox') and block.bbox else None,
                        "confidence": block.confidence if hasattr(block, 'confidence') else None
                    }
                    chunk_dict["blocks"].append(block_dict)
                
                chunks_data.append(chunk_dict)
            
            # Return structured data
            parsed_data = {
                "job_id": result.job_id,
                "duration": result.duration if hasattr(result, 'duration') else None,
                "usage": {
                    "num_pages": result.usage.num_pages,
                    "credits": result.usage.credits
                },
                "chunks": chunks_data,
                "studio_link": result.studio_link
            }
            
            return parsed_data
        except Exception as e:
            print(f"✗ Error parsing document: {str(e)}")
            raise


class DocumentManager:

    def __init__(self, db_path: str = None, use_supabase: bool = True):
        """
        Initialize DocumentManager with Supabase or local storage

        Args:
            db_path: Path to local db.json (deprecated, kept for backwards compatibility)
            use_supabase: If True, use Supabase for storage (default). Set to False to use local JSON.
        """
        from .supabase_service import get_supabase_service

        self.use_supabase = use_supabase

        if use_supabase:
            self.supabase = get_supabase_service()
            self.store = None  # Deprecated, kept for compatibility
        else:
            # Fallback to local storage (deprecated)
            if db_path is None:
                db_path = Path(__file__).parent.parent / "db.json"
            self.store = DocumentStore(str(db_path))
            self.supabase = None

        self.parser = None

    def _init_parser(self):
        if self.parser is None:
            self.parser = Client()
    
    def process_document(self, file_path: str, document_type: str = "PO",
                        force_reparse: bool = False) -> Dict:

        file_path = Path(file_path)
        document_name = file_path.name

        # Check if document exists (using Supabase or local store)
        if self.use_supabase:
            # Search for existing document by name in Supabase
            docs = self.supabase.list_documents()
            existing_doc = None
            for doc in docs:
                if doc.get('document_name') == document_name:
                    existing_doc = doc
                    break
        else:
            existing_doc = self.store.get_document_by_name(document_name)

        if existing_doc and not force_reparse:
            print(f"  Document '{document_name}' already parsed. Using cached version.")
            print(f"  Document ID: {existing_doc['document_id']}")
            print(f"  Parsed on: {existing_doc.get('created_at', 'N/A')}")
            return existing_doc

        print(f"\n📄 Processing: {document_name}")
        self._init_parser()

        upload = self.parser.upload_file(file_path)
        result = self.parser.parse_file(upload)

        # Extract file_id from upload object (it could be the object itself or have a file_id attribute)
        if hasattr(upload, 'file_id'):
            file_id = upload.file_id
        elif hasattr(upload, 'id'):
            file_id = upload.id
        else:
            file_id = str(upload) if upload else ''

        studio_link = result.get('studio_link', '')
        result_json = result

        if existing_doc and force_reparse:
            print(f"Updating existing document (ID: {existing_doc.get('document_id') or existing_doc.get('id')})")
            if self.use_supabase:
                # Supabase doesn't support updating via document_id for this method
                # We need to create a new document instead
                print(f"Warning: Supabase mode doesn't support force_reparse. Creating new document.")
                # Fall through to create new document
            else:
                updated_doc = self.store.update_document(
                    existing_doc['document_id'],
                    file_id=file_id,
                    result_json=result_json,
                    studio_link=studio_link
                )
                return updated_doc

        # Create new document
        print(f"Adding new document to database")
        if self.use_supabase:
            # Generate document_id (max existing + 1)
            all_docs = self.supabase.list_documents()
            max_id = max([doc.get('document_id', 0) for doc in all_docs], default=0)
            new_doc_id = max_id + 1

            # Return document data - app.py will create the Supabase record
            return {
                'document_id': new_doc_id,
                'document_name': document_name,
                'file_id': file_id,
                'result_json': result_json,
                'studio_link': studio_link,
                'document_type': document_type
            }
        else:
            new_doc = self.store.add_document(
                document_name=document_name,
                file_id=file_id,
                result_json=result_json,
                studio_link=studio_link,
                document_type=document_type
            )
            return new_doc
    
    def get_document(self, document_name: str = None, document_id: int = None) -> Optional[Dict]:
        if self.use_supabase:
            doc = None
            if document_id:
                doc = self.supabase.get_document(document_id)
            else:
                # Search by name - less efficient but works
                docs = self.supabase.list_documents()
                for d in docs:
                    if d.get('document_name') == document_name:
                        doc = d
                        break

            # Normalize field names: Supabase uses 'parsed_data', but code expects 'result_json'
            if doc and 'parsed_data' in doc and 'result_json' not in doc:
                doc['result_json'] = doc['parsed_data']

            return doc
        else:
            if document_name:
                return self.store.get_document_by_name(document_name)
            elif document_id:
                return self.store.get_document_by_id(document_id)
            return None

    def list_documents(self) -> List[Dict]:
        if self.use_supabase:
            return self.supabase.list_documents()
        else:
            return self.store.list_all_documents()
    
    def get_parsed_data(self, document_name: str = None, document_id: int = None) -> Optional[Dict]:
        doc = self.get_document(document_name, document_id)
        return doc.get('result_json') if doc else None
    
    def query_field(self, document_name: str, field_path: str) -> Optional[any]:
        
        parsed_data = self.get_parsed_data(document_name=document_name)
        if not parsed_data:
            return None
        
        keys = field_path.split('.')
        value = parsed_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def get_chunks(self, document_name: str = None, document_id: int = None) -> Optional[List[Dict]]:
        """Get all chunks from a parsed document"""
        parsed_data = self.get_parsed_data(document_name, document_id)
        if parsed_data and 'chunks' in parsed_data:
            return parsed_data['chunks']
        return None
    
    def get_blocks_by_type(self, document_name: str, block_type: str) -> List[Dict]:
        """
        Get all blocks of a specific type from a document
        
        Args:
            document_name: Name of the document
            block_type: Type of block (e.g., 'Table', 'Title', 'Text', 'Header')
        
        Returns:
            List of blocks matching the type
        """
        chunks = self.get_chunks(document_name=document_name)
        if not chunks:
            return []
        
        matching_blocks = []
        for chunk in chunks:
            for block in chunk.get('blocks', []):
                if block.get('type') == block_type:
                    matching_blocks.append(block)
        
        return matching_blocks
    
    def get_tables(self, document_name: str) -> List[Dict]:
        """Get all tables from a document"""
        return self.get_blocks_by_type(document_name, 'Table')
    
    def search_content(self, document_name: str, search_term: str, case_sensitive: bool = False) -> List[Dict]:
        """
        Search for content in document chunks
        
        Args:
            document_name: Name of the document
            search_term: Text to search for
            case_sensitive: Whether search should be case sensitive
        
        Returns:
            List of chunks containing the search term
        """
        chunks = self.get_chunks(document_name=document_name)
        if not chunks:
            return []
        
        matching_chunks = []
        search = search_term if case_sensitive else search_term.lower()
        
        for chunk in chunks:
            content = chunk.get('content', '')
            compare_content = content if case_sensitive else content.lower()
            
            if search in compare_content:
                matching_chunks.append(chunk)
        
        return matching_chunks
    
    def get_full_text(self, document_name: str) -> str:
        """Get all text content from a document concatenated together"""
        chunks = self.get_chunks(document_name=document_name)
        if not chunks:
            return ""
        
        return "\n\n".join(chunk.get('content', '') for chunk in chunks)
    
    def generate_bol_from_po(self, po_document_name: str = None, 
                            po_document_id: int = None,
                            save_to_db: bool = True) -> Dict:
        """
        Generate a Bill of Lading from a parsed Purchase Order using AI
        
        Args:
            po_document_name: Name of the PO document in database
            po_document_id: ID of the PO document in database
            save_to_db: Whether to save the generated BOL to database
        
        Returns:
            Dictionary containing the filled BOL data
        """
        self._init_parser()
        
        # Get the PO document
        po_doc = self.get_document(po_document_name, po_document_id)
        if not po_doc:
            raise ValueError(f"Purchase Order not found (name: {po_document_name}, id: {po_document_id})")
        
        # Get the parsed PO data
        parsed_po = po_doc.get('result_json')
        if not parsed_po:
            raise ValueError(f"Purchase Order has no parsed data")
        
        # Get template path
        template_path = Path(__file__).parent.parent / 'templates' / 'BOL_Template.txt'
        if not template_path.exists():
            template_path = Path('templates/BOL_Template.txt')
        
        # Generate BOL using AI
        bol_data = self.parser.fill_document_with_ai(
            template_path=str(template_path),
            parsed_po_data=parsed_po,
            document_type="BOL"
        )
        
        # Optionally save to database
        if save_to_db:
            po_name = po_doc['document_name']
            bol_name = f"BOL_{po_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if self.use_supabase:
                # When using Supabase, we don't save intermediate JSON data
                # Only final filled PDFs are saved via app.py
                print(f"⚠ Warning: save_to_db not supported with Supabase (JSON data not persisted)")
            else:
                self.store.add_document(
                    document_name=bol_name,
                    file_id="",  # No file_id for generated documents
                    result_json=bol_data,
                    studio_link="",
                    document_type="BOL"
                )
                print(f"✓ Saved generated BOL as: {bol_name}")
        
        return bol_data
    
    def generate_packing_slip_from_po(self, po_document_name: str = None,
                                     po_document_id: int = None,
                                     save_to_db: bool = True) -> Dict:
        """
        Generate a Packing Slip from a parsed Purchase Order using AI
        
        Args:
            po_document_name: Name of the PO document in database
            po_document_id: ID of the PO document in database
            save_to_db: Whether to save the generated packing slip to database
        
        Returns:
            Dictionary containing the filled packing slip data
        """
        self._init_parser()
        
        # Get the PO document
        po_doc = self.get_document(po_document_name, po_document_id)
        if not po_doc:
            raise ValueError(f"Purchase Order not found (name: {po_document_name}, id: {po_document_id})")
        
        # Get the parsed PO data
        parsed_po = po_doc.get('result_json')
        if not parsed_po:
            raise ValueError(f"Purchase Order has no parsed data")
        
        # Get template path
        template_path = Path(__file__).parent.parent / 'templates' / 'PackingSlip_Template.txt'
        if not template_path.exists():
            template_path = Path('templates/PackingSlip_Template.txt')
        
        # Generate Packing Slip using AI
        packing_slip_data = self.parser.fill_document_with_ai(
            template_path=str(template_path),
            parsed_po_data=parsed_po,
            document_type="PackingSlip"
        )
        
        # Optionally save to database
        if save_to_db:
            po_name = po_doc['document_name']
            ps_name = f"PackingSlip_{po_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if self.use_supabase:
                # When using Supabase, we don't save intermediate JSON data
                # Only final filled PDFs are saved via app.py
                print(f"⚠ Warning: save_to_db not supported with Supabase (JSON data not persisted)")
            else:
                self.store.add_document(
                    document_name=ps_name,
                    file_id="",  # No file_id for generated documents
                    result_json=packing_slip_data,
                    studio_link="",
                    document_type="PackingSlip"
                )
                print(f"✓ Saved generated Packing Slip as: {ps_name}")
        
        return packing_slip_data
    
    def generate_and_fill_bol(self, po_document_name: str = None,
                             po_document_id: int = None,
                             bol_template_file_id: str = None,
                             form_schema_path: str = None,
                             use_saved_schema: bool = True,
                             output_filename: str = None,
                             address_overrides: Dict = None,
                             bol_number_override: str = None,
                             bol_data: Dict = None) -> Dict:
        """
        Generate BOL data from PO and fill the BOL template
        
        Args:
            po_document_name: Name of the PO document in database
            po_document_id: ID of the PO document in database
            bol_template_file_id: Reducto file ID of BOL template (if not provided, will upload)
            form_schema_path: Path to saved form schema JSON (optional, for faster processing)
            use_saved_schema: Whether to use schema saved in database (default: True)
            output_filename: Name for the output file (auto-generated if not provided)
            address_overrides: Dictionary with 'ship_from' and/or 'ship_to' address overrides
            bol_number_override: Custom BOL number to use instead of AI-generated one
            bol_data: Pre-generated BOL data (if provided, skips AI generation)
        
        Returns:
            Dictionary with BOL data and filled document URL
        """
        self._init_parser()
        
        # Get PO document
        po_doc = self.get_document(po_document_name, po_document_id)
        if not po_doc:
            raise ValueError(f"Purchase Order not found")
        
        # Generate BOL data only if not provided
        if bol_data is None:
            print("📋 Generating BOL data from Purchase Order...")
            bol_data = self.generate_bol_from_po(po_document_name, po_document_id, save_to_db=True)
        else:
            print("📋 Using pre-generated BOL data (skipping AI call)")
        
        # Apply address overrides if provided
        if address_overrides:
            if 'ship_from' in address_overrides:
                bol_data['ship_from'] = address_overrides['ship_from']
                print(f"✓ Applied ship_from address override: {address_overrides['ship_from'].get('name')}")
            if 'ship_to' in address_overrides:
                bol_data['ship_to'] = address_overrides['ship_to']
                print(f"✓ Applied ship_to address override: {address_overrides['ship_to'].get('name')}")
        
        # Apply BOL number override if provided
        if bol_number_override:
            bol_data['bol_number'] = bol_number_override
            print(f"✓ Applied BOL number override: {bol_number_override}")
        
        # Get or upload template
        if not bol_template_file_id:
            template_path = Path(__file__).parent.parent / 'templates' / 'BOL_Template.pdf'
            if not template_path.exists():
                raise FileNotFoundError(f"BOL template not found at {template_path}")
            
            print(f"📤 Uploading BOL template...")
            upload = self.parser.upload_file(template_path)
            bol_template_file_id = upload.file_id if hasattr(upload, 'file_id') else str(upload)
        
        # Load form schema (priority: path > database > None)
        form_schema = None
        if form_schema_path:
            schema_path = Path(form_schema_path)
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    form_schema = json.load(f)
                print(f"✓ Loaded form schema from {schema_path}")
        elif use_saved_schema:
            if self.use_supabase:
                schema_data = self.supabase.get_form_schema("BOL_Template.pdf")
            else:
                schema_data = self.store.get_form_schema("BOL_Template.pdf")
            if schema_data:
                form_schema = schema_data.get("schema")
                print(f"✓ Loaded form schema from database ({schema_data.get('num_fields')} fields)")
        
        # Generate output filename
        if not output_filename:
            po_name = po_doc['document_name'].replace('.pdf', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"BOL_{po_name}_{timestamp}.pdf"
        
        # Set output path
        output_path = Path(__file__).parent.parent / 'export' / output_filename
        
        # Fill the template
        print("✏️  Filling BOL template...")
        fill_result = self.parser.fill_template_document(
            template_file_id=bol_template_file_id,
            fill_data=bol_data,
            form_schema=form_schema,
            save_path=str(output_path),
            template_name="BOL_Template.pdf"  # Pass template name for auto-saving schema
        )

        # If a schema was generated, note it
        if fill_result.get('generated_schema'):
            print(f"🎉 Form schema auto-generated and saved! Future runs will be faster.")

        return {
            "bol_data": bol_data,
            "document_url": fill_result['document_url'],
            "output_path": str(output_path),
            "template_file_id": bol_template_file_id,
            "used_schema": fill_result['used_existing_schema'],
            "generated_schema": fill_result.get('generated_schema') is not None
        }
    
    def generate_and_fill_packing_slip(self, po_document_name: str = None,
                                      po_document_id: int = None,
                                      ps_template_file_id: str = None,
                                      form_schema_path: str = None,
                                      use_saved_schema: bool = True,
                                      output_filename: str = None,
                                      address_overrides: Dict = None,
                                      packing_slip_data: Dict = None) -> Dict:
        """
        Generate Packing Slip data from PO and fill the template
        
        Args:
            po_document_name: Name of the PO document in database
            po_document_id: ID of the PO document in database
            ps_template_file_id: Reducto file ID of Packing Slip template
            form_schema_path: Path to saved form schema JSON (optional)
            use_saved_schema: Whether to use schema saved in database (default: True)
            output_filename: Name for the output file (auto-generated if not provided)
            address_overrides: Dictionary with 'ship_from' and/or 'ship_to' address overrides
            packing_slip_data: Pre-generated Packing Slip data (if provided, skips AI generation)
        
        Returns:
            Dictionary with packing slip data and filled document URL
        """
        self._init_parser()
        
        # Get PO document
        po_doc = self.get_document(po_document_name, po_document_id)
        if not po_doc:
            raise ValueError(f"Purchase Order not found")
        
        # Generate Packing Slip data only if not provided
        if packing_slip_data is None:
            print("📦 Generating Packing Slip data from Purchase Order...")
            ps_data = self.generate_packing_slip_from_po(po_document_name, po_document_id, save_to_db=True)
        else:
            print("📦 Using pre-generated Packing Slip data (skipping AI call)")
            ps_data = packing_slip_data
        
        # Apply address overrides if provided
        if address_overrides:
            if 'ship_from' in address_overrides:
                ps_data['ship_from'] = address_overrides['ship_from']
                print(f"✓ Applied ship_from address override: {address_overrides['ship_from'].get('name')}")
            if 'ship_to' in address_overrides:
                ps_data['ship_to'] = address_overrides['ship_to']
                print(f"✓ Applied ship_to address override: {address_overrides['ship_to'].get('name')}")
        
        # Get or upload template
        if not ps_template_file_id:
            # Try both PDF and Excel templates
            template_path = Path(__file__).parent.parent / 'templates' / 'PackingSlip_Template.pdf'
            if not template_path.exists():
                template_path = Path(__file__).parent.parent / 'templates' / 'PackingSlip_Template.xlsx'
            
            if not template_path.exists():
                raise FileNotFoundError(f"Packing Slip template not found")
            
            print(f"📤 Uploading Packing Slip template...")
            upload = self.parser.upload_file(template_path)
            ps_template_file_id = upload.file_id if hasattr(upload, 'file_id') else str(upload)
        
        # Load form schema (priority: path > database > None)
        form_schema = None
        if form_schema_path:
            schema_path = Path(form_schema_path)
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    form_schema = json.load(f)
                print(f"✓ Loaded form schema from {schema_path}")
        elif use_saved_schema:
            if self.use_supabase:
                schema_data = self.supabase.get_form_schema("PackingSlip_Template.pdf")
            else:
                schema_data = self.store.get_form_schema("PackingSlip_Template.pdf")
            if schema_data:
                form_schema = schema_data.get("schema")
                print(f"✓ Loaded form schema from database ({schema_data.get('num_fields')} fields)")
        
        # Generate output filename
        if not output_filename:
            po_name = po_doc['document_name'].replace('.pdf', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = '.pdf' if 'pdf' in str(template_path).lower() else '.xlsx'
            output_filename = f"PackingSlip_{po_name}_{timestamp}{ext}"
        
        # Set output path
        output_path = Path(__file__).parent.parent / 'export' / output_filename
        
        # Fill the template
        print("✏️  Filling Packing Slip template...")
        fill_result = self.parser.fill_template_document(
            template_file_id=ps_template_file_id,
            fill_data=ps_data,
            form_schema=form_schema,
            save_path=str(output_path),
            template_name="PackingSlip_Template.pdf"  # Pass template name for auto-saving schema
        )

        # If a schema was generated, note it
        if fill_result.get('generated_schema'):
            print(f"🎉 Form schema auto-generated and saved! Future runs will be faster.")

        return {
            "packing_slip_data": ps_data,
            "document_url": fill_result['document_url'],
            "output_path": str(output_path),
            "template_file_id": ps_template_file_id,
            "used_schema": fill_result['used_existing_schema'],
            "generated_schema": fill_result.get('generated_schema') is not None
        }


def process_purchase_order(file_path: str, force_reparse: bool = False) -> Dict:
    """Process a purchase order document and store in database"""
    manager = DocumentManager()
    return manager.process_document(file_path, document_type="PO", force_reparse=force_reparse)


def get_parsed_po(document_name: str) -> Optional[Dict]:
    """Get parsed purchase order data from database"""
    manager = DocumentManager()
    return manager.get_parsed_data(document_name=document_name)


def generate_bol_from_po(po_document_name: str = None, po_document_id: int = None) -> Dict:
    """
    Generate a Bill of Lading from a parsed Purchase Order
    
    Args:
        po_document_name: Name of the PO document in database
        po_document_id: ID of the PO document in database
    
    Returns:
        Dictionary containing the filled BOL data
    
    Example:
        >>> bol = generate_bol_from_po(po_document_name="SOLENIS PO 4535119724.pdf")
        >>> print(bol['bol_number'])
    """
    manager = DocumentManager()
    return manager.generate_bol_from_po(po_document_name, po_document_id, save_to_db=True)


def generate_packing_slip_from_po(po_document_name: str = None, po_document_id: int = None) -> Dict:
    """
    Generate a Packing Slip from a parsed Purchase Order
    
    Args:
        po_document_name: Name of the PO document in database
        po_document_id: ID of the PO document in database
    
    Returns:
        Dictionary containing the filled packing slip data
    
    Example:
        >>> ps = generate_packing_slip_from_po(po_document_name="SOLENIS PO 4535119724.pdf")
        >>> print(ps['customer_id'])
    """
    manager = DocumentManager()
    return manager.generate_packing_slip_from_po(po_document_name, po_document_id, save_to_db=True)


def generate_filled_bol(po_document_name: str = None, po_document_id: int = None,
                       bol_template_file_id: str = None,
                       form_schema_path: str = None) -> Dict:
    """
    Complete pipeline: Parse PO → Generate BOL data → Fill BOL template → Save to export/
    
    Args:
        po_document_name: Name of the PO document in database
        po_document_id: ID of the PO document in database
        bol_template_file_id: Optional Reducto file ID of BOL template
        form_schema_path: Optional path to form schema JSON for faster processing
    
    Returns:
        Dictionary with BOL data, document URL, and output path
    
    Example:
        >>> result = generate_filled_bol(po_document_id=1)
        >>> print(f"Saved to: {result['output_path']}")
    """
    manager = DocumentManager()
    return manager.generate_and_fill_bol(
        po_document_name=po_document_name,
        po_document_id=po_document_id,
        bol_template_file_id=bol_template_file_id,
        form_schema_path=form_schema_path
    )


def generate_filled_packing_slip(po_document_name: str = None, po_document_id: int = None,
                                 ps_template_file_id: str = None,
                                 form_schema_path: str = None) -> Dict:
    """
    Complete pipeline: Parse PO → Generate Packing Slip data → Fill template → Save to export/
    
    Args:
        po_document_name: Name of the PO document in database
        po_document_id: ID of the PO document in database
        ps_template_file_id: Optional Reducto file ID of Packing Slip template
        form_schema_path: Optional path to form schema JSON for faster processing
    
    Returns:
        Dictionary with packing slip data, document URL, and output path
    
    Example:
        >>> result = generate_filled_packing_slip(po_document_id=1)
        >>> print(f"Saved to: {result['output_path']}")
    """
    manager = DocumentManager()
    return manager.generate_and_fill_packing_slip(
        po_document_name=po_document_name,
        po_document_id=po_document_id,
        ps_template_file_id=ps_template_file_id,
        form_schema_path=form_schema_path
    )


def setup_form_schemas():
    """
    One-time setup: Generate and save form schemas for BOL and Packing Slip templates
    This should be run once when setting up the system to enable faster form filling

    Returns:
        Dictionary with paths to saved schemas
    """
    from .supabase_service import get_supabase_service

    manager = DocumentManager()
    manager._init_parser()
    supabase = get_supabase_service()

    schemas = {}

    # BOL Template Schema
    bol_template = Path(__file__).parent.parent / 'templates' / 'BOL_Template.pdf'
    if bol_template.exists():
        print("📋 Generating BOL form schema...")
        upload = manager.parser.upload_file(bol_template)
        file_id = upload.file_id if hasattr(upload, 'file_id') else str(upload)

        sample_instructions = """
        Fill with:
        - BOL Number: 202412001
        - Ship From: Hanson Chemicals, 123 Main St, City, ST 12345
        - Ship To: Customer Corp, 456 Oak Ave, City, ST 67890
        - Product: Silicone Oil, 2 IBC, 1000 kg
        """

        schema = manager.parser.generate_form_schema(file_id, sample_instructions, save_path=None)
        supabase.save_form_schema(
            template_name="BOL_Template.pdf",
            schema=schema,
            template_file_id=file_id,
            description="Bill of Lading form schema for faster document generation"
        )
        print(f"✓ Saved BOL schema to Supabase ({len(schema)} fields)")
        schemas['bol'] = schema

    # Packing Slip Template Schema
    ps_template = Path(__file__).parent.parent / 'templates' / 'PackingSlip_Template.pdf'
    if ps_template.exists():
        print("📦 Generating Packing Slip form schema...")
        upload = manager.parser.upload_file(ps_template)
        file_id = upload.file_id if hasattr(upload, 'file_id') else str(upload)

        # Match the exact format used by _packing_slip_instructions()
        sample_instructions = """
Fill this Packing Slip form with the following information:

HEADER SECTION (top right corner):
DATE field (date format): 2024-12-26
CUSTOMER ID field (text): Solenis LLC
SALESPERSON field (text): John Smith

BILL TO SECTION:
Leave all BILL TO fields blank

SHIP TO SECTION:
SHIP TO: Company Name: Solenis Plant - Burlington
SHIP TO: Street Address: 456 Industrial Drive
SHIP TO: City/State/Zip Code: Burlington WI 53105
SHIP TO: Country: USA

ORDER INFORMATION ROW (below SHIP TO section):
Fill ORDER DATE field with: 2024-12-20
Fill ORDER # field with: SO-2024-001
Fill PURCHASE ORDER # field with: PO-4535119724
Fill CUSTOMER CONTACT field with: Jane Doe

LINE ITEMS TABLE (columns: ITEM #, DESCRIPTION, ORDER QTY, SHIP QTY):
Line item (1st row):
  ITEM # (product code): HC-1001
  DESCRIPTION (product name): Sodium Hydroxide 50% - Industrial Grade (Kg)
  ORDER QTY (numeric quantity only): 2000
  SHIP QTY (numeric quantity only): 2000

Line item (2nd row):
  ITEM # (product code): HC-1002
  DESCRIPTION (product name): Polymer Additive XR-200 (Kg)
  ORDER QTY (numeric quantity only): 500
  SHIP QTY (numeric quantity only): 500

Line item (3rd row):
  ITEM # (product code): HC-1003
  DESCRIPTION (product name): Silicone Oil Grade A (Kg)
  ORDER QTY (numeric quantity only): 1000
  SHIP QTY (numeric quantity only): 1000

TOTAL: 3500
        """

        schema = manager.parser.generate_form_schema(file_id, sample_instructions, save_path=None)
        supabase.save_form_schema(
            template_name="PackingSlip_Template.pdf",
            schema=schema,
            template_file_id=file_id,
            description="Packing Slip form schema for faster document generation"
        )
        print(f"✓ Saved Packing Slip schema to Supabase ({len(schema)} fields)")
        schemas['packing_slip'] = schema

    print("\n✅ Form schemas generated and saved to Supabase!")
    print("These schemas will be used automatically for faster form filling.")

    return schemas


def generate_form_schema_for_template(template_path: str, sample_instructions: str,
                                     description: str = None) -> Dict:
    """
    Generate and save a form schema for any template

    Args:
        template_path: Path to the template PDF file
        sample_instructions: Sample filling instructions to detect fields
        description: Optional description of the schema

    Returns:
        Dictionary with schema data
    """
    from .supabase_service import get_supabase_service

    manager = DocumentManager()
    manager._init_parser()
    supabase = get_supabase_service()

    template_path = Path(template_path)
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    print(f"📋 Generating form schema for {template_path.name}...")

    # Upload template
    upload = manager.parser.upload_file(template_path)
    file_id = upload.file_id if hasattr(upload, 'file_id') else str(upload)

    # Generate schema
    schema = manager.parser.generate_form_schema(file_id, sample_instructions, save_path=None)

    # Save to Supabase
    schema_data = supabase.save_form_schema(
        template_name=template_path.name,
        schema=schema,
        template_file_id=file_id,
        description=description
    )

    print(f"✓ Generated and saved schema ({len(schema)} fields)")

    return schema_data


def list_form_schemas() -> List[Dict]:
    """List all saved form schemas"""
    from .supabase_service import get_supabase_service
    supabase = get_supabase_service()
    return supabase.list_form_schemas()


def get_form_schema(template_name: str) -> Optional[Dict]:
    """Get a specific form schema"""
    from .supabase_service import get_supabase_service
    supabase = get_supabase_service()
    return supabase.get_form_schema(template_name)


def delete_form_schema(template_name: str) -> bool:
    """Delete a form schema"""
    from .supabase_service import get_supabase_service
    supabase = get_supabase_service()
    return supabase.delete_form_schema(template_name)


