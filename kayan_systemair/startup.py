import frappe
from frappe.utils import flt


def boot_session(bootinfo):
    """
    Add SystemAir Price Config defaults to the boot session so
    the client can access them without an extra API call.
    """
    try:
        config = frappe.get_single("SystemAir Price Config")
        bootinfo.systemair_config = {
            "vat_rate": flt(config.vat_rate),
            "cost_factor_1": flt(config.cost_factor_1),
            "cost_factor_2": flt(config.cost_factor_2),
            "combined_cost_factor": flt(config.combined_cost_factor),
            "default_shipping_rate": flt(config.default_shipping_rate),
            "default_margin": flt(config.default_margin),
            "default_currency_rate": flt(config.default_currency_rate),
            "default_customs_rate": flt(config.default_customs_rate),
        }
    except Exception:
        bootinfo.systemair_config = {}
