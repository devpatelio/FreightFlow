#!/usr/bin/env python3
"""
Complete Logistics Document Pipeline Example

This script demonstrates the full workflow:
1. Parse Purchase Order
2. Generate BOL/Packing Slip data
3. Fill template documents
4. Save to export/ folder
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from backend import (
    DocumentManager,
    generate_filled_bol,
    generate_filled_packing_slip,
    setup_form_schemas
)


def main():
    print("="*70)
    print("LOGISTICS DOCUMENT GENERATION PIPELINE")
    print("="*70)
    print()
    
    manager = DocumentManager()
    
    # ========================================================================
    # STEP 1: List available Purchase Orders
    # ========================================================================
    print("📚 Available Purchase Orders:")
    print("-" * 70)
    
    po_docs = [doc for doc in manager.list_documents() if doc['document_type'] == 'PO']
    if not po_docs:
        print("No Purchase Orders found in database.")
        print("Please run process_document() first to parse a PO.")
        return
    
    for doc in po_docs:
        print(f"  [{doc['document_id']}] {doc['document_name']}")
        print(f"      Created: {doc['created_at']}")
    
    print()
    
    # ========================================================================
    # STEP 2: Generate Bill of Lading (Data Only)
    # ========================================================================
    print("="*70)
    print("GENERATING BILL OF LADING DATA")
    print("="*70)
    print()
    
    po_id = po_docs[0]['document_id']
    print(f"Using PO ID: {po_id}")
    print()
    
    try:
        bol_data = manager.generate_bol_from_po(po_document_id=po_id, save_to_db=True)
        print("✓ BOL Data Generated:")
        print(f"  BOL Number: {bol_data.get('bol_number', 'N/A')}")
        print(f"  Ship From: {bol_data.get('ship_from', {}).get('name', 'N/A')}")
        print(f"  Ship To: {bol_data.get('ship_to', {}).get('name', 'N/A')}")
        print(f"  Products: {len(bol_data.get('products', []))}")
        print(f"  Orders: {len(bol_data.get('orders', []))}")
    except Exception as e:
        print(f"❌ Error generating BOL data: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # ========================================================================
    # STEP 3: Generate Packing Slip (Data Only)
    # ========================================================================
    print("="*70)
    print("GENERATING PACKING SLIP DATA")
    print("="*70)
    print()
    
    try:
        ps_data = manager.generate_packing_slip_from_po(po_document_id=po_id, save_to_db=True)
        print("✓ Packing Slip Data Generated:")
        print(f"  Customer ID: {ps_data.get('customer_id', 'N/A')}")
        print(f"  PO Number: {ps_data.get('purchase_order', 'N/A')}")
        print(f"  Salesperson: {ps_data.get('salesperson', 'N/A')}")
        print(f"  Items: {len(ps_data.get('items', []))}")
        print(f"  Total Quantity: {ps_data.get('total_quantity', 0)}")
    except Exception as e:
        print(f"❌ Error generating Packing Slip data: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # ========================================================================
    # STEP 4: Fill Templates and Generate PDF/Excel Documents
    # ========================================================================
    print("="*70)
    print("FILLING TEMPLATE DOCUMENTS")
    print("="*70)
    print()
    
    # Check if templates exist
    bol_template = Path('../templates/BOL_Template.pdf')
    ps_template_pdf = Path('../templates/PackingSlip_Template.pdf')
    
    # if not bol_template.exists():
    #     print("⚠️  BOL Template not found at templates/BOL_Template.pdf")
    #     print("    Skipping BOL document generation...")
    # else:
    #     print("📄 Generating filled Bill of Lading...")
    #     print()
        
    #     try:
    #         # Check if form schema exists for faster processing
    #         schema_path = 'templates/BOL_FormSchema.json'
    #         if not Path(schema_path).exists():
    #             schema_path = None
            
    #         result = generate_filled_bol(
    #             po_document_id=po_id,
    #             form_schema_path=schema_path
    #         )
            
    #         print("✅ Bill of Lading Generated Successfully!")
    #         print(f"   Saved to: {result['output_path']}")
    #         print(f"   Download URL: {result['document_url'][:50]}...")
            
    #     except Exception as e:
    #         print(f"❌ Error filling BOL template: {e}")
    #         import traceback
    #         traceback.print_exc()
    
    print()
    
    if not ps_template_pdf.exists():
        print("⚠️  Packing Slip Template not found")
        print("    Skipping Packing Slip document generation...")
    else:
        print("📦 Generating filled Packing Slip...")
        print()
        
        try:
            # Check if form schema exists
            schema_path = 'templates/PackingSlip_FormSchema.json'
            if not Path(schema_path).exists():
                schema_path = None
            
            result = generate_filled_packing_slip(
                po_document_id=po_id,
                form_schema_path=schema_path
            )
            
            print("✅ Packing Slip Generated Successfully!")
            print(f"   Saved to: {result['output_path']}")
            print(f"   Download URL: {result['document_url'][:50]}...")
            
        except Exception as e:
            print(f"❌ Error filling Packing Slip template: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("="*70)
    print("PIPELINE COMPLETE")
    print("="*70)
    print()
    print("📁 Check the export/ folder for generated documents")
    print()


def setup_schemas():
    """
    One-time setup to generate form schemas for faster processing
    Run this once when you first set up the templates
    """
    print("="*70)
    print("FORM SCHEMA SETUP")
    print("="*70)
    print()
    print("This will generate form schemas for your templates.")
    print("Form schemas enable 3x faster document generation.")
    print()
    
    try:
        schemas = setup_form_schemas()
        print()
        print("✅ Setup Complete!")
        print("Generated schemas:")
        for doc_type, path in schemas.items():
            print(f"  {doc_type}: {path}")
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        # Run one-time schema setup
        setup_schemas()
    else:
        # Run main pipeline
        main()

