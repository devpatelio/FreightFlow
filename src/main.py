#!/usr/bin/env python3
"""
Logistics Document Management System
Main entry point for processing Purchase Orders and generating shipping documents
"""

from pathlib import Path
from .backend import DocumentManager, process_purchase_order
import json


def print_separator():
    print("\n" + "="*70 + "\n")


def display_document_info(doc: dict):
    """Pretty print document information"""
    print(f"📋 Document Information:")
    print(f"  ID: {doc['document_id']}")
    print(f"  Name: {doc['document_name']}")
    print(f"  Type: {doc['document_type']}")
    print(f"  File ID: {doc['file_id']}")
    print(f"  Created: {doc['created_at']}")
    print(f"  Updated: {doc['updated_at']}")
    if doc.get('studio_link'):
        print(f"  Studio Link: {doc['studio_link']}")


def main():
    print_separator()
    
    manager = DocumentManager()
      
    try:
        # result = manager.process_document(po_path, document_type="PO")
        
        # print_separator()
        # display_document_info(result)
        
        # print_separator()
        # print("Parsed Data Preview:")
        # parsed_data = result['result_json']
        
        # if isinstance(parsed_data, dict):
        #     sample_keys = list(parsed_data.keys())[:5]
        #     sample = {k: parsed_data[k] for k in sample_keys if k in parsed_data}
        #     print(json.dumps(sample, indent=2)[:500] + "...")
        # else:
        #     print(str(parsed_data)[:500] + "...")
        
        # print_separator()
        # print("✅ Document processed successfully!")
        # print(f"Total documents in database: {len(manager.list_documents())}")
        
        # print_separator()
        # print("📚 All Documents in Database:")
        # for doc in manager.list_documents():
        #     print(f"  [{doc['document_id']}] {doc['document_name']} ({doc['document_type']})")

        print_separator()
        
        PS_fill = manager.generate_packing_slip_from_po(po_document_id=1,
                                                save_to_db=True)
        print(json.dumps(PS_fill, indent=2))

        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
