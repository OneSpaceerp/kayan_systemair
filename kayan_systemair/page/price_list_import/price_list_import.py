import frappe
from frappe import _
from frappe.utils.file_manager import save_file
import openpyxl
import io

@frappe.whitelist()
def import_price_list(file_content, price_list_name, sheet_name):
    """
    Background-safe import function.
    Called from price_list_import.js via frappe.call().
    Enqueues a background job for large imports.
    """
    frappe.enqueue(
        "kayan_systemair.kayan_systemair.page.price_list_import.price_list_import._do_import",
        queue="long",
        timeout=3600,
        file_content=file_content,
        price_list_name=price_list_name,
        sheet_name=sheet_name,
        user=frappe.session.user,
    )
    return {"message": _("Import started in background. Check Import Log for results.")}

def _do_import(file_content, price_list_name, sheet_name, user):
    """Actual import logic \u2014 runs as background job."""
    wb = openpyxl.load_workbook(io.BytesIO(file_content.encode('latin1') if isinstance(file_content, str) else file_content), data_only=True)
    ws = wb[sheet_name]

    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    # Detect column positions
    name_col  = _find_col(headers, ["Item name", "item_name"])
    price_col = _find_col(headers, ["Sales price", "sales_price"])
    no_col    = _find_col(headers, ["Item no", "item_no"])

    created = updated = skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        item_name  = row[name_col]  if name_col  is not None else None
        list_price = row[price_col] if price_col is not None else None
        item_no    = row[no_col]    if no_col    is not None else None

        if not item_name or not list_price:
            skipped += 1
            continue

        # Get or create Item
        item_code = str(item_name).strip()
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": "SystemAir Axial Fans",
                "stock_uom": "Nos",
                "is_sales_item": 1,
                "is_purchase_item": 1,
                "is_stock_item": 0,
                "sa_article_no": str(item_no) if item_no else "",
            }).insert(ignore_permissions=True)
            created += 1
        else:
            updated += 1

        # Upsert Item Price
        existing_price = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": price_list_name},
            "name"
        )
        if existing_price:
            frappe.db.set_value("Item Price", existing_price, "price_list_rate", list_price)
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": price_list_name,
                "price_list_rate": list_price,
                "selling": 1,
                "currency": "EUR",
            }).insert(ignore_permissions=True)

    frappe.db.commit()

    # Write import log
    frappe.get_doc({
        "doctype": "SystemAir Import Log",
        "price_list": price_list_name,
        "sheet_name": sheet_name,
        "imported_by": user,
        "records_created": created,
        "records_updated": updated,
        "records_skipped": skipped,
        "status": "Completed",
    }).insert(ignore_permissions=True)
    frappe.db.commit()

def _find_col(headers, candidates):
    for i, h in enumerate(headers):
        if h and any(c.lower() in str(h).lower() for c in candidates):
            return i
    return None
