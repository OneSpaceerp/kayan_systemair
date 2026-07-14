"""
UAT Round-1 migration — CLIENT_FEEDBACK_FIXES.md
Handles:
  Issue 1: Rename EGP→EUR DB columns so existing draft data survives bench migrate
  Issue 2: Drop any unique index on Item.sa_article_no
  Issue 3: Remove header-level airflow/ESP Custom Fields (moved to per-row)
"""
import frappe


def execute():
    _rename_fan_item_columns()
    _rename_accessory_item_columns()
    _rename_quotation_columns()
    _delete_renamed_custom_fields()
    _remove_header_unit_custom_fields()
    _drop_article_no_unique_index()
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col_exists(doctype, col):
    return frappe.db.has_column(doctype, col)


def _rename(table, old, new_col):
    """Rename a column using CHANGE; keeps double NOT NULL DEFAULT 0."""
    frappe.db.sql(
        "ALTER TABLE `{}` CHANGE `{}` `{}` double NOT NULL DEFAULT 0".format(
            table, old, new_col
        )
    )


# ---------------------------------------------------------------------------
# Column renames
# ---------------------------------------------------------------------------

def _rename_fan_item_columns():
    if _col_exists("SystemAir Quotation Item", "unit_price_egp") and \
       not _col_exists("SystemAir Quotation Item", "unit_price_eur"):
        _rename("tabSystemAir Quotation Item", "unit_price_egp", "unit_price_eur")

    if _col_exists("SystemAir Quotation Item", "total_price_egp") and \
       not _col_exists("SystemAir Quotation Item", "total_price_eur"):
        _rename("tabSystemAir Quotation Item", "total_price_egp", "total_price_eur")


def _rename_accessory_item_columns():
    if _col_exists("SystemAir Accessory Item", "total_price_egp") and \
       not _col_exists("SystemAir Accessory Item", "total_price_eur"):
        _rename("tabSystemAir Accessory Item", "total_price_egp", "total_price_eur")


def _rename_quotation_columns():
    if _col_exists("Quotation", "sa_grand_total_egp") and \
       not _col_exists("Quotation", "sa_grand_total_eur"):
        _rename("tabQuotation", "sa_grand_total_egp", "sa_grand_total_eur")

    if _col_exists("Quotation", "sa_total_ddp_egp") and \
       not _col_exists("Quotation", "sa_total_ddp_eur"):
        _rename("tabQuotation", "sa_total_ddp_egp", "sa_total_ddp_eur")


# ---------------------------------------------------------------------------
# Custom Field record cleanup
# ---------------------------------------------------------------------------

def _delete_renamed_custom_fields():
    """
    Delete old Custom Field records for fields being renamed so that the new
    fixture (loaded during the same bench migrate) can create them under the
    correct fieldname without a name clash.
    """
    for cf_name in [
        "Quotation-sa_grand_total_egp",
        "Quotation-sa_total_ddp_egp",
    ]:
        if frappe.db.exists("Custom Field", cf_name):
            frappe.delete_doc(
                "Custom Field", cf_name,
                ignore_permissions=True, force=True
            )


def _remove_header_unit_custom_fields():
    """
    Issue 3: airflow / ESP unit dropdowns move from quotation header to each
    fan row.  Delete the header Custom Fields here so bench migrate does not
    re-create them from stale DocType cache.  The DB columns become orphaned
    (Frappe never drops columns automatically — harmless).
    """
    for cf_name in ["Quotation-sa_flow_unit", "Quotation-sa_esp_unit"]:
        if frappe.db.exists("Custom Field", cf_name):
            frappe.delete_doc(
                "Custom Field", cf_name,
                ignore_permissions=True, force=True
            )


# ---------------------------------------------------------------------------
# Index cleanup
# ---------------------------------------------------------------------------

def _drop_article_no_unique_index():
    """
    Issue 2: multiple Items may share the same article number (one per model
    variant).  Drop the unique index if it was accidentally created.
    """
    try:
        rows = frappe.db.sql("""
            SELECT INDEX_NAME
            FROM   information_schema.STATISTICS
            WHERE  TABLE_SCHEMA = DATABASE()
              AND  TABLE_NAME   = 'tabItem'
              AND  INDEX_NAME   = 'sa_article_no'
              AND  NON_UNIQUE   = 0
            LIMIT 1
        """)
        if rows:
            frappe.db.sql("ALTER TABLE `tabItem` DROP INDEX `sa_article_no`")
    except Exception:
        pass
