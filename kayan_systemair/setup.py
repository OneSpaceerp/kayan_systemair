import glob
import json
import os

import frappe


def before_install():
    _sanitize_item_search_fields()


def before_migrate():
    _backup_all_workspaces()
    _sanitize_item_search_fields()


def after_install():
    _resync_erpnext_workspaces()
    _fix_sa_mandatory_fields()
    _relax_standard_mandatory_fields()
    _apply_item_search_fields()
    _ensure_smoke_rating_defaults()


def after_migrate():
    # Frappe v16 "Removing orphan Workspaces" runs BEFORE after_migrate hooks.
    # Restore anything it deleted, then re-sync the ERPNext workspace files.
    _restore_deleted_workspaces()
    _resync_erpnext_workspaces()
    _fix_sa_mandatory_fields()
    _relax_standard_mandatory_fields()
    _apply_item_search_fields()
    _ensure_smoke_rating_defaults()


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

def _ensure_smoke_rating_defaults():
    """
    Create the standard SystemAir Smoke Rating records if they don't exist.
    These are the values the JS temperature-mapping function produces and that
    the smoke_rating Link field points to.
    """
    defaults = ["Ambient", "300°C/2Hr", "400°C/2Hr", "120°C", "Explosion"]
    try:
        created = False
        for name in defaults:
            if frappe.db.exists("SystemAir Smoke Rating", name):
                continue
            doc = frappe.get_doc({
                "doctype": "SystemAir Smoke Rating",
                "name": name,
            })
            doc.flags.ignore_permissions = True
            doc.insert()
            created = True
        if created:
            frappe.db.commit()
    except Exception:
        pass


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
        # parent_doc is NOT available in this Frappe version's grid-row eval context.
        # Use cur_frm (the globally active form) which IS accessible via eval().
        item_fields = frappe.db.get_all(
            "Custom Field",
            filters={"dt": "Quotation Item", "reqd": 1},
            fields=["name", "fieldname", "mandatory_depends_on"],
        )
        for cf in item_fields:
            fn = cf.fieldname or ""
            if fn.startswith("sa_") or fn == "is_systemair_quotation":
                continue
            target = "eval:cur_frm && !cur_frm.doc.is_systemair_quotation"
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


def _relax_standard_mandatory_fields():
    """
    Standard (non-Custom) reqd fields cannot be reached through Custom Field
    mandatory_depends_on -- they need a Property Setter instead.

    The standard `items` table is reqd on Quotation, but SA quotations keep
    their rows in sa_items and only populate `items` server-side in
    _sync_to_standard_items. It is therefore still empty when the browser runs
    its mandatory check. That check aborts the save, and because Frappe
    disables the Save button at the start of the save routine and only
    re-enables it on success, the button is left permanently dead rather than
    showing an error.
    """
    target_expr = "eval:!doc.is_systemair_quotation"
    targets = [("Quotation", "items")]
    try:
        changed = False
        for dt, fieldname in targets:
            existing = frappe.db.get_value(
                "Property Setter",
                {
                    "doc_type": dt,
                    "field_name": fieldname,
                    "property": "mandatory_depends_on",
                },
                "value",
            )
            if existing == target_expr:
                continue
            frappe.make_property_setter(
                {
                    "doctype": dt,
                    "doctype_or_field": "DocField",
                    "fieldname": fieldname,
                    "property": "mandatory_depends_on",
                    "value": target_expr,
                    "property_type": "Data",
                },
                is_system_generated=False,
            )
            changed = True

        if changed:
            frappe.db.commit()
            frappe.clear_cache(doctype="Quotation")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Item.search_fields
#
# Frappe re-validates the whole Item DocType on EVERY Custom Field insert, and
# check_search_fields() throws if search_fields names a field that does not
# exist. Shipping "item_name,sa_article_no" as a Property Setter fixture is
# therefore self-defeating: on install the property setter is already in the
# database while sa_article_no is not, so the very first custom field imported
# aborts the entire fixture import. Strip unknown names before fixtures run,
# then re-apply the full list once the custom fields exist.
# ---------------------------------------------------------------------------

ITEM_SEARCH_FIELDS = ["item_name", "sa_article_no"]


def _item_has_field(fieldname):
    if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": fieldname}):
        return True
    return bool(
        frappe.db.get_value("DocField", {"parent": "Item", "fieldname": fieldname}, "name")
    )


def _set_item_search_fields(value):
    existing = frappe.db.get_value(
        "Property Setter",
        {
            "doc_type": "Item",
            "doctype_or_field": "DocType",
            "property": "search_fields",
        },
        "name",
    )
    if existing:
        if frappe.db.get_value("Property Setter", existing, "value") == value:
            return
        frappe.db.set_value(
            "Property Setter", existing, "value", value, update_modified=False
        )
    elif value:
        frappe.get_doc({
            "doctype": "Property Setter",
            "doc_type": "Item",
            "doctype_or_field": "DocType",
            "field_name": "main",
            "property": "search_fields",
            "property_type": "Data",
            "value": value,
        }).insert(ignore_permissions=True)
    else:
        return
    frappe.db.commit()
    frappe.clear_cache(doctype="Item")


def _sanitize_item_search_fields():
    """Drop search_fields entries whose field does not exist yet."""
    try:
        value = frappe.db.get_value(
            "Property Setter",
            {
                "doc_type": "Item",
                "doctype_or_field": "DocType",
                "property": "search_fields",
            },
            "value",
        )
        if not value:
            return
        kept = [
            f for f in (part.strip() for part in value.split(",")) if f and _item_has_field(f)
        ]
        new_value = ",".join(kept)
        if new_value != value:
            _set_item_search_fields(new_value)
    except Exception:
        pass


def _apply_item_search_fields():
    """Re-add sa_article_no once the custom fields have been synced."""
    try:
        kept = [f for f in ITEM_SEARCH_FIELDS if _item_has_field(f)]
        if kept:
            _set_item_search_fields(",".join(kept))
    except Exception:
        pass
