import frappe
import unittest
from frappe.utils import flt


class TestSystemAirPriceConfig(unittest.TestCase):

    def setUp(self):
        """Ensure we have a price config to work with."""
        self.config = frappe.get_single("SystemAir Price Config")

    def test_combined_cost_factor_calculation(self):
        """combined_cost_factor must equal CF1 × CF2."""
        self.config.cost_factor_1 = 1.05
        self.config.cost_factor_2 = 1.07
        self.config._compute_combined_cost_factor()
        expected = flt(1.05 * 1.07, 6)
        self.assertAlmostEqual(
            flt(self.config.combined_cost_factor, 6),
            expected,
            places=5,
            msg="Combined cost factor should equal CF1 × CF2",
        )

    def test_default_values(self):
        """Verify shipped defaults are correct."""
        self.assertEqual(flt(self.config.vat_rate), 14.0)
        self.assertEqual(flt(self.config.cost_factor_1), 1.05)
        self.assertEqual(flt(self.config.cost_factor_2), 1.07)
        self.assertAlmostEqual(flt(self.config.combined_cost_factor), 1.1235, places=4)
        self.assertEqual(flt(self.config.default_shipping_rate), 12.0)
        self.assertEqual(flt(self.config.default_margin), 50.0)
        self.assertEqual(flt(self.config.default_currency_rate), 50.0)
        self.assertEqual(flt(self.config.default_customs_rate), 0.0)

    def test_negative_vat_raises(self):
        """Negative VAT rate should raise ValidationError."""
        self.config.vat_rate = -5
        with self.assertRaises(frappe.ValidationError):
            self.config._validate_rates()

    def test_zero_currency_rate_raises(self):
        """Zero EUR/EGP rate should raise ValidationError."""
        self.config.default_currency_rate = 0
        with self.assertRaises(frappe.ValidationError):
            self.config._validate_rates()
