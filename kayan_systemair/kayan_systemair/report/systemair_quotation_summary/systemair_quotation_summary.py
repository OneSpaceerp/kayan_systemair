import frappe

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Quotation",       "fieldname": "name",               "fieldtype": "Link",     "options": "Quotation", "width": 130},
        {"label": "Date",            "fieldname": "transaction_date",   "fieldtype": "Date",     "width": 100},
        {"label": "Customer",        "fieldname": "party_name",         "fieldtype": "Data",     "width": 160},
        {"label": "Project Ref",     "fieldname": "sa_project_ref",     "fieldtype": "Data",     "width": 130},
        {"label": "Status",          "fieldname": "status",             "fieldtype": "Data",     "width": 100},
        {"label": "Fan Items",       "fieldname": "num_items",          "fieldtype": "Int",      "width": 80},
        {"label": "Total CIF (EUR)", "fieldname": "sa_total_cif_eur",   "fieldtype": "Currency", "width": 130},
        {"label": "Grand Total (EGP)","fieldname": "sa_grand_total_egp","fieldtype": "Currency", "width": 140},
        {"label": "Effective Margin %","fieldname": "sa_effective_margin","fieldtype": "Percent","width": 120},
    ]

    conditions = "q.is_systemair_quotation = 1"
    if filters.get("from_date"):
        conditions += f" AND q.transaction_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND q.transaction_date <= '{filters['to_date']}'"
    if filters.get("status"):
        conditions += f" AND q.status = '{filters['status']}'"
    if filters.get("customer"):
        conditions += f" AND q.party_name = '{filters['customer']}'"

    data = frappe.db.sql(f"""
        SELECT
            q.name, q.transaction_date, q.party_name,
            q.sa_project_ref, q.status,
            COUNT(qi.name) AS num_items,
            q.sa_total_cif_eur, q.sa_grand_total_egp, q.sa_effective_margin
        FROM `tabQuotation` q
        LEFT JOIN `tabSystemAir Quotation Item` qi ON qi.parent = q.name
        WHERE {conditions}
        GROUP BY q.name
        ORDER BY q.transaction_date DESC
    """, as_dict=True)

    return columns, data
