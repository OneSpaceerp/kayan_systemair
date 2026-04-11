"""
Margin Analysis Report
======================
Script Report — Per-item breakdown showing all pricing steps and margin.

Filters: date_from, date_to, customer, min_margin, max_margin
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
            "fieldname": "quotation",
            "label": _("Quotation"),
            "fieldtype": "Link",
            "options": "Quotation",
            "width": 150,
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
            "width": 160,
        },
        {
            "fieldname": "item_code",
            "label": _("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 220,
        },
        {
            "fieldname": "item_name",
            "label": _("Item Name"),
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "fieldname": "qty",
            "label": _("Qty"),
            "fieldtype": "Float",
            "width": 70,
        },
        {
            "fieldname": "ex_price",
            "label": _("EX Price (EUR)"),
            "fieldtype": "Currency",
            "options": "EUR",
            "width": 130,
        },
        {
            "fieldname": "supplier_discount",
            "label": _("Discount %"),
            "fieldtype": "Percent",
            "width": 100,
        },
        {
            "fieldname": "cif",
            "label": _("CIF (EUR)"),
            "fieldtype": "Currency",
            "options": "EUR",
            "width": 120,
        },
        {
            "fieldname": "customs_rate",
            "label": _("Customs %"),
            "fieldtype": "Percent",
            "width": 100,
        },
        {
            "fieldname": "ddp_cost",
            "label": _("DDP Cost (EGP)"),
            "fieldtype": "Currency",
            "options": "EGP",
            "width": 140,
        },
        {
            "fieldname": "total_price_egp",
            "label": _("Selling Price (EGP)"),
            "fieldtype": "Currency",
            "options": "EGP",
            "width": 150,
        },
        {
            "fieldname": "gross_margin",
            "label": _("Gross Margin (EGP)"),
            "fieldtype": "Currency",
            "options": "EGP",
            "width": 150,
        },
        {
            "fieldname": "margin_percent",
            "label": _("Margin %"),
            "fieldtype": "Percent",
            "width": 100,
        },
    ]


def get_data(filters):
    conditions, values = build_conditions(filters)

    rows = frappe.db.sql(
        f"""
        SELECT
            q.name AS quotation,
            q.transaction_date,
            q.customer_name,
            sqi.item_code,
            sqi.item_name,
            sqi.qty,
            sqi.ex_price,
            sqi.supplier_discount,
            sqi.cif,
            sqi.customs_rate,
            sqi.ddp_cost,
            sqi.total_price_egp,
            sqi.margin_percent
        FROM `tabQuotation` q
        JOIN `tabSystemAir Quotation Item` sqi
            ON sqi.parent = q.name AND sqi.parenttype = 'Quotation'
        WHERE
            q.is_systemair_quotation = 1
            AND q.docstatus < 2
            {conditions}
        ORDER BY q.transaction_date DESC, q.name, sqi.idx
        """,
        values,
        as_dict=True,
    )

    data = []
    for row in rows:
        selling = flt(row.total_price_egp)
        ddp = flt(row.ddp_cost)
        gross_margin = flt(selling - ddp, 2)
        margin_pct = flt(row.margin_percent, 2)

        # Apply margin filter
        if filters.get("min_margin") is not None:
            if margin_pct < flt(filters["min_margin"]):
                continue
        if filters.get("max_margin") is not None:
            if margin_pct > flt(filters["max_margin"]):
                continue

        data.append({
            "quotation": row.quotation,
            "transaction_date": row.transaction_date,
            "customer_name": row.customer_name,
            "item_code": row.item_code,
            "item_name": row.item_name,
            "qty": flt(row.qty, 2),
            "ex_price": flt(row.ex_price, 2),
            "supplier_discount": flt(row.supplier_discount, 2),
            "cif": flt(row.cif, 2),
            "customs_rate": flt(row.customs_rate, 2),
            "ddp_cost": ddp,
            "total_price_egp": selling,
            "gross_margin": gross_margin,
            "margin_percent": margin_pct,
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

    return conditions, values
