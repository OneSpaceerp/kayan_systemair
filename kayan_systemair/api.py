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
def get_article_details(article_no):
    """
    Look up Item(s) by SA article number and return pricing + metadata.

    Returns:
        None                           — article_no not found
        dict                           — exactly one match (normal case)
        {"multiple": True, "items": []}— multiple models share this article_no;
                                         client must show a selection dialog
    """
    if not article_no:
        return None

    matches = frappe.db.get_all(
        "Item",
        filters={"sa_article_no": article_no},
        fields=["item_code"],
    )
    if not matches:
        return None

    if len(matches) > 1:
        items = []
        for m in matches:
            ic = m["item_code"]
            it = frappe.get_cached_doc("Item", ic)
            germany = _get_price(ic, "Systemair Germany 2026")
            malaysia = _get_price(ic, "Systemair Malaysia 2026")
            items.append({
                "item_code": ic,
                "item_name": it.item_name,
                "germany_list_price": flt(germany),
                "malaysia_list_price": flt(malaysia),
                "item_group": it.item_group,
                "product_family": getattr(it, "sa_product_family", "") or "",
                "type_of_fan": getattr(it, "sa_type_of_fan", "") or "",
                "primary_factory": getattr(it, "sa_primary_factory", "") or "",
                "temperature_rate": getattr(it, "sa_temperature_rate", "") or "",
                "weight_kg": flt(getattr(it, "sa_weight_kg", 0)),
            })
        return {"multiple": True, "items": items}

    item_code = matches[0]["item_code"]
    item = frappe.get_cached_doc("Item", item_code)
    germany = _get_price(item_code, "Systemair Germany 2026")
    malaysia = _get_price(item_code, "Systemair Malaysia 2026")

    return {
        "item_code": item_code,
        "item_name": item.item_name,
        "germany_list_price": flt(germany),
        "malaysia_list_price": flt(malaysia),
        "item_group": item.item_group,
        "product_family": getattr(item, "sa_product_family", "") or "",
        "type_of_fan": getattr(item, "sa_type_of_fan", "") or "",
        "primary_factory": getattr(item, "sa_primary_factory", "") or "",
        "temperature_rate": getattr(item, "sa_temperature_rate", "") or "",
        "weight_kg": flt(getattr(item, "sa_weight_kg", 0)),
    }


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
