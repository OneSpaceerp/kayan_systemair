"""
Quotation Doc Events — kayan_systemair
======================================
Hooks into the standard ERPNext Quotation DocType to:
1. Apply quotation-level defaults to all SA items rows
2. Run the 16-step pricing engine on every SA item row
3. Compute total CIF (EUR), grand total (EUR), and effective margin %
4. Compute accessory total_price_eur values
5. Fold linked-accessory costs into each fan's pricing chain
"""

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.selling.doctype.quotation.quotation import Quotation

from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import (
    compute_pricing,
)


class CustomQuotation(Quotation):
    @frappe.whitelist()
    def process_item_selection(self, item_idx):
        # ERPNext looks up idx in the standard items table, but for SA quotations
        # that table only holds synced rows and may not match sa_items indices.
        # Our client-side fetch_item_prices handles all item detail lookups.
        if self.get("is_systemair_quotation"):
            return {}
        return super().process_item_selection(item_idx)


def before_save(doc, method=None):
    """
    Triggered before every Quotation save.
    Only processes SA fields if is_systemair_quotation == 1.
    """
    if not doc.get("is_systemair_quotation"):
        return

    doc.currency = "EUR"
    _ensure_eur_egp_rate(doc)
    _apply_defaults_to_items(doc)
    _compute_accessory_totals(doc)
    _compute_all_item_pricing(doc)
    _compute_quotation_totals(doc)
    _sync_to_standard_items(doc)


def on_submit(doc, method=None):
    """Post-submit actions for SystemAir quotations."""
    if not doc.get("is_systemair_quotation"):
        return


def on_cancel(doc, method=None):
    """Post-cancel actions for SystemAir quotations."""
    if not doc.get("is_systemair_quotation"):
        return


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ensure_eur_egp_rate(doc):
    """Default sa_eur_egp_rate to 1.0 (pure EUR) if not explicitly set."""
    if not flt(doc.get("sa_eur_egp_rate")):
        doc.sa_eur_egp_rate = 1.0


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
        if not flt(row.get("supplier_discount")) and default_discount:
            row.supplier_discount = default_discount

        if not flt(row.get("additional_discount")) and default_add_disc:
            row.additional_discount = default_add_disc

        if not flt(row.get("margin_percent")):
            if default_margin:
                row.margin_percent = default_margin
            else:
                try:
                    config = frappe.get_cached_doc("SystemAir Price Config")
                    row.margin_percent = flt(config.default_margin)
                except Exception:
                    row.margin_percent = 50.0

        if not flt(row.get("customs_rate")) and default_customs:
            row.customs_rate = default_customs

        if not flt(row.get("ex_price")) and flt(row.get("germany_list_price")):
            row.ex_price = flt(row.germany_list_price)


def _compute_accessory_totals(doc):
    """
    Compute total_price_eur for each accessory: qty × unit_price_eur.
    No margin, customs, or VAT — simple line total.
    Linked accessories still show their own line total (for transparency)
    but are NOT added to the quotation grand total (they flow via fan chain).
    """
    for row in (doc.get("sa_accessories") or []):
        qty = flt(row.get("qty")) or 1.0
        unit_price_eur = flt(row.get("unit_price_eur"))
        row.total_price_eur = flt(unit_price_eur * qty, 2)


def _compute_accessory_extras(doc):
    """
    Return {sa_sn: total_linked_cost_eur} for fan rows that have linked accessories.
    Only accessories with a non-empty linked_fan_sn are counted.
    """
    extras = {}
    for row in (doc.get("sa_accessories") or []):
        sn = (row.get("linked_fan_sn") or "").strip()
        if not sn:
            continue
        cost = flt(row.get("qty")) * flt(row.get("unit_price_eur"))
        extras[sn] = extras.get(sn, 0.0) + cost
    return extras


def _compute_shipping_allocation(doc, name_extras=None):
    """
    Two-pass shipping allocation (Excel COST sheet columns S, AD, AE).

    Pass 1: compute basic_ex_price for every row (including accessory extras).
    Determine total_shipping:
      - Percent of Basic mode: total_basic × sa_shipping_rate / 100
      - Lump Sum mode:         sa_total_shipping_eur (manual override)
    Pass 2: allocate proportionally — shipping_i = basic_i × total_shipping / Σbasic

    Returns dict {row.name: allocated_shipping_eur}.
    """
    name_extras = name_extras or {}
    rows = doc.get("sa_items") or []
    basics = {}
    for row in rows:
        ex = flt(row.get("ex_price"))
        if not ex:
            basics[row.name] = 0.0
            continue
        qty = flt(row.get("qty")) or 1.0
        disc = flt(row.get("supplier_discount"))
        fan_basic = flt(ex * qty * (1.0 - disc / 100.0), 4)
        acc_extra = flt(name_extras.get(row.name, 0.0), 4)
        basics[row.name] = flt(fan_basic + acc_extra, 4)

    total_basic = sum(basics.values())

    shipping_mode = doc.get("sa_shipping_mode") or "Percent of Basic"
    if shipping_mode == "Lump Sum":
        total_shipping = flt(doc.get("sa_total_shipping_eur") or 0.0, 4)
    else:
        rate = flt(doc.get("sa_shipping_rate") or 12.0)
        total_shipping = flt(total_basic * rate / 100.0, 4)

    if not total_basic:
        return {row.name: 0.0 for row in rows}

    return {
        name: flt(basic * total_shipping / total_basic, 4)
        for name, basic in basics.items()
    }


def _compute_all_item_pricing(doc):
    """Run pricing engine on every SA item row that has an EX price."""
    # Build {sa_sn: accessory_extra_eur} for linked accessories
    sn_extras = _compute_accessory_extras(doc)

    # Map sa_sn → row.name so we can look up extras by name in the shipping pass
    sn_to_name = {
        row.sa_sn: row.name
        for row in (doc.get("sa_items") or [])
        if row.get("sa_sn")
    }
    name_extras = {
        sn_to_name[sn]: amt
        for sn, amt in sn_extras.items()
        if sn in sn_to_name
    }

    shipping_map = _compute_shipping_allocation(doc, name_extras)

    errors = []
    for row in (doc.get("sa_items") or []):
        if not flt(row.get("ex_price")):
            continue
        acc_extra = flt(name_extras.get(row.name, 0.0), 4)
        row.accessories_cost_eur = flt(acc_extra, 2)
        try:
            compute_pricing(
                row, doc,
                allocated_shipping=shipping_map.get(row.name, 0.0),
                accessory_extra=acc_extra,
            )
        except frappe.ValidationError as e:
            errors.append(str(e))

    if errors:
        frappe.throw(
            _("Pricing errors:\n") + "\n".join(errors),
            frappe.ValidationError,
        )


def _compute_quotation_totals(doc):
    """
    Compute and set SA summary fields (mirrors Excel COST row-2 mirror block):
    - sa_total_basic_eur    : Σ basic_ex_price (EUR)
    - sa_total_cif_eur      : Σ cif (EUR)
    - sa_total_ddp_eur      : Σ ddp_cost (EUR)
    - sa_grand_total_eur    : Σ total_price_eur + unlinked-accessory totals
    - sa_grand_total_egp_info: grand_total_eur × rate (when rate ≠ 1)
    - sa_effective_margin   : (grand_total - total_ddp) / grand_total × 100
    """
    total_basic_eur = 0.0
    total_cif_eur = 0.0
    total_ddp_eur = 0.0
    grand_total_eur = 0.0

    for row in (doc.get("sa_items") or []):
        total_basic_eur += flt(row.get("basic_ex_price"))
        total_cif_eur   += flt(row.get("cif"))
        total_ddp_eur   += flt(row.get("ddp_cost"))
        grand_total_eur += flt(row.get("total_price_eur"))

    for row in (doc.get("sa_accessories") or []):
        # Linked accessories are already in the fan totals — skip
        if not (row.get("linked_fan_sn") or "").strip():
            grand_total_eur += flt(row.get("total_price_eur"))

    doc.sa_total_basic_eur = flt(total_basic_eur, 2)
    doc.sa_total_cif_eur   = flt(total_cif_eur, 2)
    doc.sa_total_ddp_eur   = flt(total_ddp_eur, 2)
    doc.sa_grand_total_eur = flt(grand_total_eur, 2)

    rate = flt(doc.get("sa_eur_egp_rate") or 1.0, 4)
    doc.sa_grand_total_egp_info = flt(grand_total_eur * rate, 2) if rate != 1.0 else 0.0

    if grand_total_eur > 0:
        doc.sa_effective_margin = flt(
            (grand_total_eur - total_ddp_eur) / grand_total_eur * 100.0, 2
        )
    else:
        doc.sa_effective_margin = 0.0


def _sync_to_standard_items(doc):
    """
    Sync sa_items and sa_accessories into the standard items table so ERPNext validation passes.
    """
    doc.set("items", [])

    for row in (doc.get("sa_items") or []):
        item_code = row.get("item_code")
        if not item_code:
            continue

        doc.append("items", {
            "item_code": item_code,
            "item_name": row.get("item_name") or item_code,
            "qty": flt(row.get("qty")) or 1,
            "rate": flt(row.get("unit_price_eur")),
            "uom": "Nos",
            "conversion_factor": 1.0,
            "ordered_qty": 0,
            "description": row.get("item_name") or item_code,
        })

    for row in (doc.get("sa_accessories") or []):
        item_code = row.get("item_code")
        if not item_code:
            continue

        doc.append("items", {
            "item_code": item_code,
            "item_name": row.get("accessory_name") or item_code,
            "qty": flt(row.get("qty")) or 1,
            "rate": flt(row.get("unit_price_eur")),
            "uom": "Nos",
            "conversion_factor": 1.0,
            "ordered_qty": 0,
            "description": row.get("accessory_name") or item_code,
        })
