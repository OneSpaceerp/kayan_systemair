"""
SystemAir Pricing Engine
========================
Replicates the 16-step formula chain from the client's Excel COST sheet
(columns L–AB).  Must match Excel output to ±0.01 EUR for any input set.

Validation Test Cases (all must pass):
---------------------------------------
Test 1 — Standard fan, 0% customs, 50% margin:
    ex_price=1000, qty=2, supplier_discount=20, additional_discount=0,
    customs_rate=0, margin_percent=50, eur_egp_rate=50, shipping_rate=12
    Expected: basic_ex_price=1600.0, shipping_cost=192.0, cif=1792.0

Test 2 — Excel parity:
    ex_price=500, qty=1, supplier_discount=0, additional_discount=0,
    customs_rate=0, margin_percent=50, eur_egp_rate=50, shipping_rate=12
    Expected: cif=560.0, total_price_egp=560×1.1235×1.5×50×1.14

Test 3 — Zero EX price must raise frappe.ValidationError
"""

import frappe
from frappe import _
from frappe.utils import flt


def compute_pricing(item_row, quotation_doc):
    """
    Compute all 16 pricing steps for a single SystemAir Quotation Item row
    and write results back to item_row.

    Steps:
        1.  ex_price           — from item_row (must be > 0)
        2.  supplier_discount  — percent e.g. 20 means 20%
        3.  qty                — quantity
        4.  basic_ex_price     = ex_price × qty × (1 − supplier_discount/100)
        5.  additional_discount — percent
        6.  final_ex_price     = basic_ex_price × (1 − additional_discount/100)
        7.  shipping_cost      = basic_ex_price × (shipping_rate/100)
        8.  cif                = final_ex_price + shipping_cost
        9.  cost_factors       = CF1 × CF2  (from Price Config)
        10. customs_rate       — percent per item
        11. vat_multiplier     = 1 + vat_rate/100
        12. currency_rate      = EUR→EGP from quotation header
        13. ddp_cost           = cif × cost_factors × currency_rate
                                  × vat_multiplier × (1 + customs_rate/100)
        14. margin             — percent
        15. total_price_egp    = cif × cost_factors × (1 + margin/100)
                                  × currency_rate × vat_multiplier
                                  × (1 + customs_rate/100)
        16. unit_price_egp     = total_price_egp / qty

    Raises:
        frappe.ValidationError: if ex_price is 0 or missing.
        frappe.ValidationError: if qty is 0 or negative.
    """
    # ------------------------------------------------------------------ #
    # Fetch global price configuration                                     #
    # ------------------------------------------------------------------ #
    config = frappe.get_cached_doc("SystemAir Price Config")
    vat_rate = flt(config.vat_rate)                       # e.g. 14
    cost_factor_1 = flt(config.cost_factor_1)             # e.g. 1.05
    cost_factor_2 = flt(config.cost_factor_2)             # e.g. 1.07
    combined_cost_factor = flt(cost_factor_1 * cost_factor_2, 6)  # 1.1235
    default_shipping_rate = flt(config.default_shipping_rate)     # e.g. 12

    # ------------------------------------------------------------------ #
    # Step 1 — EX Price                                                    #
    # ------------------------------------------------------------------ #
    ex_price = flt(item_row.ex_price, 4)
    if not ex_price or ex_price <= 0:
        frappe.throw(
            _(
                "Row {0}: EX Price (EUR) must be greater than zero. "
                "Please set a list price or enter the EX price manually."
            ).format(item_row.idx or "?"),
            frappe.ValidationError,
        )

    # ------------------------------------------------------------------ #
    # Step 2 — Supplier Discount (%)                                       #
    # ------------------------------------------------------------------ #
    supplier_discount = flt(item_row.supplier_discount, 4)  # e.g. 20.0

    # ------------------------------------------------------------------ #
    # Step 3 — Quantity                                                    #
    # ------------------------------------------------------------------ #
    qty = flt(item_row.qty, 4)
    if qty <= 0:
        frappe.throw(
            _("Row {0}: Quantity must be greater than zero.").format(item_row.idx or "?"),
            frappe.ValidationError,
        )

    # ------------------------------------------------------------------ #
    # Step 4 — Basic EX Price = ex_price × qty × (1 − supplier_discount%) #
    # ------------------------------------------------------------------ #
    basic_ex_price = flt(
        ex_price * qty * (1.0 - supplier_discount / 100.0),
        4,
    )

    # ------------------------------------------------------------------ #
    # Step 5 — Additional Discount (%)                                     #
    # ------------------------------------------------------------------ #
    additional_discount = flt(item_row.additional_discount, 4)

    # ------------------------------------------------------------------ #
    # Step 6 — Final EX Price = basic_ex_price × (1 − additional_discount%) #
    # ------------------------------------------------------------------ #
    final_ex_price = flt(
        basic_ex_price * (1.0 - additional_discount / 100.0),
        4,
    )

    # ------------------------------------------------------------------ #
    # Step 7 — Shipping Cost = basic_ex_price × (shipping_rate / 100)     #
    # Note: shipping is applied to basic_ex_price, not final_ex_price      #
    # ------------------------------------------------------------------ #
    shipping_rate = flt(
        item_row.get("shipping_rate") or quotation_doc.get("sa_shipping_rate") or default_shipping_rate,
        4,
    )
    shipping_cost = flt(basic_ex_price * (shipping_rate / 100.0), 4)

    # ------------------------------------------------------------------ #
    # Step 8 — CIF = final_ex_price + shipping_cost                        #
    # ------------------------------------------------------------------ #
    cif = flt(final_ex_price + shipping_cost, 4)

    # ------------------------------------------------------------------ #
    # Step 9 — Cost Factors = CF1 × CF2                                    #
    # ------------------------------------------------------------------ #
    cost_factors = combined_cost_factor  # 1.1235

    # ------------------------------------------------------------------ #
    # Step 10 — Customs Rate (%) — per item override                       #
    # ------------------------------------------------------------------ #
    customs_rate = flt(item_row.customs_rate, 4)

    # ------------------------------------------------------------------ #
    # Step 11 — VAT Multiplier = 1 + vat_rate/100                         #
    # ------------------------------------------------------------------ #
    vat_multiplier = flt(1.0 + vat_rate / 100.0, 6)  # e.g. 1.14

    # ------------------------------------------------------------------ #
    # Step 12 — Currency Rate (EUR → EGP)                                  #
    # ------------------------------------------------------------------ #
    currency_rate = flt(quotation_doc.get("sa_eur_egp_rate") or config.default_currency_rate, 4)
    if currency_rate <= 0:
        frappe.throw(
            _("EUR/EGP Exchange Rate must be greater than zero."),
            frappe.ValidationError,
        )

    # ------------------------------------------------------------------ #
    # Step 13 — DDP Cost                                                   #
    # ddp_cost = cif × cost_factors × currency_rate × vat_multiplier      #
    #             × (1 + customs_rate/100)                                 #
    # ------------------------------------------------------------------ #
    customs_multiplier = flt(1.0 + customs_rate / 100.0, 6)
    ddp_cost = flt(
        cif * cost_factors * currency_rate * vat_multiplier * customs_multiplier,
        4,
    )

    # ------------------------------------------------------------------ #
    # Step 14 — Margin (%) per item                                        #
    # ------------------------------------------------------------------ #
    margin_percent = flt(item_row.margin_percent, 4)
    margin_multiplier = flt(1.0 + margin_percent / 100.0, 6)

    # ------------------------------------------------------------------ #
    # Step 15 — Total Price (EGP)                                          #
    # total_price = cif × cost_factors × (1 + margin%) × currency_rate    #
    #               × vat_multiplier × (1 + customs%)                     #
    # ------------------------------------------------------------------ #
    total_price_egp = flt(
        cif * cost_factors * margin_multiplier * currency_rate * vat_multiplier * customs_multiplier,
        4,
    )

    # ------------------------------------------------------------------ #
    # Step 16 — Unit Price (EGP) = total_price / qty                      #
    # ------------------------------------------------------------------ #
    unit_price_egp = flt(total_price_egp / qty, 4)

    # ------------------------------------------------------------------ #
    # Write results back to item_row                                       #
    # Final monetary values rounded to 2 decimal places                   #
    # ------------------------------------------------------------------ #
    item_row.basic_ex_price = flt(basic_ex_price, 2)
    item_row.shipping_cost = flt(shipping_cost, 2)
    item_row.final_ex_price = flt(final_ex_price, 2)
    item_row.cif = flt(cif, 2)
    item_row.ddp_cost = flt(ddp_cost, 2)
    item_row.unit_price_egp = flt(unit_price_egp, 2)
    item_row.total_price_egp = flt(total_price_egp, 2)
    item_row.rate = flt(unit_price_egp, 2)
    item_row.amount = flt(total_price_egp, 2)

    return {
        "ex_price": ex_price,
        "supplier_discount": supplier_discount,
        "qty": qty,
        "basic_ex_price": item_row.basic_ex_price,
        "additional_discount": additional_discount,
        "final_ex_price": item_row.final_ex_price,
        "shipping_rate": shipping_rate,
        "shipping_cost": item_row.shipping_cost,
        "cif": item_row.cif,
        "cost_factors": cost_factors,
        "customs_rate": customs_rate,
        "vat_multiplier": vat_multiplier,
        "currency_rate": currency_rate,
        "ddp_cost": item_row.ddp_cost,
        "margin_percent": margin_percent,
        "total_price_egp": item_row.total_price_egp,
        "unit_price_egp": item_row.unit_price_egp,
    }
