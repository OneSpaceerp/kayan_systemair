import frappe
from frappe import _
from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import get_list_price

@frappe.whitelist()
def get_item_prices(item_code):
    """Returns Germany and Malaysia list prices for a given item code."""
    return {
        "germany":  get_list_price(item_code, "Systemair Germany 2026"),
        "malaysia": get_list_price(item_code, "Systemair Malaysia 2026"),
    }

@frappe.whitelist()
def check_item_exists(model_code):
    """Returns item name if exists, else None."""
    return frappe.db.get_value("Item", {"item_code": model_code}, "name")

@frappe.whitelist()
def get_weight_for_diameter(diameter):
    """Returns max weight for a given nominal diameter."""
    return frappe.db.get_value(
        "SystemAir Weight Table",
        {"nominal_diameter": int(diameter)},
        ["min_weight_kg", "max_weight_kg"],
        as_dict=True
    )

@frappe.whitelist()
def get_price_config():
    """Returns current SystemAir Price Config values."""
    return frappe.get_single("SystemAir Price Config").as_dict()
