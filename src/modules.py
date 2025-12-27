"""
Logistics Data Models
Clean and minimal class scheme for Purchase Orders, Bills of Lading, and Packing Slips.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List


# ============================================================================
# ENUMS
# ============================================================================

class Country(str, Enum):
    """Country codes for international shipping"""
    USA = "USA"
    CANADA = "Canada"
    MEXICO = "Mexico"
    # Add more as needed


class PackageType(str, Enum):
    """Types of packaging units"""
    IBC = "IBC"
    DRUM = "Drum"
    PALLET = "Pallet"
    BOX = "Box"


class WeightUnit(str, Enum):
    """Weight measurement units"""
    KG = "kg"
    LB = "lb"


class Warehouse(str, Enum):
    """Warehouse/Carrier locations"""
    MAIN = "Main Warehouse"
    SECONDARY = "Secondary Warehouse"
    # Add specific carriers as needed


class UnitType(str, Enum):
    """Unit types for products and packages"""
    KG = "kg"
    LB = "lb"
    IBC = "IBC"
    DRUM = "Drum"
    PALLET = "Pallet"
    BOX = "Box"
    EACH = "each"


class WarehouseCarrier(str, Enum):
    """Warehouse and carrier options (alias for Warehouse)"""
    MAIN = "Main Warehouse"
    SECONDARY = "Secondary Warehouse"
    CUSTOM = "Custom"


# ============================================================================
# BASE CLASSES
# ============================================================================

@dataclass
class Address:
    """Address information for shipping"""
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Package:
    """Package information with quantity and type"""
    quantity: int
    type: str  # Can be PackageType or WeightUnit depending on context
    
    def __str__(self):
        return f"{self.quantity} {self.type}"


# ============================================================================
# PRODUCT & MATERIAL
# ============================================================================

@dataclass
class Product:
    """Product/Material details for shipping"""
    name: str
    description: str
    item_number: Optional[str] = None
    un_code: Optional[str] = None  # UN Code for hazardous materials
    
    # Handling unit (e.g., 2 IBC)
    handling_unit: Optional[Package] = None
    
    # Package/Weight (e.g., 1000 kg)
    package: Optional[Package] = None
    weight: Optional[float] = None
    
    def __str__(self):
        return f"{self.name} - {self.description}"


# ============================================================================
# PURCHASE ORDER (PO)
# ============================================================================

@dataclass
class PurchaseOrder:
    """Purchase Order data"""
    # Identification
    po_number: str
    po_date: date
    customer_po: Optional[str] = None
    
    # People
    buyer_name: str = ""
    sales_person: str = ""
    phone: Optional[str] = None
    email: Optional[str] = None
    company_name: str = ""
    
    # Shipping
    ship_from: Optional[Address] = None
    ship_to: Optional[Address] = None
    delivery_date: Optional[date] = None
    
    # Items
    items: List[Product] = field(default_factory=list)
    
    # Quantities
    order_quantity: Optional[float] = None
    delivery_quantity: Optional[float] = None
    quantity_unit: str = "kg"  # or lb
    
    def __str__(self):
        return f"PO {self.po_number} - {self.company_name}"


# ============================================================================
# BILL OF LADING (BOL)
# ============================================================================

@dataclass
class Order:
    """Order details for BOL"""
    customer_id: str
    po_number: str
    sales_order_number: str  # YearMonthBOLNumber concatenated
    material_name: str
    num_packages: int  # Number of IBCs, etc.
    weight: float
    weight_unit: str = "kg"
    country_of_origin: str = "USA"
    customer_po: Optional[str] = None
    additional_shipper_info: Optional[str] = None
    
    def __str__(self):
        return f"{self.customer_id} {self.po_number}"


@dataclass
class BillOfLading:
    """Bill of Lading document"""
    # BOL Number
    bol_number: str
    bol_date: date = field(default_factory=date.today)
    
    # Addresses
    ship_from: Optional[Address] = None
    ship_to: Optional[Address] = None
    bill_to: Optional[Address] = None  # Third party freight charges
    
    # Products & Orders
    products: List[Product] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    
    # Carrier
    carrier_name: str = ""
    
    # Financial
    cod_amount: Optional[float] = None
    
    # Notes
    special_instructions: Optional[str] = None
    
    def __str__(self):
        return f"BOL {self.bol_number}"


# ============================================================================
# PACKING SLIP
# ============================================================================

@dataclass
class PackingSlipItem:
    """Single item on a packing slip"""
    item_number: str
    product_description: str
    quantity: int
    unit: str = "each"


@dataclass
class PackingSlip:
    """Packing Slip document"""
    # Dates
    date: date = field(default_factory=date.today)
    order_date: Optional[date] = None
    packing_date: Optional[date] = None
    
    # Identification
    customer_id: str = ""
    purchase_order: str = ""
    
    # People
    salesperson: str = ""
    checked_by: Optional[str] = None
    
    # Addresses
    ship_to: Optional[Address] = None
    shipping_address: Optional[Address] = None  # Alternative shipping address if different
    
    # Items
    items: List[PackingSlipItem] = field(default_factory=list)
    
    # Totals
    total_quantity: int = 0
    total_boxes: int = 0
    
    # Notes
    special_notes: Optional[str] = None
    
    def __str__(self):
        return f"Packing Slip - {self.customer_id} PO: {self.purchase_order}"


# ============================================================================
# DATA STORE CLASSES (for customer/product management)
# ============================================================================

@dataclass
class Buyer:
    """Buyer contact for an account"""
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class SalesPerson:
    """Sales team member"""
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'employee_id': self.employee_id,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class Account:
    """Customer account"""
    id: str
    company_name: str
    customer_id: str
    buyers: List[Buyer] = field(default_factory=list)
    addresses: List[Address] = field(default_factory=list)
    common_products: List[str] = field(default_factory=list)  # Product IDs
    purchase_orders: List[str] = field(default_factory=list)  # PO IDs
    default_payment_terms: str = "NET 90 DAYS"
    default_delivery_terms: str = "Free Carrier DESTINATION"
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_buyer(self, buyer: Buyer):
        self.buyers.append(buyer)

    def add_address(self, address: Address):
        self.addresses.append(address)

    def add_common_product(self, product_id: str):
        if product_id not in self.common_products:
            self.common_products.append(product_id)

    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'customer_id': self.customer_id,
            'buyers': [b.__dict__ for b in self.buyers],
            'addresses': [a.__dict__ for a in self.addresses],
            'common_products': self.common_products,
            'purchase_orders': self.purchase_orders,
            'default_payment_terms': self.default_payment_terms,
            'default_delivery_terms': self.default_delivery_terms,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        data['buyers'] = [Buyer(**b) for b in data.get('buyers', [])]
        data['addresses'] = [Address(**a) for a in data.get('addresses', [])]
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class SavedProduct:
    """Saved product in catalog"""
    id: str
    name: str
    description: str
    item_number: Optional[str] = None
    un_code: Optional[str] = None
    default_unit_type: UnitType = UnitType.KG
    default_handling_unit_type: UnitType = UnitType.IBC
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'item_number': self.item_number,
            'un_code': self.un_code,
            'default_unit_type': self.default_unit_type.value,
            'default_handling_unit_type': self.default_handling_unit_type.value,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        data['default_unit_type'] = UnitType(data['default_unit_type'])
        data['default_handling_unit_type'] = UnitType(data['default_handling_unit_type'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class SellerInfo:
    """Seller company information"""
    id: str
    company_name: str
    addresses: List[Address] = field(default_factory=list)
    sales_people: List[SalesPerson] = field(default_factory=list)
    default_carrier: Optional[WarehouseCarrier] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_address(self, address: Address):
        self.addresses.append(address)

    def add_sales_person(self, salesperson: SalesPerson):
        self.sales_people.append(salesperson)

    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'addresses': [a.__dict__ for a in self.addresses],
            'sales_people': [sp.to_dict() for sp in self.sales_people],
            'default_carrier': self.default_carrier.value if self.default_carrier else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        data['addresses'] = [Address(**a) for a in data.get('addresses', [])]
        data['sales_people'] = [SalesPerson.from_dict(sp) for sp in data.get('sales_people', [])]
        if data.get('default_carrier'):
            data['default_carrier'] = WarehouseCarrier(data['default_carrier'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_address(name: str, address: str, city: str, state: str, 
                  zip_code: str, country: str = "USA", 
                  phone: Optional[str] = None, email: Optional[str] = None) -> Address:
    """Helper function to create an Address"""
    return Address(
        name=name,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
        country=country,
        phone=phone,
        email=email
    )


def create_product(name: str, description: str, 
                  item_number: Optional[str] = None,
                  handling_qty: Optional[int] = None,
                  handling_type: str = "IBC",
                  weight: Optional[float] = None,
                  weight_unit: str = "kg") -> Product:
    """Helper function to create a Product"""
    handling_unit = Package(handling_qty, handling_type) if handling_qty else None
    package = Package(int(weight or 0), weight_unit) if weight else None
    
    return Product(
        name=name,
        description=description,
        item_number=item_number,
        handling_unit=handling_unit,
        package=package,
        weight=weight
    )

