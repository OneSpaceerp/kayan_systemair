import glob
import os

import frappe


# Standard ERPNext workspaces that must stay visible.
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
    _resync_erpnext_workspaces()
    _restore_standard_workspaces()


def after_migrate():
    # Frappe v16 "Removing orphan Workspaces" runs BEFORE after_migrate hooks.
    # It deletes standard ERPNext workspace records whose JSON files it fails to
    # match. Re-syncing ERPNext workspace files here restores any that were removed.
    _resync_erpnext_workspaces()
    _restore_standard_workspaces()


def _resync_erpnext_workspaces():
    try:
        from frappe.modules.import_file import import_file_by_path

        erpnext_path = frappe.get_app_path("erpnext")
        pattern = os.path.join(erpnext_path, "*", "workspace", "*", "*.json")
        for ws_file in glob.glob(pattern):
            try:
                import_file_by_path(ws_file, force=True, ignore_version=True)
            except Exception:
                pass
        frappe.db.commit()
    except Exception:
        pass


def _restore_standard_workspaces():
    changed = False
    for ws_name in _STANDARD_WORKSPACES:
        if frappe.db.exists("Workspace", ws_name):
            if frappe.db.get_value("Workspace", ws_name, "is_hidden"):
                frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)
                changed = True
    if changed:
        frappe.db.commit()
