"""
Pricing Engine Test Suite
=========================
Tests the 16-step formula chain against the three validation cases
specified in the PRD.  These tests run without a live DB by using
mock objects and patching frappe.get_cached_doc.
"""

import unittest
from unittest.mock import MagicMock, patch
from frappe.utils import flt


class MockConfig:
    """Mocks SystemAir Price Config with PRD defaults."""
    vat_rate = 14.0
    cost_factor_1 = 1.05
    cost_factor_2 = 1.07
    combined_cost_factor = 1.1235
    default_shipping_rate = 12.0
    default_margin = 50.0
    default_currency_rate = 50.0
    default_customs_rate = 0.0


class MockItemRow:
    """Mocks a single SystemAir Quotation Item child row."""
    def __init__(self, **kwargs):
        defaults = {
            "idx": 1,
            "ex_price": 1000.0,
            "supplier_discount": 0.0,
            "additional_discount": 0.0,
            "qty": 1.0,
            "customs_rate": 0.0,
            "margin_percent": 50.0,
            "shipping_rate": None,
            # Output fields — will be written by engine
            "basic_ex_price": 0.0,
            "shipping_cost": 0.0,
            "final_ex_price": 0.0,
            "cif": 0.0,
            "ddp_cost": 0.0,
            "unit_price_egp": 0.0,
            "total_price_egp": 0.0,
            "rate": 0.0,
            "amount": 0.0,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)

    def get(self, key, default=None):
        return getattr(self, key, default)


class MockQuotation:
    """Mocks the parent Quotation document."""
    def __init__(self, eur_egp_rate=50.0, shipping_rate=12.0):
        self.sa_eur_egp_rate = eur_egp_rate
        self.sa_shipping_rate = shipping_rate

    def get(self, key, default=None):
        return getattr(self, key, default)


class TestPricingEngine(unittest.TestCase):

    def _run(self, item_kwargs, quotation_kwargs=None):
        """Helper: patch frappe.get_cached_doc and run compute_pricing."""
        from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import (
            compute_pricing,
        )
        q_kwargs = {"eur_egp_rate": 50.0, "shipping_rate": 12.0}
        if quotation_kwargs:
            q_kwargs.update(quotation_kwargs)

        item_row = MockItemRow(**item_kwargs)
        quotation_doc = MockQuotation(**q_kwargs)

        with patch("frappe.get_cached_doc", return_value=MockConfig()):
            result = compute_pricing(item_row, quotation_doc)

        return item_row, result

    # ------------------------------------------------------------------
    # Test 1 — Standard fan, 0% customs, 50% margin
    # ------------------------------------------------------------------
    def test_1_basic_ex_price(self):
        """Test 1: basic_ex_price = ex_price × qty × (1 − supplier_discount/100)"""
        # ex_price=1000, qty=2, supplier_discount=20
        # basic = 1000 × 2 × (1 - 0.20) = 1600.0
        item_row, _ = self._run(
            {"ex_price": 1000.0, "qty": 2.0, "supplier_discount": 20.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        self.assertAlmostEqual(item_row.basic_ex_price, 1600.0, places=2)

    def test_1_shipping_cost(self):
        """Test 1: shipping_cost = basic_ex_price × 12% = 1600 × 0.12 = 192.0"""
        item_row, _ = self._run(
            {"ex_price": 1000.0, "qty": 2.0, "supplier_discount": 20.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        self.assertAlmostEqual(item_row.shipping_cost, 192.0, places=2)

    def test_1_cif(self):
        """Test 1: cif = final_ex_price + shipping_cost = 1600 + 192 = 1792.0"""
        item_row, _ = self._run(
            {"ex_price": 1000.0, "qty": 2.0, "supplier_discount": 20.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        self.assertAlmostEqual(item_row.cif, 1792.0, places=2)

    def test_1_total_price_egp(self):
        """Test 1: total_price_egp = 1792 × 1.1235 × 1.5 × 50 × 1.14 × 1.0"""
        item_row, _ = self._run(
            {"ex_price": 1000.0, "qty": 2.0, "supplier_discount": 20.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        expected = flt(1792.0 * 1.1235 * 1.5 * 50.0 * 1.14 * 1.0, 2)
        self.assertAlmostEqual(item_row.total_price_egp, expected, places=0)

    # ------------------------------------------------------------------
    # Test 2 — Excel parity: ex_price=500, qty=1, no discounts
    # ------------------------------------------------------------------
    def test_2_cif(self):
        """Test 2: cif = 560.0 (500 + 60 shipping on 500×1×1.0)"""
        item_row, _ = self._run(
            {"ex_price": 500.0, "qty": 1.0, "supplier_discount": 0.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        self.assertAlmostEqual(item_row.cif, 560.0, places=2)

    def test_2_total_price_egp(self):
        """Test 2: total_price_egp = 560 × 1.1235 × 1.5 × 50 × 1.14"""
        item_row, _ = self._run(
            {"ex_price": 500.0, "qty": 1.0, "supplier_discount": 0.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        expected = flt(560.0 * 1.1235 * 1.5 * 50.0 * 1.14, 2)
        self.assertAlmostEqual(item_row.total_price_egp, expected, places=0)

    def test_2_unit_price_equals_total_when_qty_1(self):
        """Test 2: unit_price_egp == total_price_egp when qty=1"""
        item_row, _ = self._run(
            {"ex_price": 500.0, "qty": 1.0, "supplier_discount": 0.0,
             "additional_discount": 0.0, "customs_rate": 0.0, "margin_percent": 50.0}
        )
        self.assertAlmostEqual(item_row.unit_price_egp, item_row.total_price_egp, places=2)

    # ------------------------------------------------------------------
    # Test 3 — Zero EX price must raise frappe.ValidationError
    # ------------------------------------------------------------------
    def test_3_zero_ex_price_raises(self):
        """Test 3: ex_price=0 must raise frappe.ValidationError."""
        import frappe as _frappe
        from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import (
            compute_pricing,
        )
        item_row = MockItemRow(ex_price=0.0, qty=1.0)
        quotation_doc = MockQuotation()

        with patch("frappe.get_cached_doc", return_value=MockConfig()):
            with self.assertRaises(_frappe.ValidationError):
                compute_pricing(item_row, quotation_doc)

    def test_3_negative_ex_price_raises(self):
        """Negative EX price must also raise frappe.ValidationError."""
        import frappe as _frappe
        from kayan_systemair.kayan_systemair.doctype.systemair_quotation_item.pricing_engine import (
            compute_pricing,
        )
        item_row = MockItemRow(ex_price=-100.0, qty=1.0)
        quotation_doc = MockQuotation()

        with patch("frappe.get_cached_doc", return_value=MockConfig()):
            with self.assertRaises(_frappe.ValidationError):
                compute_pricing(item_row, quotation_doc)

    # ------------------------------------------------------------------
    # Additional edge-case tests
    # ------------------------------------------------------------------
    def test_rate_equals_unit_price(self):
        """rate field must equal unit_price_egp."""
        item_row, _ = self._run({"ex_price": 800.0, "qty": 3.0, "margin_percent": 40.0})
        self.assertEqual(item_row.rate, item_row.unit_price_egp)

    def test_amount_equals_total_price(self):
        """amount field must equal total_price_egp."""
        item_row, _ = self._run({"ex_price": 800.0, "qty": 3.0, "margin_percent": 40.0})
        self.assertEqual(item_row.amount, item_row.total_price_egp)

    def test_customs_increases_total(self):
        """Adding customs duty must increase ddp_cost and total_price_egp."""
        item_no_customs, _ = self._run({"ex_price": 600.0, "qty": 1.0, "customs_rate": 0.0})
        item_with_customs, _ = self._run({"ex_price": 600.0, "qty": 1.0, "customs_rate": 10.0})
        self.assertGreater(item_with_customs.total_price_egp, item_no_customs.total_price_egp)
        self.assertGreater(item_with_customs.ddp_cost, item_no_customs.ddp_cost)

    def test_higher_margin_increases_total(self):
        """Higher margin must increase total_price_egp but not ddp_cost."""
        item_low, _ = self._run({"ex_price": 700.0, "qty": 1.0, "margin_percent": 30.0})
        item_high, _ = self._run({"ex_price": 700.0, "qty": 1.0, "margin_percent": 60.0})
        self.assertGreater(item_high.total_price_egp, item_low.total_price_egp)
        # DDP cost is independent of margin
        self.assertAlmostEqual(item_high.ddp_cost, item_low.ddp_cost, places=2)
