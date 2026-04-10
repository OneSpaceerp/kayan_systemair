import frappe

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Quotation",       "fieldname": "parent",             "fieldtype": "Link",     "options": "Quotation", "width": 130},
        {"label": "Item Code",       "fieldname": "item_code",          "fieldtype": "Link",     "options": "Item",      "width": 130},
        {"label": "Item Name",       "fieldname": "item_name",          "fieldtype": "Data",     "width": 160},
        {"label": "EX Price (EUR)",  "fieldname": "ex_price",           "fieldtype": "Currency", "width": 130},
        {"label": "Discount %",      "fieldname": "supplier_discount",  "fieldtype": "Percent",  "width": 100},
        {"label": "CIF (EUR)",       "fieldname": "cif",                "fieldtype": "Currency", "width": 100},
        {"label": "Customs %",       "fieldname": "customs_rate",       "fieldtype": "Percent",  "width": 100},
        {"label": "DDP Cost (EUR)",  "fieldname": "ddp_cost",           "fieldtype": "Currency", "width": 120},
        {"label": "Selling Price (EGP)","fieldname": "total_price_egp", "fieldtype": "Currency", "width": 130},
        {"label": "Margin %",        "fieldname": "margin_percent",     "fieldtype": "Percent",  "width": 100},
    ]

    conditions = "q.is_systemair_quotation = 1"

    data = frappe.db.sql(f"""
        SELECT
            qi.parent, qi.item_code, qi.item_name, qi.ex_price,
            qi.supplier_discount, qi.cif, qi.customs_rate, qi.ddp_cost,
            qi.total_price_egp, qi.margin_percent
        FROM `tabSystemAir Quotation Item` qi
        JOIN `tabQuotation` q ON q.name = qi.parent
        WHERE {conditions}
        ORDER BY qi.parent DESC
    """, as_dict=True)

    return columns, data
