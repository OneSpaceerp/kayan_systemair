from . import __version__ as app_version

app_name        = "kayan_systemair"
app_title       = "Kayan SystemAir"
app_publisher   = "Nest Software Development"
app_description = "SystemAir Axial Fan Sales Module"
app_email       = "info@nsd-eg.com"
app_license     = "MIT"
app_version     = app_version

# ── Fixtures ──────────────────────────────────────────────────────────────────
fixtures = [
    "Role",
    "Item Group",
    "Price List",
    "Workflow",
    "Workflow State",
    "Workflow Action",
    {
        "dt": "Custom Field",
        "filters": [["dt", "in", ["Item", "Quotation", "Quotation Item"]]]
    },
    {
        "dt": "Property Setter",
        "filters": [["doc_type", "in", ["Item", "Quotation"]]]
    },
    "SystemAir Price Config",
    "SystemAir Weight Table",
    "Print Format",
]

# ── Document Events ───────────────────────────────────────────────────────────
doc_events = {
    "Quotation": {
        "before_save":  "kayan_systemair.custom.quotation.before_save",
        "on_submit":    "kayan_systemair.custom.quotation.on_submit",
        "on_cancel":    "kayan_systemair.custom.quotation.on_cancel",
    }
}

# ── Scheduled Tasks ───────────────────────────────────────────────────────────
scheduler_events = {
    "weekly": [
        "kayan_systemair.tasks.remind_price_list_update"
    ]
}

# ── App Includes (JS/CSS) ─────────────────────────────────────────────────────
app_include_js  = "/assets/kayan_systemair/js/quotation_extend.js"
app_include_css = "/assets/kayan_systemair/css/kayan_systemair.css"

# ── Override Whitelisted Methods ──────────────────────────────────────────────
override_whitelisted_methods = {}


