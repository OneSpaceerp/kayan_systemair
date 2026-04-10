import frappe
from frappe.model.document import Document
from frappe.utils import flt

class SystemAirPriceConfig(Document):
    def validate(self):
        self.combined_cost_factor = flt(self.cost_factor_1) * flt(self.cost_factor_2)
