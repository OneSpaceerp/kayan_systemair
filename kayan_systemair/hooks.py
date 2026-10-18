app_name = "kayan_systemair"
app_title = "Kayan SystemAir"
app_publisher = "nsdLabs - Nest Software Development"
app_description = "SystemAir axial fan quotation and pricing application for Kayan for Import"
app_email = "info@nsd-eg.com"
app_license = "MIT"
app_version = "1.0.0"
app_logo_url = "/assets/kayan_systemair/images/app_icon.png"

# Frappe v16 desktop screen.
#
# v16 replaced the old navigation: the desk moved from /app to /desk, the /apps
# page is deprecated, and a desktop screen now renders a tile per app plus icons
# for every public workspace. That autogeneration only picks up a custom app if
# this hook is present, so without it the app has no tile at all.
#
# `route` is passed through literally -- it is neither resolved nor permission
# checked -- so it must track the workspace's actual desk route.
add_to_apps_screen = [
    {
        "name": "kayan_systemair",
        "title": "Kayan SystemAir",
        "logo": "/assets/kayan_systemair/images/app_icon.png",
        "route": "/desk/systemair",
        "has_permission": "kayan_systemair.api.has_app_permission",
    }
]

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
        # search_fields is applied post-install by setup.py and must never be
        # exported: as a fixture it imports before its fields exist, and Frappe
        # re-validates search_fields on every Custom Field insert, which aborts
        # the whole fixture import.
        "filters": [
            ["doc_type", "in", ["Item", "Quotation"]],
            ["property", "!=", "search_fields"],
        ],
    },
    "SystemAir Price Config",
    "SystemAir Smoke Rating",
    "SystemAir Weight Table",
    "Print Format",
]

# Document Events
doc_events = {
    "Quotation": {
        # before_validate fires before AccountsController.validate() so we can
        # pre-seed conversion_rate and suppress ERPNext's Currency Exchange lookup.
        "before_validate": "kayan_systemair.custom.quotation.before_validate",
        # validate fires before _validate_mandatory() in both insert and update paths,
        # ensuring _sync_to_standard_items runs before ERPNext's mandatory field check.
        "validate": "kayan_systemair.custom.quotation.before_save",
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

override_doctype_class = {
    "Quotation": "kayan_systemair.custom.quotation.CustomQuotation"
}

# Whitelisted Methods
# These are exposed as REST endpoints via frappe.call()
# No need to list here — use @frappe.whitelist() decorator in api.py

# After install / migrate — restore standard ERPNext workspaces
before_install = "kayan_systemair.setup.before_install"
before_migrate = "kayan_systemair.setup.before_migrate"
after_install = "kayan_systemair.setup.after_install"
after_migrate = "kayan_systemair.setup.after_migrate"

# Website
# website_generators = ["Web Page"]
