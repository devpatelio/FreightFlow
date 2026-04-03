"""
Reducto PDF fill service.

Converts extracted JSON data into natural-language fill instructions,
optionally pre-fills form schema values, and calls Reducto Edit API.
"""

import copy
import re
import textwrap
from typing import Dict, List, Optional


def _wrap_text(text: str, width: int = 60) -> str:
    if not text or len(str(text)) <= width:
        return str(text)
    text = str(text)
    lines = text.split('\n')
    wrapped = []
    for line in lines:
        if len(line) <= width:
            wrapped.append(line)
        else:
            wrapped.append(textwrap.fill(line, width=width, break_long_words=False, break_on_hyphens=False))
    return '\n'.join(wrapped)


# ── Instruction Builders ─────────────────────────────────────────────────

def data_to_instructions(data: Dict) -> str:
    is_packing_slip = 'customer_id' in data or 'purchase_order_number' in data
    is_bol = 'bol_number' in data or 'bol_date' in data

    if is_packing_slip and not is_bol:
        return _packing_slip_instructions(data)
    elif is_bol:
        return _bol_instructions(data)
    else:
        return _generic_instructions(data)


def _bol_instructions(data: Dict) -> str:
    lines: list[str] = []
    lines.append("Fill this Bill of Lading with the following information:")
    lines.append("")

    if data.get('bol_number'):
        lines.append(f"BOL NUMBER (digits only): {data['bol_number']}")
    if data.get('bol_date'):
        lines.append(f"BOL DATE (YYYY-MM-DD): {data['bol_date']}")
    if data.get('carrier_name'):
        lines.append(f"CARRIER NAME: {data['carrier_name']}")

    for section_key, label in [('ship_from', 'SHIP FROM'), ('ship_to', 'SHIP TO')]:
        addr = data.get(section_key)
        if addr:
            lines.append("")
            lines.append(f"{label}:")
            if addr.get('name'):
                lines.append(f"  Company: {addr['name']}")
            if addr.get('address'):
                lines.append(f"  Address: {addr['address']}")
            csz = f"{addr.get('city', '')} {addr.get('state', '')} {addr.get('zip_code', '')}".strip()
            if csz:
                lines.append(f"  City/State/Zip: {csz}")

    products = data.get('products', [])
    if products:
        lines.append("")
        lines.append("PRODUCTS (be strict about types: counts vs weights vs units):")
        for i, p in enumerate(products, 1):
            lines.append(f"  Product {i}:")
            if p.get('name'):
                lines.append(f"    Name (text): {p['name']}")
            if p.get('description'):
                lines.append(f"    Description (text): {_wrap_text(p['description'])}")
            if p.get('item_number'):
                lines.append(f"    Item Number (text/code): {p['item_number']}")
            if p.get('un_code'):
                lines.append(f"    UN Code (text): {p['un_code']}")
            hu = p.get('handling_unit') or {}
            if isinstance(hu, dict):
                if hu.get('quantity') is not None:
                    lines.append(f"    Handling Unit Quantity (integer count only): {hu['quantity']}")
                if hu.get('type'):
                    lines.append(f"    Handling Unit Type (IBC/Drum/Pallet/Box text only): {hu['type']}")
            pkg = p.get('package') or {}
            if isinstance(pkg, dict):
                if pkg.get('quantity') is not None:
                    lines.append(f"    Package/Weight Quantity (numeric only): {pkg['quantity']}")
                if pkg.get('type'):
                    lines.append(f"    Package/Weight Unit (kg/lb text only): {pkg['type']}")
            if p.get('weight') is not None:
                lines.append(f"    Total Weight (numeric only): {p['weight']}")

    orders = data.get('orders', [])
    if orders:
        lines.append("")
        lines.append("ORDERS (be strict: counts are integers; weights are numbers; units are separate):")
        for i, o in enumerate(orders, 1):
            lines.append(f"  Order {i}:")
            for field, label_txt, note in [
                ('customer_id', 'Customer ID', 'text'),
                ('po_number', 'PO Number', 'text'),
                ('sales_order_number', 'Sales Order Number', 'digits/text'),
                ('material_name', 'Material Name', 'text'),
            ]:
                if o.get(field):
                    lines.append(f"    {label_txt} ({note}): {o[field]}")
            if o.get('num_packages') is not None:
                lines.append(f"    Number of Packages (integer count only): {o['num_packages']}")
            if o.get('weight') is not None:
                lines.append(f"    Weight (numeric only): {o['weight']}")
            if o.get('weight_unit'):
                lines.append(f"    Weight Unit (kg/lb text only): {o['weight_unit']}")
            if o.get('country_of_origin'):
                lines.append(f"    Country of Origin (text): {o['country_of_origin']}")
            if o.get('customer_po'):
                lines.append(f"    Customer PO (text): {o['customer_po']}")
            if o.get('additional_shipper_info'):
                lines.append(f"    Additional Shipper Info (text): {_wrap_text(o['additional_shipper_info'])}")

    if data.get('special_instructions'):
        lines.append("")
        lines.append(f"SPECIAL INSTRUCTIONS: {_wrap_text(data['special_instructions'])}")

    return "\n".join(lines)


def _packing_slip_instructions(data: Dict) -> str:
    lines: list[str] = []
    lines.append("Fill this Packing Slip form with the following information:")
    lines.append("")

    lines.append("HEADER SECTION (top right corner):")
    if data.get('date'):
        lines.append(f"DATE field (date format): {data['date']}")
    if data.get('customer_id'):
        lines.append(f"CUSTOMER ID field (text): {data['customer_id']}")
    if data.get('salesperson'):
        lines.append(f"SALESPERSON field (text): {data['salesperson']}")
    lines.append("")

    for section_key, label in [('bill_to', 'BILL TO'), ('ship_from', 'SHIP FROM'), ('ship_to', 'SHIP TO')]:
        addr = data.get(section_key)
        lines.append(f"{label} SECTION:")
        if addr and isinstance(addr, dict) and any(addr.values()):
            if addr.get('name'):
                lines.append(f"{label}: Company Name: {addr['name']}")
            if addr.get('address'):
                lines.append(f"{label}: Street Address: {addr['address']}")
            csz = f"{addr.get('city', '')} {addr.get('state', '')} {addr.get('zip_code', '')}".strip()
            if csz:
                lines.append(f"{label}: City/State/Zip Code: {csz}")
            if addr.get('country'):
                lines.append(f"{label}: Country: {addr['country']}")
        else:
            lines.append(f"Leave all {label} fields blank")
        lines.append("")

    lines.append("ORDER INFORMATION ROW (below SHIP TO section):")
    for field, label in [
        ('order_date', 'ORDER DATE'), ('order_number', 'ORDER #'),
        ('purchase_order_number', 'PURCHASE ORDER #'), ('customer_contact', 'CUSTOMER CONTACT'),
    ]:
        val = data.get(field, '')
        if val:
            lines.append(f"Fill {label} field with: {val}")
        else:
            lines.append(f"{label}: Leave blank")
    lines.append("")

    lines.append("LINE ITEMS TABLE (columns: ITEM #, DESCRIPTION, ORDER QTY, SHIP QTY):")
    items = data.get('items', [])
    row_labels = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th']
    for idx, item in enumerate(items):
        rl = row_labels[idx] if idx < len(row_labels) else f"{idx+1}th"
        lines.append(f"Line item ({rl} row):")
        if item.get('item_number'):
            lines.append(f"  ITEM # (product code): {item['item_number']}")
        if item.get('description'):
            lines.append(f"  DESCRIPTION (product name): {_wrap_text(item['description'])}")
        if item.get('order_qty') is not None:
            lines.append(f"  ORDER QTY (numeric quantity only): {item['order_qty']}")
        if item.get('ship_qty') is not None:
            lines.append(f"  SHIP QTY (numeric quantity only): {item['ship_qty']}")
        lines.append("")

    if data.get('total'):
        lines.append(f"TOTAL: {data['total']}")

    return "\n".join(lines)


def _generic_instructions(data: Dict) -> str:
    lines: list[str] = ["Fill this form with the following information:", ""]

    def process(d: Dict, prefix: str = ""):
        for key, value in d.items():
            name = key.replace('_', ' ').title()
            full = f"{prefix}{name}" if prefix else name
            if isinstance(value, dict):
                process(value, f"{full} - ")
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    for i, item in enumerate(value, 1):
                        process(item, f"{full} {i} - ")
                else:
                    lines.append(f"{full}: {', '.join(str(v) for v in value) if value else ''}")
            elif value is None:
                lines.append(f"{full}: [Leave blank]")
            else:
                lines.append(f"{full}: {value}")

    process(data)
    return "\n".join(lines)


# ── Packing Slip Schema Pre-fill ─────────────────────────────────────────

def prefill_packing_slip_schema(form_schema: List[Dict], fill_data: Dict) -> List[Dict]:
    """Deterministically set schema field values for packing slips to avoid LLM inconsistency."""
    schema = copy.deepcopy(form_schema)

    def s(v):
        return "" if v is None else str(v)

    header = {
        "DATE": s(fill_data.get("date")),
        "CUSTOMER ID": s(fill_data.get("customer_id")),
        "SALESPERSON": s(fill_data.get("salesperson")),
    }
    order_info = {
        "ORDER DATE": s(fill_data.get("order_date")),
        "ORDER #": s(fill_data.get("order_number")),
        "PURCHASE ORDER #": s(fill_data.get("purchase_order_number")),
        "CUSTOMER CONTACT": s(fill_data.get("customer_contact")),
    }

    sf = fill_data.get("ship_from") or {}
    st = fill_data.get("ship_to") or {}
    bt = fill_data.get("bill_to") or {}
    has_bt = isinstance(bt, dict) and any(bt.values())

    def csz(addr):
        return " ".join([s(addr.get("city")).strip(), s(addr.get("state")).strip(), s(addr.get("zip_code")).strip()]).strip()

    items = fill_data.get("items") or []

    def row_num(desc: str) -> Optional[int]:
        m = re.search(r"\((\d+)(st|nd|rd|th)\s+row", desc)
        return int(m.group(1)) if m else None

    def canon(desc: str) -> str:
        head = (desc or "").strip().split(".", 1)[0].strip()
        head = re.sub(r":\s*$", "", head)
        return re.sub(r"\s+", " ", head).upper()

    for field in schema:
        desc = (field.get("description") or "").strip()
        if not desc:
            continue
        key = canon(desc)

        if key in header:
            field["value"] = header[key]
            continue
        if key in order_info:
            field["value"] = order_info[key]
            continue

        for prefix, addr_data, addr_csz in [
            ("SHIP FROM:", sf, csz(sf)),
            ("SHIP TO:", st, csz(st)),
            ("BILL TO:", bt, csz(bt)),
        ]:
            if key.startswith(prefix):
                if prefix == "BILL TO:" and not has_bt:
                    field["value"] = ""
                    break
                sub = key.replace(prefix, "", 1).strip().rstrip(":")
                if sub in ("COMPANY NAME",):
                    field["value"] = s(addr_data.get("name"))
                elif sub in ("STREET ADDRESS",):
                    field["value"] = s(addr_data.get("address"))
                elif sub in ("CITY/STATE/ZIP CODE",):
                    field["value"] = addr_csz
                elif sub in ("COUNTRY",):
                    field["value"] = s(addr_data.get("country"))
                break

        if key.startswith(("ITEM # (LINE ITEM)", "DESCRIPTION (LINE ITEM)",
                           "ORDER QTY (LINE ITEM)", "SHIP QTY (LINE ITEM)")):
            rn = row_num(desc)
            if rn is None:
                continue
            idx = rn - 1
            if idx < 0 or idx >= len(items):
                field["value"] = ""
                continue
            item = items[idx] or {}
            if key.startswith("ITEM # (LINE ITEM)"):
                field["value"] = s(item.get("item_number"))
            elif key.startswith("DESCRIPTION (LINE ITEM)"):
                field["value"] = s(item.get("description"))
            elif key.startswith("ORDER QTY (LINE ITEM)"):
                field["value"] = s(item.get("order_qty"))
            elif key.startswith("SHIP QTY (LINE ITEM)"):
                field["value"] = s(item.get("ship_qty"))

    return schema


# ── Reducto Fill ──────────────────────────────────────────────────────────

def fill_pdf_template(
    reducto_api_key: str,
    template_file_data: bytes,
    fill_data: Dict,
    form_schema: Optional[List[Dict]] = None,
    is_packing_slip: bool = False,
) -> Dict:
    """
    Fill a PDF template using Reducto Edit API.

    Returns dict with 'document_url' and optionally 'generated_schema'.
    """
    from reducto import Reducto

    client = Reducto(api_key=reducto_api_key)

    instructions = data_to_instructions(fill_data)

    import tempfile, os
    from pathlib import Path
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(template_file_data)
        tmp_path = Path(tmp.name)

    try:
        upload = client.upload(file=tmp_path)

        edit_options = {
            "enable_overflow_pages": False,
            "llm_provider_preference": "openai",
            "color": "#000000",
        }

        if form_schema:
            if is_packing_slip:
                form_schema = prefill_packing_slip_schema(form_schema, fill_data)

            result = client.edit.run(
                document_url=upload,
                edit_instructions=instructions,
                edit_options=edit_options,
                form_schema=form_schema,
            )
            generated_schema = None
        else:
            result = client.edit.run(
                document_url=upload,
                edit_instructions=instructions,
                edit_options=edit_options,
            )
            generated_schema = None
            if hasattr(result, 'form_schema') and result.form_schema:
                if hasattr(result.form_schema[0], 'model_dump'):
                    generated_schema = [f.model_dump() for f in result.form_schema]
                else:
                    generated_schema = result.form_schema

        return {
            'document_url': result.document_url,
            'generated_schema': generated_schema,
            'used_existing_schema': form_schema is not None,
        }
    finally:
        os.unlink(tmp_path)
