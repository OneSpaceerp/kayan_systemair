import glob
import json
import os

import frappe


def before_migrate():
    _backup_all_workspaces()


def after_install():
    _resync_erpnext_workspaces()


def after_migrate():
    # Frappe v16 "Removing orphan Workspaces" runs BEFORE after_migrate hooks.
    # Restore anything it deleted, then re-sync the ERPNext workspace files.
    _restore_deleted_workspaces()
    _resync_erpnext_workspaces()


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
