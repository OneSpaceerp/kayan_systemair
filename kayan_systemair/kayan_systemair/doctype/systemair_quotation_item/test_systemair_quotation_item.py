import frappe
import unittest
from kayan_systemair.doctype.systemair_quotation_item.pricing_engine import compute_pricing

class TestPricingEngine(unittest.TestCase):

    def setUp(self):
        # Ensure Price Config has known values
        cfg = frappe.get_single("SystemAir Price Config")
        cfg.vat_rate = 14
        cfg.cost_factor_1 = 1.05
        cfg.cost_factor_2 = 1.07
        cfg.default_shipping_rate = 12
        cfg.save()

    def test_standard_fan_50pct_margin(self):
        """Test Case 1: Standard fan, 0% customs, 50% margin."""
        item = frappe._dict(
            ex_price=1000, qty=2, supplier_discount=20,
            additional_discount=0, customs_rate=0, margin_percent=50
        )
        quotation = frappe._dict(sa_eur_egp_rate=50, sa_shipping_rate=12)
        compute_pricing(item, quotation)

        self.assertAlmostEqual(item.basic_ex_price, 1600.0,  places=2)  # 1000\u00d72\u00d70.8
        self.assertAlmostEqual(item.shipping_cost,  192.0,   places=2)  # 1600\u00d70.12
        self.assertAlmostEqual(item.cif,            1792.0,  places=2)  # 1600 + 192
        # total = 1792 \u00d7 1.1235 \u00d7 1.5 \u00d7 50 \u00d7 1.14 \u00d7 1.0
        expected_total = 1792 * 1.1235 * 1.5 * 50 * 1.14 * 1.0
        self.assertAlmostEqual(item.total_price_egp, expected_total, places=2)
        self.assertAlmostEqual(item.unit_price_egp, expected_total / 2, places=2)

    def test_smoke_rated_fan_10pct_customs(self):
        """Test Case 2: Smoke-rated (B), 10% customs, 40% margin."""
        item = frappe._dict(
            ex_price=2500, qty=1, supplier_discount=15,
            additional_discount=5, customs_rate=10, margin_percent=40
        )
        quotation = frappe._dict(sa_eur_egp_rate=55, sa_shipping_rate=12)
        compute_pricing(item, quotation)
        self.assertGreater(item.total_price_egp, 0)
        self.assertAlmostEqual(item.unit_price_egp, item.total_price_egp, places=2)

    def test_zero_ex_price_raises_error(self):
        """Test Case 3: Zero EX Price must raise validation error."""
        item = frappe._dict(
            ex_price=0, qty=1, supplier_discount=0,
            additional_discount=0, customs_rate=0, margin_percent=50,
            item_code="TEST-001", idx=1
        )
        quotation = frappe._dict(sa_eur_egp_rate=50, sa_shipping_rate=12)
        with self.assertRaises(frappe.exceptions.ValidationError):
            compute_pricing(item, quotation)

    def test_excel_parity(self):
        """
        Test Case 6: Excel parity.
        Known inputs from 000-Pricing Sheet 2026.xlsx with known outputs.
        EX Price = 500 EUR, Qty = 1, Discount = 0%, Shipping = 12%,
        CF = 1.1235, VAT = 1.14, Rate = 50, MG = 50%, Customs = 0%
        Expected Total = 500 \u00d7 1.12 \u00d7 1.1235 \u00d7 1.5 \u00d7 50 \u00d7 1.14 \u00d7 1.0
        """
        item = frappe._dict(
            ex_price=500, qty=1, supplier_discount=0,
            additional_discount=0, customs_rate=0, margin_percent=50
        )
        quotation = frappe._dict(sa_eur_egp_rate=50, sa_shipping_rate=12)
        compute_pricing(item, quotation)

        # CIF = 500 + (500 \u00d7 0.12) = 560
        self.assertAlmostEqual(item.cif, 560.0, places=4)
        # Total = 560 \u00d7 1.1235 \u00d7 1.5 \u00d7 50 \u00d7 1.14
        expected = 560 * 1.1235 * 1.5 * 50 * 1.14
        self.assertAlmostEqual(item.total_price_egp, expected, places=2)
