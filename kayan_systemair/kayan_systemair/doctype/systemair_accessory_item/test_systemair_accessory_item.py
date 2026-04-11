import frappe
import unittest


class TestSystemAirAccessoryItem(unittest.TestCase):

    def test_child_table_structure(self):
        """Verify all expected fields exist on SystemAir Accessory Item."""
        meta = frappe.get_meta("SystemAir Accessory Item")
        expected_fields = [
            "sa_article_no", "item_code", "accessory_name",
            "qty", "unit_price_eur", "total_price_egp",
        ]
        field_names = [f.fieldname for f in meta.fields]
        for fn in expected_fields:
            self.assertIn(fn, field_names, f"Missing field: {fn}")

    def test_is_child_table(self):
        """SystemAir Accessory Item must be flagged as a child table (istable=1)."""
        meta = frappe.get_meta("SystemAir Accessory Item")
        self.assertTrue(meta.istable, "SystemAir Accessory Item should be a child table")
