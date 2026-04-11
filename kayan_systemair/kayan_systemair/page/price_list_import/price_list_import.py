"""
Price List Import Page — Server-Side Methods
=============================================
Provides whitelisted API methods for:
1. Previewing an uploaded Excel file (first 20 rows)
2. Enqueueing the background import job
3. Getting import progress / log
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate


@frappe.whitelist()
def preview_excel(file_url, price_list):
    """
    Read the first 20 data rows from an uploaded Excel file and return
    them as a list of dicts for preview.

    Args:
        file_url (str): URL of the uploaded file (from Frappe File)
        price_list (str): Target price list name

    Returns:
        dict: {
            "columns": [...],
            "rows": [...],
            "sheet_name": str,
            "total_rows": int
        }
    """
    import openpyxl

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheet_name = _detect_sheet(wb.sheetnames, price_list)
    ws = wb[sheet_name]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        frappe.throw(_("Excel file appears to be empty."))

    # Detect header row
    header_row = [str(c).strip() if c is not None else "" for c in rows[0]]
    col_map = _map_columns(header_row)

    if not col_map.get("item_name") and not col_map.get("item_no"):
        frappe.throw(
            _(
                "Could not detect required columns. "
                "Expected: 'Item name' or 'item_name', 'Sales price' or 'sales_price', "
                "'Item no' or 'item_no'."
            )
        )

    preview_rows = []
    for row in rows[1:21]:  # First 20 data rows
        mapped = _map_row(row, col_map)
        if mapped:
            preview_rows.append(mapped)

    wb.close()
    return {
        "columns": ["Item Code / Name", "Price (EUR)", "Article No."],
        "rows": preview_rows,
        "sheet_name": sheet_name,
        "total_rows": max(0, ws.max_row - 1),
    }


@frappe.whitelist()
def start_import(file_url, price_list, sheet_name=None):
    """
    Enqueue a background job to import all rows from the Excel file
    into ERPNext Item Price records.

    Returns:
        dict: {"log_name": str}  — the SystemAir Import Log document name
    """
    # Create a pending import log
    log = frappe.get_doc({
        "doctype": "SystemAir Import Log",
        "price_list": price_list,
        "sheet_name": sheet_name or "",
        "imported_by": frappe.session.user,
        "status": "Pending",
        "records_created": 0,
        "records_updated": 0,
        "records_skipped": 0,
    })
    log.insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.enqueue(
        "kayan_systemair.kayan_systemair.page.price_list_import.price_list_import._run_import",
        queue="long",
        timeout=3600,
        file_url=file_url,
        price_list=price_list,
        sheet_name=sheet_name,
        log_name=log.name,
    )

    return {"log_name": log.name}


@frappe.whitelist()
def get_import_status(log_name):
    """Return the current status of an import job."""
    log = frappe.db.get_value(
        "SystemAir Import Log",
        log_name,
        ["status", "records_created", "records_updated", "records_skipped"],
        as_dict=True,
    )
    return log or {}


@frappe.whitelist()
def get_price_lists():
    """Return available SystemAir price lists."""
    lists = frappe.db.get_all(
        "Price List",
        filters={"price_list_name": ["like", "Systemair%"], "enabled": 1},
        fields=["name", "price_list_name", "currency"],
    )
    return lists


# ---------------------------------------------------------------------------
# Background job (called via frappe.enqueue — not whitelisted)
# ---------------------------------------------------------------------------

def _run_import(file_url, price_list, sheet_name, log_name):
    """
    Background job: read Excel file row by row, create/update Item + Item Price.
    Updates the SystemAir Import Log on completion.
    """
    import openpyxl

    created = 0
    updated = 0
    skipped = 0
    error_msg = None

    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        if not sheet_name:
            sheet_name = _detect_sheet(wb.sheetnames, price_list)
        ws = wb[sheet_name]

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ValueError("Excel file is empty")

        header_row = [str(c).strip() if c is not None else "" for c in rows[0]]
        col_map = _map_columns(header_row)

        if not col_map.get("item_name") and not col_map.get("item_no"):
            raise ValueError(
                "Cannot detect required columns (item_name/item_no, sales_price)"
            )

        for row_data in rows[1:]:
            mapped = _map_row(row_data, col_map)
            if not mapped:
                skipped += 1
                continue

            item_name = mapped.get("item_name") or mapped.get("article_no")
            article_no = mapped.get("article_no") or ""
            price = flt(mapped.get("price"))

            if not item_name or not price:
                skipped += 1
                continue

            # Get or create Item
            item_code = _get_or_create_item(item_name, article_no)

            # Upsert Item Price
            was_created = _upsert_item_price(item_code, price_list, price)
            if was_created:
                created += 1
            else:
                updated += 1

        wb.close()
        frappe.db.commit()

    except Exception as e:
        error_msg = str(e)
        frappe.log_error(frappe.get_traceback(), "SystemAir Price List Import Error")

    # Update import log
    status = "Failed" if error_msg else "Completed"
    frappe.db.set_value(
        "SystemAir Import Log",
        log_name,
        {
            "status": status,
            "records_created": created,
            "records_updated": updated,
            "records_skipped": skipped,
        },
    )
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _detect_sheet(sheet_names, price_list):
    """
    Auto-detect the correct sheet name based on the price list.
    Falls back to the first sheet if no match found.
    """
    price_list_lower = price_list.lower()

    for name in sheet_names:
        name_lower = name.lower()
        if "germany" in price_list_lower and ("germany" in name_lower or "de" in name_lower):
            return name
        if "malaysia" in price_list_lower and ("malaysia" in name_lower or "my" in name_lower):
            return name

    # If no match, return first sheet
    return sheet_names[0]


def _map_columns(header_row):
    """
    Build a column index map from the header row.
    Handles both German and English column headers.

    Returns dict: {"item_name": idx, "price": idx, "article_no": idx}
    """
    mapping = {}
    name_candidates = ["item name", "item_name", "description", "bezeichnung", "artikel"]
    price_candidates = ["sales price", "sales_price", "price", "preis", "list price"]
    article_candidates = ["item no", "item_no", "article no", "article_no", "artikel nr", "artikelnr"]

    for idx, col in enumerate(header_row):
        col_lower = col.lower().strip()
        if any(c in col_lower for c in name_candidates) and "item_name" not in mapping:
            mapping["item_name"] = idx
        if any(c in col_lower for c in price_candidates) and "price" not in mapping:
            mapping["price"] = idx
        if any(c in col_lower for c in article_candidates) and "article_no" not in mapping:
            mapping["article_no"] = idx

    return mapping


def _map_row(row, col_map):
    """Map a data row tuple to a dict using col_map."""
    if not row:
        return None

    def safe_get(idx):
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    item_name = safe_get(col_map.get("item_name"))
    price = safe_get(col_map.get("price"))
    article_no = safe_get(col_map.get("article_no"))

    if not item_name and not article_no:
        return None

    return {
        "item_name": str(item_name).strip() if item_name else "",
        "price": flt(price) if price is not None else 0.0,
        "article_no": str(article_no).strip() if article_no else "",
    }


def _get_or_create_item(item_name, article_no=""):
    """Return existing item_code or create a new Item and return its code."""
    # Try exact item_code match first
    existing = frappe.db.get_value("Item", {"item_code": item_name}, "name")
    if existing:
        return existing

    # Try item_name match
    existing = frappe.db.get_value("Item", {"item_name": item_name}, "name")
    if existing:
        return existing

    # Create new item
    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_name[:140],  # ERPNext item_code max length
        "item_name": item_name[:140],
        "item_group": "SystemAir Axial Fans",
        "stock_uom": "Nos",
        "is_purchase_item": 1,
        "is_sales_item": 1,
        "is_stock_item": 0,
        "sa_article_no": article_no[:140] if article_no else "",
    })
    item.insert(ignore_permissions=True)
    return item.item_code


def _upsert_item_price(item_code, price_list, price):
    """
    Create or update an Item Price record.

    Returns:
        bool: True if created, False if updated.
    """
    existing = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "selling": 1},
        "name",
    )

    if existing:
        frappe.db.set_value("Item Price", existing, "price_list_rate", price)
        return False
    else:
        ip = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": price_list,
            "price_list_rate": price,
            "selling": 1,
            "currency": "EUR",
            "valid_from": nowdate(),
        })
        ip.insert(ignore_permissions=True)
        return True
