import frappe
from frappe.model.document import Document
from frappe.utils import flt

class SystemAirFanItem(Document):

    def validate(self):
        self.model_code = self._assemble_model_code()
        self._check_item_exists()
        self._fetch_prices()
        self._fetch_weight()

    def on_submit(self):
        if not self.item_exists:
            pass # created client side

    # ── Private helpers ────────────────────────────────────────────────────

    def _assemble_model_code(self):
        code = f"{self.fan_model} {self.nominal_diameter}"
        code += f"-{self.num_blades}/{self.blade_angle}\u00b0"
        code += f"-{self.num_poles}"
        if self.smoke_rating and self.smoke_rating != "None":
            code += f"({self.smoke_rating})"
        if self.guide_vane:
            code += "-PV"
        if self.medium_casing:
            code += " MC"
        if self.config_suffix and self.config_suffix != "None":
            code += self.config_suffix
        if self.reversible:
            code += "-TR"
        return code

    def _check_item_exists(self):
        existing = frappe.db.get_value("Item", {"item_code": self.model_code}, "name")
        self.item_exists = 1 if existing else 0
        self.erp_item = existing or None

    def _fetch_prices(self):
        # We need to import locally to avoid circular dependencies if they arise
        from kayan_systemair.api import get_item_prices
        prices = get_item_prices(self.model_code)
        self.germany_price  = prices.get("germany") or 0
        self.malaysia_price = prices.get("malaysia") or 0

    def _fetch_weight(self):
        from kayan_systemair.api import get_weight_for_diameter
        weight = get_weight_for_diameter(self.nominal_diameter)
        if weight and weight.get("max_weight_kg"):
            self.approx_weight = flt(weight.get("max_weight_kg"))

@frappe.whitelist()
def create_item_from_doc(docname):
    doc = frappe.get_doc("SystemAir Fan Item", docname)

    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": doc.model_code,
        "item_name": doc.model_code,
        "item_group": "SystemAir Axial Fans",
        "stock_uom": "Nos",
        "is_purchase_item": 1,
        "is_sales_item": 1,
        "is_stock_item": 0,
        "sa_nominal_diameter": str(doc.nominal_diameter),
        "sa_num_blades": doc.num_blades,
        "sa_blade_angle": doc.blade_angle,
        "sa_num_poles": str(doc.num_poles),
        "sa_smoke_rating": doc.smoke_rating,
        "sa_weight_kg": doc.approx_weight,
        "sa_product_family": doc.product_group,
        "sa_primary_factory": doc.primary_factory,
    })
    item.insert(ignore_permissions=True)
    doc.erp_item = item.name
    doc.item_exists = 1
    doc.save(ignore_permissions=True)
    
    frappe.msgprint(
        f"Item <b>{doc.model_code}</b> created successfully in ERPNext.",
        alert=True, indicator="green"
    )
    return item.name
