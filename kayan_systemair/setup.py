import glob
import json
import os

import frappe


def before_migrate():
    _backup_all_workspaces()


def after_install():
    _resync_erpnext_workspaces()
    _fix_sa_mandatory_fields()


def after_migrate():
    # Frappe v16 "Removing orphan Workspaces" runs BEFORE after_migrate hooks.
    # Restore anything it deleted, then re-sync the ERPNext workspace files.
    _restore_deleted_workspaces()
    _resync_erpnext_workspaces()
    _fix_sa_mandatory_fields()


# ---------------------------------------------------------------------------
# Backup / restore (handles setup-wizard workspaces that have no JSON file)
# ---------------------------------------------------------------------------

def _backup_path():
    return os.path.join(frappe.get_site_path(), ".kayan_ws_backup.json")


def _backup_all_workspaces():
    """
    Dump every public workspace doc to disk before migration runs its orphan
    removal.  Called by the before_migrate hook.
    """
    try:
        names = frappe.db.get_all("Workspace", filters={"for_user": ""}, pluck="name")
        data = []
        for name in names:
            try:
                data.append(frappe.get_doc("Workspace", name).as_dict())
            except Exception:
                pass
        with open(_backup_path(), "w", encoding="utf-8") as fh:
            fh.write(frappe.as_json(data))
    except Exception:
        pass


def _restore_deleted_workspaces():
    """
    After orphan removal, re-insert any workspace that was deleted.
    Called by the after_migrate hook.
    """
    path = _backup_path()
    try:
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as fh:
            backed_up = frappe.parse_json(fh.read())
        for ws_data in backed_up:
            name = ws_data.get("name")
            if not name or frappe.db.exists("Workspace", name):
                continue
            try:
                doc = frappe.get_doc(ws_data)
                doc.flags.ignore_permissions = True
                doc.flags.ignore_links = True
                doc.flags.ignore_validate = True
                doc.flags.ignore_mandatory = True
                doc.insert()
            except Exception:
                pass
        frappe.db.commit()
    except Exception:
        pass
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Re-sync ERPNext workspace JSON files (covers JSON-backed workspaces)
# ---------------------------------------------------------------------------

def _resync_erpnext_workspaces():
    """
    Import ERPNext workspace JSON files so workspaces that DO have app files
    are restored even on a fresh site where no backup exists yet.
    """
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


# ---------------------------------------------------------------------------
# Conditional mandatory: SA quotations must not be blocked by standard
# Quotation / Quotation Item mandatory custom fields.
# ---------------------------------------------------------------------------

def _fix_sa_mandatory_fields():
    """
    For every mandatory Custom Field on Quotation (or Quotation Item) that is
    NOT one of our SA fields, add mandatory_depends_on so the field is only
    required when is_systemair_quotation is NOT set.

    Frappe evaluates mandatory_depends_on both client-side (JS) and server-side
    (_validate_mandatory), so this fixes the "Missing Fields" dialog permanently
    without any JS hacks.
    """
    try:
        changed = False

        # Quotation parent fields
        qtn_fields = frappe.db.get_all(
            "Custom Field",
            filters={"dt": "Quotation", "reqd": 1},
            fields=["name", "fieldname", "mandatory_depends_on"],
        )
        for cf in qtn_fields:
            fn = cf.fieldname or ""
            if fn.startswith("sa_") or fn == "is_systemair_quotation":
                continue
            target = "eval:!doc.is_systemair_quotation"
            if cf.mandatory_depends_on == target:
                continue
            frappe.db.set_value(
                "Custom Field", cf.name, "mandatory_depends_on", target,
                update_modified=False,
            )
            changed = True

        # Quotation Item child-table fields
        item_fields = frappe.db.get_all(
            "Custom Field",
            filters={"dt": "Quotation Item", "reqd": 1},
            fields=["name", "fieldname", "mandatory_depends_on"],
        )
        for cf in item_fields:
            fn = cf.fieldname or ""
            if fn.startswith("sa_") or fn == "is_systemair_quotation":
                continue
            target = "eval:parent_doc && !parent_doc.is_systemair_quotation"
            if cf.mandatory_depends_on == target:
                continue
            frappe.db.set_value(
                "Custom Field", cf.name, "mandatory_depends_on", target,
                update_modified=False,
            )
            changed = True

        if changed:
            frappe.db.commit()
            frappe.clear_cache(doctype="Quotation")
            frappe.clear_cache(doctype="Quotation Item")
    except Exception:
        pass
