"""
Quotation Doc Events — kayan_systemair
======================================
Hooks into the standard ERPNext Quotation DocType to:
1. Apply quotation-level defaults to all SA items rows
2. Run the 16-step pricing engine on every SA item row
3. Compute total CIF (EUR), grand total (EGP), and effective margin %
4. Compute accessory total_price_egp values
"""

import frappe
from frappe import _
from frappe.utils import flt

from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import (
    compute_pricing,
)


def before_save(doc, method=None):
    """
    Triggered before every Quotation save.
    Only processes SA fields if is_systemair_quotation == 1.
    """
    if not doc.get("is_systemair_quotation"):
        return

    _ensure_eur_egp_rate(doc)
    _apply_defaults_to_items(doc)
    _compute_all_item_pricing(doc)
    _compute_accessory_totals(doc)
    _compute_quotation_totals(doc)


def on_submit(doc, method=None):
    """Post-submit actions for SystemAir quotations."""
    if not doc.get("is_systemair_quotation"):
        return
    # Nothing additional required at submit time beyond standard ERPNext flow.


def on_cancel(doc, method=None):
    """Post-cancel actions for SystemAir quotations."""
    if not doc.get("is_systemair_quotation"):
        return
    # Nothing additional required at cancel time.


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ensure_eur_egp_rate(doc):
    """Set sa_eur_egp_rate from Price Config if not already set."""
    if not flt(doc.get("sa_eur_egp_rate")):
        try:
            config = frappe.get_cached_doc("SystemAir Price Config")
            doc.sa_eur_egp_rate = flt(config.default_currency_rate)
        except Exception:
            pass  # Config may not exist on fresh install before fixtures loaded


def _apply_defaults_to_items(doc):
    """
    For each SA item row, fill in empty pricing fields from quotation-level defaults.
    Only fills if the field is falsy (None, 0, or empty string).
    """
    default_discount = flt(doc.get("sa_default_discount"))
    default_margin = flt(doc.get("sa_default_margin"))
    default_customs = flt(doc.get("sa_default_customs"))
    default_add_disc = flt(doc.get("sa_additional_discount"))

    for row in (doc.get("sa_items") or []):
        # Supplier discount
        if not flt(row.get("supplier_discount")) and default_discount:
            row.supplier_discount = default_discount

        # Additional discount
        if not flt(row.get("additional_discount")) and default_add_disc:
            row.additional_discount = default_add_disc

        # Margin
        if not flt(row.get("margin_percent")):
            if default_margin:
                row.margin_percent = default_margin
            else:
                # Fall back to Price Config
                try:
                    config = frappe.get_cached_doc("SystemAir Price Config")
                    row.margin_percent = flt(config.default_margin)
                except Exception:
                    row.margin_percent = 50.0

        # Customs duty
        if not flt(row.get("customs_rate")) and default_customs:
            row.customs_rate = default_customs

        # EX price: use Germany list price as default if not manually set
        if not flt(row.get("ex_price")) and flt(row.get("germany_list_price")):
            row.ex_price = flt(row.germany_list_price)


def _compute_all_item_pricing(doc):
    """Run pricing engine on every SA item row that has an EX price."""
    errors = []
    for row in (doc.get("sa_items") or []):
        if not flt(row.get("ex_price")):
            # Skip rows with no price — will be caught on submit if still missing
            continue
        try:
            compute_pricing(row, doc)
        except frappe.ValidationError as e:
            errors.append(str(e))

    if errors:
        frappe.throw(
            _("Pricing errors:\n") + "\n".join(errors),
            frappe.ValidationError,
        )


def _compute_accessory_totals(doc):
    """
    Compute total_price_egp for each accessory:
    total_price_egp = unit_price_eur × qty × eur_egp_rate
    (No margin, customs, or VAT applied to accessories — simple conversion)
    """
    eur_egp_rate = flt(doc.get("sa_eur_egp_rate"))
    if not eur_egp_rate:
        return

    for row in (doc.get("sa_accessories") or []):
        qty = flt(row.get("qty")) or 1.0
        unit_price_eur = flt(row.get("unit_price_eur"))
        row.total_price_egp = flt(unit_price_eur * qty * eur_egp_rate, 2)


def _compute_quotation_totals(doc):
    """
    Compute and set:
    - sa_total_cif_eur   : sum of all item CIF values (EUR)
    - sa_grand_total_egp : sum of all item total_price_egp + accessory total_price_egp
    - sa_effective_margin: (grand_total - total_ddp) / grand_total × 100
    """
    total_cif_eur = 0.0
    grand_total_egp = 0.0
    total_ddp_egp = 0.0

    for row in (doc.get("sa_items") or []):
        total_cif_eur += flt(row.get("cif"))
        grand_total_egp += flt(row.get("total_price_egp"))
        total_ddp_egp += flt(row.get("ddp_cost"))

    for row in (doc.get("sa_accessories") or []):
        grand_total_egp += flt(row.get("total_price_egp"))

    doc.sa_total_cif_eur = flt(total_cif_eur, 2)
    doc.sa_grand_total_egp = flt(grand_total_egp, 2)

    if grand_total_egp > 0:
        effective_margin = (grand_total_egp - total_ddp_egp) / grand_total_egp * 100.0
        doc.sa_effective_margin = flt(effective_margin, 2)
    else:
        doc.sa_effective_margin = 0.0
