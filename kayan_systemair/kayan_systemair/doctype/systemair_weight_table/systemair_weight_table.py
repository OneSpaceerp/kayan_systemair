import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SystemAirWeightTable(Document):
    # pylint: disable=no-member

    def validate(self):
        """Validate weight table entry."""
        if flt(self.min_weight_kg) < 0:
            frappe.throw(frappe._("Min Weight cannot be negative."))
        if flt(self.max_weight_kg) < 0:
            frappe.throw(frappe._("Max Weight cannot be negative."))
        if flt(self.max_weight_kg) < flt(self.min_weight_kg):
            frappe.throw(
                frappe._("Max Weight must be greater than or equal to Min Weight.")
            )
        if int(self.nominal_diameter) <= 0:
            frappe.throw(frappe._("Nominal Diameter must be a positive integer."))
