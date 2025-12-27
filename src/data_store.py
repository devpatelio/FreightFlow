"""
Data Store Manager
==================
Handles persistent storage for Accounts, Products, and Seller Information
"""

import json
import os
import uuid
from typing import Optional, List, Dict
from datetime import datetime
from modules import Account, SavedProduct, SellerInfo, Buyer, SalesPerson, Address


class DataStore:
    """
    Centralized data storage for all logistics entities
    """
    
    def __init__(self, data_path: str = "data_store.json"):
        self.data_path = data_path
        self._ensure_store_exists()
    
    def _ensure_store_exists(self):
        """Create data store file if it doesn't exist"""
        if not os.path.exists(self.data_path):
            initial_data = {
                'accounts': {},
                'products': {},
                'seller_info': {},
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
            }
            with open(self.data_path, 'w') as f:
                json.dump(initial_data, f, indent=2)
    
    def _load_store(self) -> Dict:
        """Load entire data store"""
        with open(self.data_path, 'r') as f:
            return json.load(f)
    
    def _save_store(self, data: Dict):
        """Save entire data store"""
        data['metadata']['last_updated'] = datetime.now().isoformat()
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    # ========================================================================
    # ACCOUNT OPERATIONS
    # ========================================================================
    
    def create_account(self, company_name: str, customer_id: str, **kwargs) -> Account:
        """Create a new account"""
        store = self._load_store()
        
        account_id = kwargs.get('id', str(uuid.uuid4()))
        
        account = Account(
            id=account_id,
            company_name=company_name,
            customer_id=customer_id,
            **{k: v for k, v in kwargs.items() if k != 'id'}
        )
        
        store['accounts'][account_id] = account.to_dict()
        self._save_store(store)
        
        return account
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """Get account by ID"""
        store = self._load_store()
        account_data = store['accounts'].get(account_id)
        
        if account_data:
            return Account.from_dict(account_data)
        return None
    
    def get_account_by_customer_id(self, customer_id: str) -> Optional[Account]:
        """Get account by customer ID"""
        store = self._load_store()
        
        for account_data in store['accounts'].values():
            if account_data.get('customer_id') == customer_id:
                return Account.from_dict(account_data)
        return None
    
    def list_accounts(self) -> List[Account]:
        """List all accounts"""
        store = self._load_store()
        return [Account.from_dict(data) for data in store['accounts'].values()]
    
    def update_account(self, account_id: str, account: Account) -> bool:
        """Update an existing account"""
        store = self._load_store()
        
        if account_id in store['accounts']:
            account.updated_at = datetime.now()
            store['accounts'][account_id] = account.to_dict()
            self._save_store(store)
            return True
        return False
    
    def delete_account(self, account_id: str) -> bool:
        """Delete an account"""
        store = self._load_store()
        
        if account_id in store['accounts']:
            del store['accounts'][account_id]
            self._save_store(store)
            return True
        return False
    
    def add_buyer_to_account(self, account_id: str, buyer: Buyer) -> bool:
        """Add a buyer to an account"""
        account = self.get_account(account_id)
        if account:
            account.add_buyer(buyer)
            return self.update_account(account_id, account)
        return False
    
    def add_address_to_account(self, account_id: str, address: Address) -> bool:
        """Add an address to an account"""
        account = self.get_account(account_id)
        if account:
            account.add_address(address)
            return self.update_account(account_id, account)
        return False
    
    # ========================================================================
    # PRODUCT OPERATIONS
    # ========================================================================
    
    def create_product(self, name: str, description: str, **kwargs) -> SavedProduct:
        """Create a new product"""
        store = self._load_store()
        
        product_id = kwargs.get('id', str(uuid.uuid4()))
        
        product = SavedProduct(
            id=product_id,
            name=name,
            description=description,
            **{k: v for k, v in kwargs.items() if k != 'id'}
        )
        
        store['products'][product_id] = product.to_dict()
        self._save_store(store)
        
        return product
    
    def get_product(self, product_id: str) -> Optional[SavedProduct]:
        """Get product by ID"""
        store = self._load_store()
        product_data = store['products'].get(product_id)
        
        if product_data:
            return SavedProduct.from_dict(product_data)
        return None
    
    def get_product_by_item_number(self, item_number: str) -> Optional[SavedProduct]:
        """Get product by item number"""
        store = self._load_store()
        
        for product_data in store['products'].values():
            if product_data.get('item_number') == item_number:
                return SavedProduct.from_dict(product_data)
        return None
    
    def list_products(self) -> List[SavedProduct]:
        """List all products"""
        store = self._load_store()
        return [SavedProduct.from_dict(data) for data in store['products'].values()]
    
    def update_product(self, product_id: str, product: SavedProduct) -> bool:
        """Update an existing product"""
        store = self._load_store()
        
        if product_id in store['products']:
            product.updated_at = datetime.now()
            store['products'][product_id] = product.to_dict()
            self._save_store(store)
            return True
        return False
    
    def delete_product(self, product_id: str) -> bool:
        """Delete a product"""
        store = self._load_store()
        
        if product_id in store['products']:
            del store['products'][product_id]
            self._save_store(store)
            return True
        return False
    
    # ========================================================================
    # SELLER INFO OPERATIONS
    # ========================================================================
    
    def create_seller_info(self, company_name: str, **kwargs) -> SellerInfo:
        """Create seller info"""
        store = self._load_store()
        
        seller_id = kwargs.get('id', 'default')
        
        seller = SellerInfo(
            id=seller_id,
            company_name=company_name,
            **{k: v for k, v in kwargs.items() if k != 'id'}
        )
        
        store['seller_info'][seller_id] = seller.to_dict()
        self._save_store(store)
        
        return seller
    
    def get_seller_info(self, seller_id: str = 'default') -> Optional[SellerInfo]:
        """Get seller info by ID"""
        store = self._load_store()
        seller_data = store['seller_info'].get(seller_id)
        
        if seller_data:
            return SellerInfo.from_dict(seller_data)
        return None
    
    def list_seller_info(self) -> List[SellerInfo]:
        """List all seller info entries"""
        store = self._load_store()
        return [SellerInfo.from_dict(data) for data in store['seller_info'].values()]
    
    def update_seller_info(self, seller_id: str, seller: SellerInfo) -> bool:
        """Update seller info"""
        store = self._load_store()
        
        if seller_id in store['seller_info']:
            seller.updated_at = datetime.now()
            store['seller_info'][seller_id] = seller.to_dict()
            self._save_store(store)
            return True
        return False
    
    def delete_seller_info(self, seller_id: str) -> bool:
        """Delete seller info"""
        store = self._load_store()
        
        if seller_id in store['seller_info']:
            del store['seller_info'][seller_id]
            self._save_store(store)
            return True
        return False
    
    def add_address_to_seller(self, seller_id: str, address: Address) -> bool:
        """Add an address to seller info"""
        seller = self.get_seller_info(seller_id)
        if seller:
            seller.add_address(address)
            return self.update_seller_info(seller_id, seller)
        return False
    
    def add_salesperson_to_seller(self, seller_id: str, salesperson: SalesPerson) -> bool:
        """Add a salesperson to seller info"""
        seller = self.get_seller_info(seller_id)
        if seller:
            seller.add_sales_person(salesperson)
            return self.update_seller_info(seller_id, seller)
        return False
    
    # ========================================================================
    # SEARCH & QUERY OPERATIONS
    # ========================================================================
    
    def search_accounts(self, query: str) -> List[Account]:
        """Search accounts by company name or customer ID"""
        accounts = self.list_accounts()
        query_lower = query.lower()
        
        return [
            account for account in accounts
            if query_lower in account.company_name.lower() or
               query_lower in account.customer_id.lower()
        ]
    
    def search_products(self, query: str) -> List[SavedProduct]:
        """Search products by name, description, or item number"""
        products = self.list_products()
        query_lower = query.lower()
        
        return [
            product for product in products
            if query_lower in product.name.lower() or
               query_lower in product.description.lower() or
               (product.item_number and query_lower in product.item_number.lower())
        ]
    
    def get_account_products(self, account_id: str) -> List[SavedProduct]:
        """Get all common products for an account"""
        account = self.get_account(account_id)
        if not account:
            return []
        
        products = []
        for product_id in account.common_products:
            product = self.get_product(product_id)
            if product:
                products.append(product)
        
        return products
    
    # ========================================================================
    # UTILITY OPERATIONS
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """Get statistics about the data store"""
        store = self._load_store()
        
        return {
            'total_accounts': len(store['accounts']),
            'total_products': len(store['products']),
            'total_sellers': len(store['seller_info']),
            'last_updated': store['metadata']['last_updated'],
            'created_at': store['metadata']['created_at']
        }
    
    def export_data(self, output_path: str) -> bool:
        """Export all data to a file"""
        try:
            store = self._load_store()
            with open(output_path, 'w') as f:
                json.dump(store, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False
    
    def import_data(self, input_path: str) -> bool:
        """Import data from a file"""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            # Validate structure
            if 'accounts' not in data or 'products' not in data or 'seller_info' not in data:
                print("Invalid data structure")
                return False
            
            self._save_store(data)
            return True
        except Exception as e:
            print(f"Error importing data: {e}")
            return False

