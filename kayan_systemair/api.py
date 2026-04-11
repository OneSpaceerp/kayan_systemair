import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_item_prices(item_code):
    """
    Return Germany and Malaysia list prices for the given item_code.

    Returns:
        dict: {"germany": float, "malaysia": float}
    """
    germany_price = _get_price(item_code, "Systemair Germany 2026")
    malaysia_price = _get_price(item_code, "Systemair Malaysia 2026")

    return {
        "germany": flt(germany_price),
        "malaysia": flt(malaysia_price),
    }


def _get_price(item_code, price_list):
    """Fetch price from Item Price — exact match first, then fuzzy."""
    # Exact match on item_code
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "selling": 1},
        "price_list_rate",
    )
    if price:
        return flt(price)

    # Fuzzy fallback: item_name LIKE %item_code%
    results = frappe.db.sql(
        """
        SELECT ip.price_list_rate
        FROM `tabItem Price` ip
        JOIN `tabItem` i ON i.item_code = ip.item_code
        WHERE ip.price_list = %s
          AND ip.selling = 1
          AND i.item_name LIKE %s
        LIMIT 1
        """,
        (price_list, f"%{item_code}%"),
        as_dict=True,
    )
    if results:
        return flt(results[0].price_list_rate)

    return 0.0


@frappe.whitelist()
def check_item_exists(model_code):
    """
    Check if an ERPNext Item with the given model_code exists.

    Returns:
        str | None: item_name if found, else None
    """
    item_name = frappe.db.get_value("Item", {"item_code": model_code}, "name")
    return item_name or None


@frappe.whitelist()
def get_weight_for_diameter(diameter):
    """
    Return weight range for the given nominal diameter from SystemAir Weight Table.

    Args:
        diameter: Nominal diameter in mm (int or str)

    Returns:
        dict: {"min_weight_kg": float, "max_weight_kg": float} or {}
    """
    diameter = int(flt(diameter))
    result = frappe.db.get_value(
        "SystemAir Weight Table",
        {"nominal_diameter": diameter},
        ["min_weight_kg", "max_weight_kg"],
        as_dict=True,
    )
    if result:
        return {
            "min_weight_kg": flt(result.min_weight_kg),
            "max_weight_kg": flt(result.max_weight_kg),
        }
    return {}


@frappe.whitelist()
def get_price_config():
    """
    Return the full SystemAir Price Config singleton as a dict.

    Returns:
        dict: All fields from SystemAir Price Config
    """
    config = frappe.get_single("SystemAir Price Config")
    return {
        "vat_rate": flt(config.vat_rate),
        "cost_factor_1": flt(config.cost_factor_1),
        "cost_factor_2": flt(config.cost_factor_2),
        "combined_cost_factor": flt(config.combined_cost_factor),
        "default_shipping_rate": flt(config.default_shipping_rate),
        "default_margin": flt(config.default_margin),
        "default_currency_rate": flt(config.default_currency_rate),
        "default_customs_rate": flt(config.default_customs_rate),
    }
