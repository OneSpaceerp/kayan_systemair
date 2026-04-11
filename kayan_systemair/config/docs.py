from frappe import _


def get_data():
    return {
        "title": _("Kayan SystemAir"),
        "description": _("SystemAir axial fan quotation and pricing application"),
        "author": "Nest Software Development",
        "metatags": {
            "description": "Custom ERPNext application for SystemAir axial fan quotations",
        },
        "get_tree_titles": {"module": ["kayan_systemair"]},
    }
