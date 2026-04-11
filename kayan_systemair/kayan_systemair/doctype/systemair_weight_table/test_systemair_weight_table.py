import frappe
import unittest
from frappe.utils import flt


class TestSystemAirWeightTable(unittest.TestCase):

    def test_all_15_records_exist(self):
        """Verify all 15 weight table records are present after install."""
        expected_diameters = [315, 355, 400, 450, 500, 560, 630, 710,
                               800, 900, 1000, 1120, 1250, 1400, 1600]
        for diam in expected_diameters:
            record = frappe.db.get_value(
                "SystemAir Weight Table",
                {"nominal_diameter": diam},
                ["nominal_diameter", "min_weight_kg", "max_weight_kg"],
                as_dict=True,
            )
            self.assertIsNotNone(
                record, f"Weight table record missing for diameter {diam}mm"
            )
            self.assertGreater(
                flt(record.min_weight_kg), 0,
                f"Min weight must be > 0 for diameter {diam}mm"
            )
            self.assertGreaterEqual(
                flt(record.max_weight_kg), flt(record.min_weight_kg),
                f"Max weight must be >= min weight for diameter {diam}mm"
            )

    def test_validation_max_less_than_min_raises(self):
        """Max weight < min weight should raise ValidationError."""
        doc = frappe.get_doc({
            "doctype": "SystemAir Weight Table",
            "nominal_diameter": 9999,
            "min_weight_kg": 100.0,
            "max_weight_kg": 50.0,
        })
        with self.assertRaises(frappe.ValidationError):
            doc.validate()
