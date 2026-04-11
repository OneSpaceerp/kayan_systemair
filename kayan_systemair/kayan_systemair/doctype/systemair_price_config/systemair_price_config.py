import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SystemAirPriceConfig(Document):
    # pylint: disable=no-member

    def validate(self):
        """Auto-calculate combined cost factor and validate values."""
        self._compute_combined_cost_factor()
        self._validate_rates()

    def _compute_combined_cost_factor(self):
        """combined_cost_factor = cost_factor_1 × cost_factor_2"""
        cf1 = flt(self.cost_factor_1, 6)
        cf2 = flt(self.cost_factor_2, 6)
        if cf1 and cf2:
            self.combined_cost_factor = flt(cf1 * cf2, 6)
        else:
            self.combined_cost_factor = 0.0

    def _validate_rates(self):
        """Ensure rates are positive and within sensible ranges."""
        if flt(self.vat_rate) < 0:
            frappe.throw(frappe._("VAT Rate cannot be negative."))
        if flt(self.cost_factor_1) <= 0:
            frappe.throw(frappe._("Cost Factor 1 must be greater than zero."))
        if flt(self.cost_factor_2) <= 0:
            frappe.throw(frappe._("Cost Factor 2 must be greater than zero."))
        if flt(self.default_currency_rate) <= 0:
            frappe.throw(frappe._("Default EUR→EGP Rate must be greater than zero."))
        if flt(self.default_shipping_rate) < 0:
            frappe.throw(frappe._("Default Shipping Rate cannot be negative."))
        if flt(self.default_margin) < 0:
            frappe.throw(frappe._("Default Margin cannot be negative."))
