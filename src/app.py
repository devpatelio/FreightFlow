"""
Flask Application for Logistics Management
Provides web interface for managing products, customers, templates, and PO processing workflow
"""

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
from datetime import datetime

# Import Supabase service
from .supabase_service import get_supabase_service

from .backend import (
    DocumentManager,
    generate_form_schema_for_template,
    list_form_schemas,
    get_form_schema,
    delete_form_schema,
    setup_form_schemas
)
from .modules import Account, SavedProduct, Address, Buyer, UnitType, Country

app = Flask(__name__,
            template_folder='../templates_flask',
            static_folder='../static')

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = Path(__file__).parent.parent / 'uploads'
app.config['EXPORT_FOLDER'] = Path(__file__).parent.parent / 'export'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

# Ensure necessary folders exist (important for Vercel serverless environment)
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
app.config['EXPORT_FOLDER'].mkdir(parents=True, exist_ok=True)

# Initialize Supabase service and document manager
supabase = get_supabase_service()
doc_manager = DocumentManager()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ============================================================================
# DASHBOARD ROUTE
# ============================================================================

@app.route('/')
def index():
    """Dashboard/Home page"""
    stats = supabase.get_statistics()

    # Get recent documents (last 5)
    try:
        all_docs = supabase.list_documents()
        recent_docs = all_docs[:5] if all_docs else []  # Already sorted by created_at DESC
    except:
        recent_docs = []

    return render_template('index.html',
                         stats=stats,
                         recent_docs=recent_docs)


# ============================================================================
# PRODUCT ROUTES
# ============================================================================

@app.route('/products')
def products_list():
    """List all products"""
    products = supabase.list_products()
    return render_template('products/list.html', products=products)


@app.route('/products/create', methods=['GET', 'POST'])
def products_create():
    """Create new product"""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            item_number = request.form.get('item_number') or None
            un_code = request.form.get('un_code') or None
            unit_type = request.form.get('unit_type', 'kg')
            handling_unit_type = request.form.get('handling_unit_type', 'IBC')
            notes = request.form.get('notes') or None

            product = supabase.create_product(
                name=name,
                description=description,
                item_number=item_number,
                un_code=un_code,
                default_unit_type=unit_type,
                default_handling_unit_type=handling_unit_type,
                notes=notes
            )
            flash(f'Product "{product["name"]}" created successfully!', 'success')
            return redirect(url_for('products_list'))
        except Exception as e:
            flash(f'Error creating product: {str(e)}', 'error')

    unit_types = [e.value for e in UnitType]
    return render_template('products/create.html', unit_types=unit_types)


@app.route('/products/<product_id>/edit', methods=['GET', 'POST'])
def products_edit(product_id):
    """Edit existing product"""
    product = supabase.get_product(product_id)
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products_list'))

    if request.method == 'POST':
        try:
            update_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'item_number': request.form.get('item_number') or None,
                'un_code': request.form.get('un_code') or None,
                'default_unit_type': request.form.get('unit_type', 'kg'),
                'default_handling_unit_type': request.form.get('handling_unit_type', 'IBC'),
                'notes': request.form.get('notes') or None
            }

            supabase.update_product(product_id, update_data)
            flash(f'Product "{update_data["name"]}" updated successfully!', 'success')
            return redirect(url_for('products_list'))
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'error')

    unit_types = [e.value for e in UnitType]
    return render_template('products/edit.html', product=product, unit_types=unit_types)


@app.route('/products/<product_id>/delete', methods=['POST'])
def products_delete(product_id):
    """Delete product"""
    if supabase.delete_product(product_id):
        flash('Product deleted successfully!', 'success')
    else:
        flash('Failed to delete product', 'error')
    return redirect(url_for('products_list'))


# ============================================================================
# CUSTOMER ROUTES
# ============================================================================

@app.route('/customers')
def customers_list():
    """List all customers"""
    customers = supabase.list_accounts()
    return render_template('customers/list.html', customers=customers)


@app.route('/customers/<customer_id>/view')
def customers_view(customer_id):
    """View customer details with associated documents"""
    customer = supabase.get_account_with_documents(customer_id)
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('customers_list'))

    return render_template('customers/view.html', customer=customer)


@app.route('/customers/create', methods=['GET', 'POST'])
def customers_create():
    """Create new customer"""
    if request.method == 'POST':
        try:
            company_name = request.form.get('company_name')
            customer_id = request.form.get('customer_id')
            payment_terms = request.form.get('payment_terms', 'NET 90 DAYS')
            delivery_terms = request.form.get('delivery_terms', 'Free Carrier DESTINATION')
            notes = request.form.get('notes') or None

            account = supabase.create_account(
                company_name=company_name,
                customer_id=customer_id,
                default_payment_terms=payment_terms,
                default_delivery_terms=delivery_terms,
                notes=notes
            )
            flash(f'Customer "{account["company_name"]}" created successfully!', 'success')
            return redirect(url_for('customers_list'))
        except Exception as e:
            flash(f'Error creating customer: {str(e)}', 'error')

    return render_template('customers/create.html')


@app.route('/customers/<customer_id>/edit', methods=['GET', 'POST'])
def customers_edit(customer_id):
    """Edit existing customer"""
    customer = supabase.get_account(customer_id)
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('customers_list'))

    if request.method == 'POST':
        try:
            update_data = {
                'company_name': request.form.get('company_name'),
                'customer_id': request.form.get('customer_id'),
                'default_payment_terms': request.form.get('payment_terms', 'NET 90 DAYS'),
                'default_delivery_terms': request.form.get('delivery_terms', 'Free Carrier DESTINATION'),
                'notes': request.form.get('notes') or None
            }

            supabase.update_account(customer_id, update_data)
            flash(f'Customer "{update_data["company_name"]}" updated successfully!', 'success')
            return redirect(url_for('customers_list'))
        except Exception as e:
            flash(f'Error updating customer: {str(e)}', 'error')

    return render_template('customers/edit.html', customer=customer)


@app.route('/customers/<customer_id>/delete', methods=['POST'])
def customers_delete(customer_id):
    """Delete customer"""
    if supabase.delete_account(customer_id):
        flash('Customer deleted successfully!', 'success')
    else:
        flash('Failed to delete customer', 'error')
    return redirect(url_for('customers_list'))


# ============================================================================
# TEMPLATE EDITOR ROUTES
# ============================================================================

@app.route('/templates')
def templates_list():
    """List editable templates"""
    template_dir = Path(__file__).parent.parent / 'templates'
    templates = []

    for template_name in ['BOL_Template.txt', 'PackingSlip_Template.txt', 'HansonChemicals.txt']:
        template_path = template_dir / template_name
        if template_path.exists():
            templates.append({
                'name': template_name,
                'path': str(template_path),
                'size': template_path.stat().st_size,
                'modified': datetime.fromtimestamp(template_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })

    return render_template('templates/edit.html', templates=templates)


@app.route('/templates/<template_name>', methods=['GET', 'POST'])
def templates_edit(template_name):
    """Edit template content"""
    # Security: only allow specific template files
    allowed_templates = ['BOL_Template.txt', 'PackingSlip_Template.txt', 'HansonChemicals.txt']
    if template_name not in allowed_templates:
        flash('Invalid template name', 'error')
        return redirect(url_for('templates_list'))

    template_dir = Path(__file__).parent.parent / 'templates'
    template_path = template_dir / template_name

    if not template_path.exists():
        flash('Template not found', 'error')
        return redirect(url_for('templates_list'))

    if request.method == 'POST':
        try:
            content = request.form.get('content')
            with open(template_path, 'w') as f:
                f.write(content)
            flash(f'Template "{template_name}" saved successfully!', 'success')
            return redirect(url_for('templates_list'))
        except Exception as e:
            flash(f'Error saving template: {str(e)}', 'error')

    with open(template_path, 'r') as f:
        content = f.read()

    return render_template('templates/edit.html',
                         template_name=template_name,
                         content=content,
                         editing=True)


# ============================================================================
# PO UPLOAD WORKFLOW ROUTES
# ============================================================================

@app.route('/po/upload', methods=['GET', 'POST'])
def po_upload():
    """Upload PO and select customer"""
    customers = supabase.list_accounts()

    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id')

            if 'po_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(request.url)

            file = request.files['po_file']

            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"

                # Save temporarily for processing
                filepath = app.config['UPLOAD_FOLDER'] / unique_filename
                file.save(filepath)

                # Process with backend
                doc = doc_manager.process_document(str(filepath), document_type="PO")

                # Upload to Supabase storage
                with open(filepath, 'rb') as f:
                    file_data = f.read()

                storage_path = f"{datetime.now().strftime('%Y/%m')}/{unique_filename}"
                file_url = supabase.upload_file(
                    bucket=supabase.BUCKET_UPLOADS,
                    file_path=storage_path,
                    file_data=file_data,
                    content_type='application/pdf'
                )

                # Get account by ID (UUID from form)
                print(f"\n=== PO Upload Debug ===")
                print(f"Form value (account UUID): {customer_id}")

                # The form sends the account UUID (id field), not the customer_id field
                account = supabase.get_account_by_id(customer_id)
                if not account:
                    flash(f'Error: Customer not found. Please select a valid customer.', 'error')
                    print(f"❌ Account not found for UUID: {customer_id}")
                    return redirect(request.url)

                account_id = account['id']  # This is already the UUID
                print(f"✓ Found account: {account['company_name']}")
                print(f"✓ Account customer_id: {account['customer_id']}")
                print(f"✓ Account UUID: {account_id}")
                print(f"=====================\n")

                # Create document record in Supabase
                created_doc = supabase.create_document(
                    document_id=doc['document_id'],
                    document_type='PO',
                    document_name=unique_filename,
                    account_id=account_id,
                    file_path=storage_path,
                    file_url=file_url,
                    parsed_data=doc.get('result_json'),
                    status='processed'
                )
                print(f"Created PO document: {created_doc}")

                # Store account UUID in session for review page
                session['current_account_id'] = account_id

                flash('PO uploaded and parsed successfully!', 'success')
                return redirect(url_for('po_review', doc_id=doc['document_id']))
            else:
                flash('Invalid file type. Only PDF and image files allowed.', 'error')
        except Exception as e:
            flash(f'Error processing PO: {str(e)}', 'error')

    return render_template('po/upload.html', customers=customers)


@app.route('/po/<int:doc_id>/review')
def po_review(doc_id):
    """Review parsed PO data and allow editing"""
    doc = doc_manager.get_document(document_id=doc_id)

    if not doc:
        flash('Document not found', 'error')
        return redirect(url_for('po_upload'))

    account_id = session.get('current_account_id')
    customer = supabase.get_account_by_id(account_id) if account_id else None

    # Generate BOL and Packing Slip data using AI
    try:
        bol_data = doc_manager.generate_bol_from_po(po_document_id=doc_id, save_to_db=False)
        ps_data = doc_manager.generate_packing_slip_from_po(po_document_id=doc_id, save_to_db=False)
    except Exception as e:
        flash(f'Error generating documents: {str(e)}', 'warning')
        bol_data = {}
        ps_data = {}

    return render_template('po/review.html',
                         doc=doc,
                         customer=customer,
                         bol_data=json.dumps(bol_data, indent=2, default=str),
                         ps_data=json.dumps(ps_data, indent=2, default=str))


@app.route('/po/<int:doc_id>/generate', methods=['POST'])
def po_generate(doc_id):
    """Generate BOL and Packing Slip from reviewed data"""
    try:
        # Check if user wants to use form schemas
        use_schema = request.form.get('use_schema', 'true').lower() == 'true'

        # Generate filled documents
        bol_result = doc_manager.generate_and_fill_bol(
            po_document_id=doc_id,
            use_saved_schema=use_schema
        )
        ps_result = doc_manager.generate_and_fill_packing_slip(
            po_document_id=doc_id,
            use_saved_schema=use_schema
        )

        # Extract filenames and paths
        bol_filename = Path(bol_result['output_path']).name
        ps_filename = Path(ps_result['output_path']).name
        bol_filepath = Path(bol_result['output_path'])
        ps_filepath = Path(ps_result['output_path'])

        # Get the original PO document to find the associated account
        po_doc = supabase.get_document(doc_id)
        account_id = po_doc.get('account_id') if po_doc else None

        print(f"\n=== Document Generation Debug ===")
        print(f"PO Document ID: {doc_id}")
        print(f"PO Document: {po_doc.get('document_name') if po_doc else 'NOT FOUND'}")
        print(f"Account ID from PO: {account_id}")
        print(f"================================\n")

        # Generate new document IDs for both BOL and Packing Slip
        all_docs = supabase.list_documents()
        max_doc_id = max([d.get('document_id', 0) for d in all_docs], default=0)
        bol_doc_id = max_doc_id + 1
        ps_doc_id = max_doc_id + 2

        # Upload BOL to Supabase storage and create document record
        if bol_filepath.exists():
            with open(bol_filepath, 'rb') as f:
                bol_file_data = f.read()

            bol_storage_path = f"{datetime.now().strftime('%Y/%m')}/{bol_filename}"
            bol_file_url = supabase.upload_file(
                bucket=supabase.BUCKET_GENERATED,
                file_path=bol_storage_path,
                file_data=bol_file_data,
                content_type='application/pdf'
            )

            # Create BOL document record
            print(f"Creating BOL document with account_id: {account_id}")
            bol_doc = supabase.create_document(
                document_id=bol_doc_id,
                document_type='BOL',
                document_name=bol_filename,
                account_id=account_id,
                file_path=bol_storage_path,
                file_url=bol_file_url,
                parsed_data=bol_result.get('bol_data'),
                status='generated'
            )
            print(f"Created BOL document: {bol_doc}")

            # Link BOL to original PO
            if bol_doc:
                supabase.link_documents(
                    po_document_id=doc_id,
                    generated_document_id=bol_doc_id,
                    relationship_type='BOL'
                )

        # Upload Packing Slip to Supabase storage and create document record
        if ps_filepath.exists():
            with open(ps_filepath, 'rb') as f:
                ps_file_data = f.read()

            # Determine content type based on file extension
            content_type = 'application/pdf' if ps_filename.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            ps_storage_path = f"{datetime.now().strftime('%Y/%m')}/{ps_filename}"
            ps_file_url = supabase.upload_file(
                bucket=supabase.BUCKET_GENERATED,
                file_path=ps_storage_path,
                file_data=ps_file_data,
                content_type=content_type
            )

            # Create Packing Slip document record
            print(f"Creating Packing Slip document with account_id: {account_id}")
            ps_doc = supabase.create_document(
                document_id=ps_doc_id,
                document_type='PACKING_SLIP',
                document_name=ps_filename,
                account_id=account_id,
                file_path=ps_storage_path,
                file_url=ps_file_url,
                parsed_data=ps_result.get('packing_slip_data'),
                status='generated'
            )
            print(f"Created Packing Slip document: {ps_doc}")

            # Link Packing Slip to original PO
            if ps_doc:
                supabase.link_documents(
                    po_document_id=doc_id,
                    generated_document_id=ps_doc_id,
                    relationship_type='PACKING_SLIP'
                )

        # Show info about schema usage and generation
        messages = []
        if bol_result.get('generated_schema') or ps_result.get('generated_schema'):
            messages.append('Form schemas auto-generated and saved for future use!')
        if bol_result.get('used_schema') or ps_result.get('used_schema'):
            messages.append('Used existing form schemas (faster processing)')

        if messages:
            flash('Documents generated and uploaded to Supabase successfully! ' + ' '.join(messages), 'success')
        else:
            flash('Documents generated and uploaded to Supabase successfully!', 'success')

        return redirect(url_for('documents_view',
                              bol_file=bol_filename,
                              ps_file=ps_filename))
    except Exception as e:
        flash(f'Error generating documents: {str(e)}', 'error')
        return redirect(url_for('po_review', doc_id=doc_id))


# ============================================================================
# DOCUMENT VIEWER ROUTES
# ============================================================================

@app.route('/documents/view')
def documents_view():
    """View generated documents"""
    bol_file = request.args.get('bol_file')
    ps_file = request.args.get('ps_file')

    return render_template('documents/view.html',
                         bol_file=bol_file,
                         ps_file=ps_file)


@app.route('/documents/download/<filename>')
def documents_download(filename):
    """Download generated document from local export folder"""
    export_dir = Path(__file__).parent.parent / 'export'
    filepath = export_dir / filename

    if not filepath.exists():
        flash('File not found', 'error')
        return redirect(url_for('index'))

    return send_file(filepath, as_attachment=True)


@app.route('/documents/file/<int:doc_id>')
def documents_file(doc_id):
    """View/download document from Supabase storage"""
    try:
        # Check if download is requested
        force_download = request.args.get('download') == '1'

        # Get document from database
        doc = supabase.get_document(doc_id)
        if not doc:
            flash('Document not found', 'error')
            return redirect(url_for('index'))

        file_path = doc.get('file_path')
        document_name = doc.get('document_name', 'document.pdf')
        document_type = doc.get('document_type')

        if not file_path:
            flash('File path not found for this document', 'error')
            return redirect(url_for('index'))

        # Determine which bucket to use based on document type
        if document_type == 'PO':
            bucket = supabase.BUCKET_UPLOADS
        else:
            bucket = supabase.BUCKET_GENERATED

        # Download file from Supabase storage
        file_data = supabase.download_file(bucket, file_path)

        # Determine content type based on file extension
        if document_name.endswith('.pdf'):
            content_type = 'application/pdf'
        elif document_name.endswith('.xlsx'):
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif document_name.endswith('.png'):
            content_type = 'image/png'
        elif document_name.endswith('.jpg') or document_name.endswith('.jpeg'):
            content_type = 'image/jpeg'
        else:
            content_type = 'application/octet-stream'

        # Return file as response
        from io import BytesIO
        return send_file(
            BytesIO(file_data),
            mimetype=content_type,
            as_attachment=force_download,
            download_name=document_name
        )

    except Exception as e:
        print(f"Error fetching file: {str(e)}")
        flash(f'Error retrieving file: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/documents/preview/<filename>')
def documents_preview(filename):
    """Preview generated document in browser"""
    export_dir = Path(__file__).parent.parent / 'export'
    filepath = export_dir / filename

    if not filepath.exists():
        flash('File not found', 'error')
        return redirect(url_for('index'))

    return send_file(filepath, mimetype='application/pdf')


# ============================================================================
# FORM SCHEMA ROUTES
# ============================================================================

@app.route('/schemas')
def schemas_list():
    """List all form schemas"""
    schemas = list_form_schemas()
    return render_template('schemas/list.html', schemas=schemas)


@app.route('/schemas/generate', methods=['GET', 'POST'])
def schemas_generate():
    """Generate a new form schema"""
    if request.method == 'POST':
        try:
            template_name = request.form.get('template_name')
            sample_instructions = request.form.get('sample_instructions')
            description = request.form.get('description') or None
            
            # Get template path
            template_dir = Path(__file__).parent.parent / 'templates'
            template_path = template_dir / template_name
            
            if not template_path.exists():
                flash(f'Template not found: {template_name}', 'error')
                return redirect(request.url)
            
            # Generate schema
            schema_data = generate_form_schema_for_template(
                template_path=str(template_path),
                sample_instructions=sample_instructions,
                description=description
            )
            
            flash(f'Form schema generated successfully! ({schema_data["num_fields"]} fields detected)', 'success')
            return redirect(url_for('schemas_list'))
            
        except Exception as e:
            flash(f'Error generating schema: {str(e)}', 'error')
    
    # Get available PDF templates
    template_dir = Path(__file__).parent.parent / 'templates'
    pdf_templates = []
    if template_dir.exists():
        pdf_templates = [f.name for f in template_dir.glob('*.pdf')]
    
    return render_template('schemas/generate.html', templates=pdf_templates)


@app.route('/schemas/<template_name>')
def schemas_view(template_name):
    """View form schema details"""
    schema_data = get_form_schema(template_name)
    
    if not schema_data:
        flash('Schema not found', 'error')
        return redirect(url_for('schemas_list'))
    
    return render_template('schemas/view.html', 
                         schema_data=schema_data,
                         schema_json=json.dumps(schema_data['schema'], indent=2))


@app.route('/schemas/<template_name>/delete', methods=['POST'])
def schemas_delete(template_name):
    """Delete a form schema"""
    if delete_form_schema(template_name):
        flash('Schema deleted successfully!', 'success')
    else:
        flash('Failed to delete schema', 'error')
    return redirect(url_for('schemas_list'))


@app.route('/schemas/setup', methods=['POST'])
def schemas_setup():
    """Run the initial setup to generate schemas for all templates"""
    try:
        schemas = setup_form_schemas()
        flash(f'Successfully generated {len(schemas)} form schemas!', 'success')
    except Exception as e:
        flash(f'Error during setup: {str(e)}', 'error')
    return redirect(url_for('schemas_list'))


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8000)
