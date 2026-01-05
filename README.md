## Purchase Order (PO) Fields

- Buyer Name
- Sales Person Name
- Phone number
- email
- PO Number
- PO Date
- Company Name 
- Ship to / From Address
- Delivery Date
- Customer PO#
- Item 
- Material Description
- Quantity and Unit
- Order vs. Delivery Quantity (these differ) in both lb and kg
- Manually enter UN Code


## Bill of Lading

Address Class
- Name 
- Address
- City/State/Zip

Order Class
- {Customer ID} {PO Number}
- Material Name 
- Number of PKGS (IBC)
- Weight (kg or lb)
- Country of Origin (Country Enum)
- {Customer ID} Sales Order: {Sales Order Number -> YearMonthBOLNumber Concatenated}
- Customer PO# {BUR- or some other Customer PO# parsed}
- Additional Shipper Info


Product Class
- Handling Unit
    - QTY
    - Type [IBC]
- Name
- Description
- Package
    - QTY
    - Type [kg, lbs]
- Weight

Ship From (Address Class)
Ship To (Address Class)
Third Part Freight Charges Bill To (Address Class)

Bill of Lading (BOL) Number (Num)

Carrier Name (Warehouse Enum)

COD Amount

** TLDR Capture All the Fields for the BOL Form **


## Packing Slip

- Date
- Customer ID
- Order Date
- Purchase Order #
- Salesperson
- Packing Date
- Quantity
- Item #
- Product Description (Product Class w. Additional Info)
- Total Quantity of Goods/Boxes
- Special Notes
- Checked By
