import frappe
from frappe.utils import flt

def compute_pricing(item_row, quotation_doc):
    """
    Full 16-step pricing formula chain.
    Replicates Excel COST sheet columns L\u2013AB exactly.
    """
    cfg = frappe.get_single("SystemAir Price Config")

    # \u2500\u2500 Inputs \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    ex_price            = flt(item_row.ex_price)
    qty                 = flt(item_row.qty) or 1
    supplier_discount   = flt(item_row.supplier_discount) / 100
    additional_discount = flt(item_row.additional_discount) / 100
    customs_rate        = flt(item_row.customs_rate) / 100
    margin              = flt(item_row.margin_percent) / 100
    shipping_rate       = flt(
        getattr(quotation_doc, "sa_shipping_rate", None) or cfg.default_shipping_rate
    ) / 100
    currency_rate       = flt(
        getattr(quotation_doc, "sa_eur_egp_rate", None) or cfg.default_currency_rate
    ) or 1
    cost_factors        = flt(cfg.cost_factor_1) * flt(cfg.cost_factor_2)  # 1.05 \u00d7 1.07
    vat_multiplier      = 1 + (flt(cfg.vat_rate) / 100)                    # 1.14

    if not ex_price:
        frappe.throw(f"EX Price must be set for item {item_row.item_code or item_row.idx}")

    # \u2500\u2500 Steps 4\u201316 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    basic_ex_price   = ex_price * qty * (1 - supplier_discount)            # Step 4  \u2192 Col P
    final_ex_price   = basic_ex_price * (1 - additional_discount)          # Step 6  \u2192 Col R
    shipping_cost    = basic_ex_price * shipping_rate                       # Step 7  \u2192 Col S
    cif              = final_ex_price + shipping_cost                       # Step 8  \u2192 Col T
    ddp_cost         = (cif * cost_factors * currency_rate                  # Step 13 \u2192 Col Y
                        * vat_multiplier * (1 + customs_rate))
    total_price      = (cif * cost_factors * (1 + margin)                  # Step 15 \u2192 Col AB
                        * currency_rate * vat_multiplier * (1 + customs_rate))
    unit_price       = total_price / qty                                    # Step 16 \u2192 Col AA

    # \u2500\u2500 Write back \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    item_row.basic_ex_price  = round(basic_ex_price, 4)
    item_row.final_ex_price  = round(final_ex_price, 4)
    item_row.shipping_cost   = round(shipping_cost, 4)
    item_row.cif             = round(cif, 4)
    item_row.ddp_cost        = round(ddp_cost, 4)
    item_row.unit_price_egp  = round(unit_price, 2)
    item_row.total_price_egp = round(total_price, 2)
    item_row.rate            = round(unit_price, 2)
    item_row.amount          = round(total_price, 2)

    return item_row

def get_list_price(item_code, price_list):
    """
    Exact match first, fuzzy match fallback.
    Returns float or list of dicts (for fuzzy).
    """
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "selling": 1},
        "price_list_rate"
    )
    if price:
        return flt(price)

    # Fuzzy fallback via item_name
    results = frappe.db.sql("""
        SELECT ip.item_code, ip.price_list_rate, i.item_name
        FROM   `tabItem Price` ip
        JOIN   `tabItem` i ON i.item_code = ip.item_code
        WHERE  ip.price_list = %s
        AND    i.item_name LIKE %s
        LIMIT  10
    """, (price_list, f"%{item_code}%"), as_dict=True)

    return results if results else None
