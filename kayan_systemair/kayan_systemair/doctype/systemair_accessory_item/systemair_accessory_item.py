import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SystemAirAccessoryItem(Document):
    # Child table — total_price_egp is computed by the parent Quotation hook
    pass
