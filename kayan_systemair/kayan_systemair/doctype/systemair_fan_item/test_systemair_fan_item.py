import frappe
import unittest
from kayan_systemair.kayan_systemair.doctype.systemair_fan_item.systemair_fan_item import (
    assemble_model_code,
)


class MockFanItem:
    """Lightweight mock for testing assemble_model_code without DB."""
    def __init__(self, **kwargs):
        defaults = {
            "fan_model": "AXC",
            "nominal_diameter": "355",
            "num_blades": 6,
            "blade_angle": "10",
            "num_poles": "2",
            "smoke_rating": "None",
            "guide_vane": 0,
            "plus_impeller": 0,
            "medium_casing": 0,
            "reversible": 0,
            "config_suffix": "None",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestSystemAirFanItem(unittest.TestCase):

    def test_basic_model_code(self):
        """Basic type-key assembly without any suffixes."""
        doc = MockFanItem()
        code = assemble_model_code(doc)
        self.assertEqual(code, "AXC 355-6/10\u00b0-2")

    def test_smoke_rating_b(self):
        """Smoke rating B appended in parentheses."""
        doc = MockFanItem(smoke_rating="B")
        code = assemble_model_code(doc)
        self.assertEqual(code, "AXC 355-6/10\u00b0-2(B)")

    def test_smoke_rating_none_omitted(self):
        """Smoke rating 'None' must not appear in code."""
        doc = MockFanItem(smoke_rating="None")
        code = assemble_model_code(doc)
        self.assertNotIn("(None)", code)
        self.assertNotIn("None", code)

    def test_guide_vane_suffix(self):
        """Guide vane appends -PV."""
        doc = MockFanItem(guide_vane=1)
        code = assemble_model_code(doc)
        self.assertIn("-PV", code)

    def test_medium_casing_suffix(self):
        """Medium casing appends MC (with space)."""
        doc = MockFanItem(medium_casing=1)
        code = assemble_model_code(doc)
        self.assertIn(" MC", code)

    def test_reversible_suffix(self):
        """Reversible appends -TR."""
        doc = MockFanItem(reversible=1)
        code = assemble_model_code(doc)
        self.assertIn("-TR", code)

    def test_full_example_from_prd(self):
        """Full example: AXC 355-6/10°-2(B)-PV MC"""
        doc = MockFanItem(
            fan_model="AXC",
            nominal_diameter="355",
            num_blades=6,
            blade_angle="10",
            num_poles="2",
            smoke_rating="B",
            guide_vane=1,
            medium_casing=1,
            reversible=0,
            config_suffix="None",
        )
        code = assemble_model_code(doc)
        self.assertEqual(code, "AXC 355-6/10\u00b0-2(B)-PV MC")

    def test_config_suffix_g(self):
        """-G config suffix is appended."""
        doc = MockFanItem(config_suffix="-G")
        code = assemble_model_code(doc)
        self.assertIn("-G", code)

    def test_config_suffix_none_omitted(self):
        """Config suffix 'None' must not appear in code."""
        doc = MockFanItem(config_suffix="None")
        code = assemble_model_code(doc)
        self.assertNotIn("None", code)
