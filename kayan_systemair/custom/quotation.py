import frappe
from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import compute_pricing

def before_save(doc, method):
    """Triggered by hooks.py for every Quotation save."""
    if not getattr(doc, "is_systemair_quotation", 0):
        return
    _recalculate_all_items(doc)
    _compute_quotation_totals(doc)

def _recalculate_all_items(doc):
    for item in doc.get("sa_items") or []:
        # Apply quotation-level defaults if item-level not set
        if not item.supplier_discount:
            item.supplier_discount = doc.sa_default_discount or 0
        if not item.additional_discount:
            item.additional_discount = doc.sa_additional_discount or 0
        if not item.customs_rate:
            item.customs_rate = doc.sa_default_customs or 0
        if not item.margin_percent:
            item.margin_percent = doc.sa_default_margin or 50
        compute_pricing(item, doc)

def _compute_quotation_totals(doc):
    total_cif    = sum(flt(r.cif) for r in doc.get("sa_items") or [])
    grand_total  = sum(flt(r.total_price_egp) for r in doc.get("sa_items") or [])
    total_ddp    = sum(flt(r.ddp_cost) for r in doc.get("sa_items") or [])

    doc.sa_total_cif_eur = total_cif
    doc.sa_grand_total_egp = grand_total
    doc.grand_total = grand_total

    # Effective margin = (Grand Total - Total DDP) / Grand Total
    if grand_total:
        doc.sa_effective_margin = round((grand_total - total_ddp) / grand_total * 100, 2)

def on_submit(doc, method):
    if not getattr(doc, "is_systemair_quotation", 0):
        return
    # Lock calculated fields on submission if needed

def on_cancel(doc, method):
    pass

def flt(val, precision=None):
    from frappe.utils import flt as _flt
    return _flt(val, precision)
