import frappe
from frappe.model.document import Document


class SystemAirQuotationItem(Document):
    # Child table — no standalone logic; pricing is handled by pricing_engine.py
    pass
