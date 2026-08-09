import frappe


# Standard ERPNext workspaces that must remain visible after installing this app.
_STANDARD_WORKSPACES = [
    "Home",
    "Selling",
    "Buying",
    "Accounting",
    "CRM",
    "Purchase",
    "Stock",
    "Manufacturing",
    "HR",
    "Payroll",
    "Projects",
    "Assets",
    "Support",
    "Settings",
    "Integrations",
    "Build",
]


def after_install():
    _restore_standard_workspaces()


def after_migrate():
    _restore_standard_workspaces()


def _restore_standard_workspaces():
    """
    Frappe v16's workspace sync can set is_hidden=1 on standard ERPNext
    workspaces when a new app with a role-restricted workspace is installed.
    This ensures they remain visible after every migrate.
    """
    for ws_name in _STANDARD_WORKSPACES:
        if frappe.db.exists("Workspace", ws_name):
            frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)
    frappe.db.commit()
