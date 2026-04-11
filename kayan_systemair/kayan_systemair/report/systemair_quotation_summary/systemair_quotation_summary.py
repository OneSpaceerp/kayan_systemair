"""
SystemAir Quotation Summary Report
====================================
Script Report — Columns: Quotation No., Date, Customer, Project Ref, Status,
Item Count, Total CIF (EUR), Grand Total (EGP), Effective Margin %

Filters: date_from, date_to, customer, status
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Quotation No."),
            "fieldtype": "Link",
            "options": "Quotation",
            "width": 160,
        },
        {
            "fieldname": "transaction_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "fieldname": "customer_name",
            "label": _("Customer"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "sa_project_ref",
            "label": _("Project Reference"),
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "item_count",
            "label": _("Item Count"),
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "fieldname": "sa_total_cif_eur",
            "label": _("Total CIF (EUR)"),
            "fieldtype": "Currency",
            "options": "EUR",
            "width": 140,
        },
        {
            "fieldname": "sa_grand_total_egp",
            "label": _("Grand Total (EGP)"),
            "fieldtype": "Currency",
            "options": "EGP",
            "width": 150,
        },
        {
            "fieldname": "sa_effective_margin",
            "label": _("Effective Margin %"),
            "fieldtype": "Percent",
            "width": 130,
        },
    ]


def get_data(filters):
    conditions, values = build_conditions(filters)

    rows = frappe.db.sql(
        f"""
        SELECT
            q.name,
            q.transaction_date,
            q.customer_name,
            q.sa_project_ref,
            q.status,
            COUNT(DISTINCT sqi.name) AS item_count,
            q.sa_total_cif_eur,
            q.sa_grand_total_egp,
            q.sa_effective_margin
        FROM `tabQuotation` q
        LEFT JOIN `tabSystemAir Quotation Item` sqi
            ON sqi.parent = q.name AND sqi.parenttype = 'Quotation'
        WHERE
            q.is_systemair_quotation = 1
            AND q.docstatus < 2
            {conditions}
        GROUP BY q.name
        ORDER BY q.transaction_date DESC
        """,
        values,
        as_dict=True,
    )

    data = []
    for row in rows:
        data.append({
            "name": row.name,
            "transaction_date": row.transaction_date,
            "customer_name": row.customer_name,
            "sa_project_ref": row.sa_project_ref or "",
            "status": row.status,
            "item_count": row.item_count or 0,
            "sa_total_cif_eur": flt(row.sa_total_cif_eur, 2),
            "sa_grand_total_egp": flt(row.sa_grand_total_egp, 2),
            "sa_effective_margin": flt(row.sa_effective_margin, 2),
        })

    return data


def build_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("date_from"):
        conditions += " AND q.transaction_date >= %(date_from)s"
        values["date_from"] = filters["date_from"]

    if filters.get("date_to"):
        conditions += " AND q.transaction_date <= %(date_to)s"
        values["date_to"] = filters["date_to"]

    if filters.get("customer"):
        conditions += " AND q.party_name = %(customer)s"
        values["customer"] = filters["customer"]

    if filters.get("status"):
        conditions += " AND q.status = %(status)s"
        values["status"] = filters["status"]

    return conditions, values
