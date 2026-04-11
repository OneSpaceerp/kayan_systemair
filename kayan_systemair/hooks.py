app_name = "kayan_systemair"
app_title = "Kayan SystemAir"
app_publisher = "Nest Software Development"
app_description = "SystemAir axial fan quotation and pricing application for Kayan for Import"
app_email = "info@nsd-eg.com"
app_license = "MIT"
app_version = "1.0.0"

# Fixtures exported by bench export-fixtures
fixtures = [
    "Role",
    "Item Group",
    "Price List",
    "Workflow",
    "Workflow State",
    "Workflow Action Master",
    {
        "dt": "Custom Field",
        "filters": [["dt", "in", ["Item", "Quotation"]]],
    },
    {
        "dt": "Property Setter",
        "filters": [["doc_type", "in", ["Item", "Quotation"]]],
    },
    "SystemAir Price Config",
    "SystemAir Weight Table",
    "Print Format",
]

# Document Events
doc_events = {
    "Quotation": {
        "before_save": "kayan_systemair.custom.quotation.before_save",
        "on_submit": "kayan_systemair.custom.quotation.on_submit",
        "on_cancel": "kayan_systemair.custom.quotation.on_cancel",
    }
}

# Scheduled Tasks
scheduler_events = {
    "weekly": [
        "kayan_systemair.tasks.remind_price_list_update",
    ]
}

# Global JS/CSS included on every desk page
app_include_js = "/assets/kayan_systemair/js/quotation_extend.js"
app_include_css = "/assets/kayan_systemair/css/kayan_systemair.css"

# Boot session
boot_session = "kayan_systemair.startup.boot_session"

# Override standard DocType classes
# override_doctype_class = {}

# DocType Class Override
# override_doctype_class = {
#     "Quotation": "kayan_systemair.custom.quotation.CustomQuotation"
# }

# Whitelisted Methods
# These are exposed as REST endpoints via frappe.call()
# No need to list here — use @frappe.whitelist() decorator in api.py

# After migrate
# after_migrate = ["kayan_systemair.setup.after_migrate"]

# Website
# website_generators = ["Web Page"]
