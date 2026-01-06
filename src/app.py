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

# Use /tmp for serverless environments (Vercel), local paths for development
if os.getenv('VERCEL'):
    # Vercel serverless environment - use /tmp (ephemeral)
    app.config['UPLOAD_FOLDER'] = Path('/tmp/uploads')
    app.config['EXPORT_FOLDER'] = Path('/tmp/export')
else:
    # Local development - use project directories
    app.config['UPLOAD_FOLDER'] = Path(__file__).parent.parent / 'uploads'
    app.config['EXPORT_FOLDER'] = Path(__file__).parent.parent / 'export'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

# Ensure necessary folders exist (safe for both local and serverless)
try:
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
    app.config['EXPORT_FOLDER'].mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as e:
    # In read-only environments, folders may not be creatable
    # This is okay - they'll be created when needed in /tmp
    print(f"Note: Could not create folders at startup: {e}")

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


def ensure_dir(directory):
    """Ensure directory exists, creating it if necessary"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        pass  # Directory might already exist or be in read-only filesystem


# ============================================================================
# FAVICON ROUTE (suppress 404 errors)
# ============================================================================

@app.route('/favicon.ico')
def favicon():
    """Return 204 No Content for favicon requests to suppress 404 errors"""
    return '', 204


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
# ADDRESS ROUTES
# ============================================================================

@app.route('/addresses')
def addresses_list():
    """List all addresses"""
    seller_addresses = supabase.list_seller_addresses()
    customers = supabase.list_accounts()
    
    # Get addresses for each customer
    customer_addresses = []
    for customer in customers:
        addrs = supabase.list_customer_addresses(customer['id'])
        for addr in addrs:
            addr['customer'] = customer
            customer_addresses.append(addr)
    
    return render_template('addresses/list.html', 
                         seller_addresses=seller_addresses,
                         customer_addresses=customer_addresses)


@app.route('/addresses/create', methods=['GET', 'POST'])
def addresses_create():
    """Create new address"""
    if request.method == 'POST':
        try:
            address = supabase.create_address(
                name=request.form.get('name'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                zip_code=request.form.get('zip_code'),
                country=request.form.get('country', 'USA'),
                phone=request.form.get('phone') or None,
                email=request.form.get('email') or None,
                address_type=request.form.get('address_type', 'shipping'),
                account_id=request.form.get('account_id') or None,
                seller_company_id=request.form.get('seller_company_id') or None,
                is_default=request.form.get('is_default') == 'on',
                label=request.form.get('label') or None
            )
            flash(f'Address "{address["name"]}" created successfully!', 'success')
            return redirect(url_for('addresses_list'))
        except Exception as e:
            flash(f'Error creating address: {str(e)}', 'error')

    customers = supabase.list_accounts()
    seller_companies = supabase.list_seller_companies()
    return render_template('addresses/create.html', 
                         customers=customers,
                         seller_companies=seller_companies)


@app.route('/addresses/<address_id>/edit', methods=['GET', 'POST'])
def addresses_edit(address_id):
    """Edit existing address"""
    address = supabase.get_address(address_id)
    if not address:
        flash('Address not found', 'error')
        return redirect(url_for('addresses_list'))

    if request.method == 'POST':
        try:
            update_data = {
                'name': request.form.get('name'),
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'state': request.form.get('state'),
                'zip_code': request.form.get('zip_code'),
                'country': request.form.get('country', 'USA'),
                'phone': request.form.get('phone') or None,
                'email': request.form.get('email') or None,
                'address_type': request.form.get('address_type', 'shipping'),
                'account_id': request.form.get('account_id') or None,
                'seller_company_id': request.form.get('seller_company_id') or None,
                'is_default': request.form.get('is_default') == 'on',
                'label': request.form.get('label') or None
            }

            supabase.update_address(address_id, update_data)
            flash(f'Address "{update_data["name"]}" updated successfully!', 'success')
            return redirect(url_for('addresses_list'))
        except Exception as e:
            flash(f'Error updating address: {str(e)}', 'error')

    customers = supabase.list_accounts()
    seller_companies = supabase.list_seller_companies()
    return render_template('addresses/edit.html', 
                         address=address,
                         customers=customers,
                         seller_companies=seller_companies)


@app.route('/addresses/<address_id>/delete', methods=['POST'])
def addresses_delete(address_id):
    """Delete address"""
    if supabase.delete_address(address_id):
        flash('Address deleted successfully!', 'success')
    else:
        flash('Failed to delete address', 'error')
    return redirect(url_for('addresses_list'))


# ============================================================================
# SELLER COMPANY ROUTES
# ============================================================================

@app.route('/sellers')
def sellers_list():
    """List all seller companies"""
    sellers = supabase.list_seller_companies()
    return render_template('sellers/list.html', sellers=sellers)


@app.route('/sellers/create', methods=['GET', 'POST'])
def sellers_create():
    """Create new seller company"""
    if request.method == 'POST':
        try:
            seller = supabase.create_seller_company(
                company_name=request.form.get('company_name'),
                default_salesperson=request.form.get('default_salesperson') or None,
                phone=request.form.get('phone') or None,
                email=request.form.get('email') or None,
                notes=request.form.get('notes') or None,
                is_default=request.form.get('is_default') == 'on'
            )
            flash(f'Seller company "{seller["company_name"]}" created successfully!', 'success')
            return redirect(url_for('sellers_list'))
        except Exception as e:
            flash(f'Error creating seller company: {str(e)}', 'error')

    return render_template('sellers/create.html')


@app.route('/sellers/<seller_id>/view')
def sellers_view(seller_id):
    """View seller company details with addresses"""
    seller = supabase.get_seller_company(seller_id)
    if not seller:
        flash('Seller company not found', 'error')
        return redirect(url_for('sellers_list'))

    return render_template('sellers/view.html', seller=seller)


@app.route('/sellers/<seller_id>/edit', methods=['GET', 'POST'])
def sellers_edit(seller_id):
    """Edit existing seller company"""
    seller = supabase.get_seller_company(seller_id)
    if not seller:
        flash('Seller company not found', 'error')
        return redirect(url_for('sellers_list'))

    if request.method == 'POST':
        try:
            update_data = {
                'company_name': request.form.get('company_name'),
                'default_salesperson': request.form.get('default_salesperson') or None,
                'phone': request.form.get('phone') or None,
                'email': request.form.get('email') or None,
                'notes': request.form.get('notes') or None,
                'is_default': request.form.get('is_default') == 'on'
            }

            supabase.update_seller_company(seller_id, update_data)
            flash(f'Seller company "{update_data["company_name"]}" updated successfully!', 'success')
            return redirect(url_for('sellers_list'))
        except Exception as e:
            flash(f'Error updating seller company: {str(e)}', 'error')

    return render_template('sellers/edit.html', seller=seller)


@app.route('/sellers/<seller_id>/delete', methods=['POST'])
def sellers_delete(seller_id):
    """Delete seller company"""
    if supabase.delete_seller_company(seller_id):
        flash('Seller company deleted successfully!', 'success')
    else:
        flash('Failed to delete seller company', 'error')
    return redirect(url_for('sellers_list'))


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
                ensure_dir(app.config['UPLOAD_FOLDER'])  # Ensure directory exists
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

    # Get seller companies and their addresses for selection
    seller_companies = supabase.list_seller_companies()
    default_seller = supabase.get_default_seller_company()
    
    # Get customer addresses if customer exists
    customer_addresses = []
    if customer:
        customer_addresses = supabase.list_customer_addresses(customer['id'])

    # Generate next BOL number based on customer's PO count
    next_bol_number = ""
    if account_id:
        next_bol_number = supabase.get_next_bol_number(account_id)

    # Try to get cached generated data first
    cached_data = supabase.get_generated_data(doc_id)
    bol_data = cached_data.get('bol_data')
    ps_data = cached_data.get('packing_slip_data')
    
    # Generate BOL and Packing Slip data using AI only if not cached
    if not bol_data or not ps_data:
        try:
            if not bol_data:
                print("🔄 Generating BOL data (not cached)")
                bol_data = doc_manager.generate_bol_from_po(po_document_id=doc_id, save_to_db=False)
            else:
                print("✓ Using cached BOL data")
                
            if not ps_data:
                print("🔄 Generating Packing Slip data (not cached)")
                ps_data = doc_manager.generate_packing_slip_from_po(po_document_id=doc_id, save_to_db=False)
            else:
                print("✓ Using cached Packing Slip data")
            
            # Override BOL number with our calculated one
            if next_bol_number:
                bol_data['bol_number'] = next_bol_number
                
            # If we have a default seller, use their ship_from address
            if default_seller and default_seller.get('addresses'):
                # Find default address or use first one
                seller_address = None
                for addr in default_seller.get('addresses', []):
                    if addr.get('is_default'):
                        seller_address = addr
                        break
                if not seller_address and default_seller.get('addresses'):
                    seller_address = default_seller['addresses'][0]
                
                if seller_address:
                    bol_data['ship_from'] = {
                        'name': seller_address.get('name') or default_seller.get('company_name'),
                        'address': seller_address.get('address'),
                        'city': seller_address.get('city'),
                        'state': seller_address.get('state'),
                        'zip_code': seller_address.get('zip_code'),
                        'country': seller_address.get('country', 'USA'),
                        'phone': seller_address.get('phone') or default_seller.get('phone'),
                        'email': seller_address.get('email') or default_seller.get('email')
                    }
                    ps_data['salesperson'] = default_seller.get('default_salesperson', '')
            
            # Store generated data in Supabase for future use
            supabase.store_generated_data(doc_id, bol_data=bol_data, packing_slip_data=ps_data)
            print(f"✓ Stored generated data in PO document (doc_id: {doc_id})")
            
        except Exception as e:
            flash(f'Error generating documents: {str(e)}', 'warning')
            bol_data = {}
            ps_data = {}
    else:
        print(f"✓ Using fully cached data from PO document (doc_id: {doc_id})")

    return render_template('po/review.html',
                         doc=doc,
                         customer=customer,
                         customer_addresses=customer_addresses,
                         seller_companies=seller_companies,
                         default_seller=default_seller,
                         next_bol_number=next_bol_number,
                         bol_data=json.dumps(bol_data, indent=2, default=str),
                         ps_data=json.dumps(ps_data, indent=2, default=str))


@app.route('/po/<int:doc_id>/generate', methods=['POST'])
def po_generate(doc_id):
    """Generate BOL and Packing Slip from reviewed data"""
    try:
        # Check if user wants to use form schemas
        use_schema = request.form.get('use_schema', 'true').lower() == 'true'
        
        # Get selected ship_from address
        ship_from_address_id = request.form.get('ship_from_address_id')
        ship_to_address_id = request.form.get('ship_to_address_id')
        
        # Build address overrides
        address_overrides = {}
        
        if ship_from_address_id:
            ship_from_addr = supabase.get_address(ship_from_address_id)
            if ship_from_addr:
                address_overrides['ship_from'] = {
                    'name': ship_from_addr.get('name'),
                    'address': ship_from_addr.get('address'),
                    'city': ship_from_addr.get('city'),
                    'state': ship_from_addr.get('state'),
                    'zip_code': ship_from_addr.get('zip_code'),
                    'country': ship_from_addr.get('country', 'USA'),
                    'phone': ship_from_addr.get('phone'),
                    'email': ship_from_addr.get('email')
                }
        
        if ship_to_address_id:
            ship_to_addr = supabase.get_address(ship_to_address_id)
            if ship_to_addr:
                address_overrides['ship_to'] = {
                    'name': ship_to_addr.get('name'),
                    'address': ship_to_addr.get('address'),
                    'city': ship_to_addr.get('city'),
                    'state': ship_to_addr.get('state'),
                    'zip_code': ship_to_addr.get('zip_code'),
                    'country': ship_to_addr.get('country', 'USA'),
                    'phone': ship_to_addr.get('phone'),
                    'email': ship_to_addr.get('email')
                }
        
        # Get account_id for BOL number generation
        account_id = session.get('current_account_id')
        bol_number_override = None
        if account_id:
            bol_number_override = supabase.get_next_bol_number(account_id)

        # Get cached generated data to avoid duplicate AI calls
        cached_data = supabase.get_generated_data(doc_id)
        cached_bol_data = cached_data.get('bol_data')
        cached_ps_data = cached_data.get('packing_slip_data')
        
        if cached_bol_data:
            print(f"✓ Using cached BOL data from review step (saving AI call)")
        if cached_ps_data:
            print(f"✓ Using cached Packing Slip data from review step (saving AI call)")

        # Generate filled documents with address overrides and cached data
        bol_result = doc_manager.generate_and_fill_bol(
            po_document_id=doc_id,
            use_saved_schema=use_schema,
            address_overrides=address_overrides,
            bol_number_override=bol_number_override,
            bol_data=cached_bol_data  # Pass cached data to skip AI generation
        )
        ps_result = doc_manager.generate_and_fill_packing_slip(
            po_document_id=doc_id,
            use_saved_schema=use_schema,
            address_overrides=address_overrides,
            packing_slip_data=cached_ps_data  # Pass cached data to skip AI generation
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
