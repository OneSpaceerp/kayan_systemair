import csv
import io
import re

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_item_prices(item_code):
    """
    Return Germany and Malaysia list prices for the given item_code.

    Returns:
        dict: {"germany": float, "malaysia": float}
    """
    germany_price = _get_price(item_code, "Systemair Germany 2026")
    malaysia_price = _get_price(item_code, "Systemair Malaysia 2026")

    return {
        "germany": flt(germany_price),
        "malaysia": flt(malaysia_price),
    }


def _get_price(item_code, price_list):
    """Fetch price from Item Price — exact match first, then fuzzy."""
    # Exact match on item_code
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "selling": 1},
        "price_list_rate",
    )
    if price:
        return flt(price)

    # Fuzzy fallback: item_name LIKE %item_code%
    results = frappe.db.sql(
        """
        SELECT ip.price_list_rate
        FROM `tabItem Price` ip
        JOIN `tabItem` i ON i.item_code = ip.item_code
        WHERE ip.price_list = %s
          AND ip.selling = 1
          AND i.item_name LIKE %s
        LIMIT 1
        """,
        (price_list, f"%{item_code}%"),
        as_dict=True,
    )
    if results:
        return flt(results[0].price_list_rate)

    return 0.0


@frappe.whitelist()
def check_item_exists(model_code):
    """
    Check if an ERPNext Item with the given model_code exists.

    Returns:
        str | None: item_name if found, else None
    """
    item_name = frappe.db.get_value("Item", {"item_code": model_code}, "name")
    return item_name or None


@frappe.whitelist()
def get_weight_for_diameter(diameter):
    """
    Return weight range for the given nominal diameter from SystemAir Weight Table.

    Args:
        diameter: Nominal diameter in mm (int or str)

    Returns:
        dict: {"min_weight_kg": float, "max_weight_kg": float} or {}
    """
    diameter = int(flt(diameter))
    result = frappe.db.get_value(
        "SystemAir Weight Table",
        {"nominal_diameter": diameter},
        ["min_weight_kg", "max_weight_kg"],
        as_dict=True,
    )
    if result:
        return {
            "min_weight_kg": flt(result.min_weight_kg),
            "max_weight_kg": flt(result.max_weight_kg),
        }
    return {}


@frappe.whitelist()
def get_article_details(article_no):
    """
    Look up Item(s) by SA article number and return pricing + metadata.

    Returns:
        None                           — article_no not found
        dict                           — exactly one match (normal case)
        {"multiple": True, "items": []}— multiple models share this article_no;
                                         client must show a selection dialog
    """
    if not article_no:
        return None

    matches = frappe.db.get_all(
        "Item",
        filters={"sa_article_no": article_no},
        fields=["item_code"],
    )
    if not matches:
        return None

    if len(matches) > 1:
        items = []
        for m in matches:
            ic = m["item_code"]
            it = frappe.get_cached_doc("Item", ic)
            germany = _get_price(ic, "Systemair Germany 2026")
            malaysia = _get_price(ic, "Systemair Malaysia 2026")
            items.append({
                "item_code": ic,
                "item_name": it.item_name,
                "germany_list_price": flt(germany),
                "malaysia_list_price": flt(malaysia),
                "item_group": it.item_group,
                "product_family": getattr(it, "sa_product_family", "") or "",
                "type_of_fan": getattr(it, "sa_type_of_fan", "") or "",
                "primary_factory": getattr(it, "sa_primary_factory", "") or "",
                "temperature_rate": getattr(it, "sa_temperature_rate", "") or "",
                "weight_kg": flt(getattr(it, "sa_weight_kg", 0)),
            })
        return {"multiple": True, "items": items}

    item_code = matches[0]["item_code"]
    item = frappe.get_cached_doc("Item", item_code)
    germany = _get_price(item_code, "Systemair Germany 2026")
    malaysia = _get_price(item_code, "Systemair Malaysia 2026")

    return {
        "item_code": item_code,
        "item_name": item.item_name,
        "germany_list_price": flt(germany),
        "malaysia_list_price": flt(malaysia),
        "item_group": item.item_group,
        "product_family": getattr(item, "sa_product_family", "") or "",
        "type_of_fan": getattr(item, "sa_type_of_fan", "") or "",
        "primary_factory": getattr(item, "sa_primary_factory", "") or "",
        "temperature_rate": getattr(item, "sa_temperature_rate", "") or "",
        "weight_kg": flt(getattr(item, "sa_weight_kg", 0)),
    }


@frappe.whitelist()
def get_price_config():
    """
    Return the full SystemAir Price Config singleton as a dict.

    Returns:
        dict: All fields from SystemAir Price Config
    """
    config = frappe.get_single("SystemAir Price Config")
    return {
        "vat_rate": flt(config.vat_rate),
        "cost_factor_1": flt(config.cost_factor_1),
        "cost_factor_2": flt(config.cost_factor_2),
        "combined_cost_factor": flt(config.combined_cost_factor),
        "default_shipping_rate": flt(config.default_shipping_rate),
        "default_margin": flt(config.default_margin),
        "default_currency_rate": flt(config.default_currency_rate),
        "default_customs_rate": flt(config.default_customs_rate),
    }


# ---------------------------------------------------------------------------
# Spreadsheet import into the SystemAir child tables
# ---------------------------------------------------------------------------

SA_IMPORT_TABLES = {
    "sa_items": "SystemAir Quotation Item",
    "sa_accessories": "SystemAir Accessory Item",
}

_LAYOUT_FIELDTYPES = {
    "Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold",
}

MAX_IMPORT_ROWS = 500


def _normalize_header(text):
    """Fold a header to letters+digits so 'Unit Price (EUR)' == 'unit_price_eur'."""
    return re.sub(r"[^a-z0-9]+", "", str(text or "").strip().lower())


def _read_sheet(file_url):
    """Return the first worksheet of an xlsx/xls/csv File as a list of row lists."""
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    # file_url arrives from the browser; never read a file the user cannot.
    file_doc.check_permission("read")

    path = file_doc.get_full_path()
    fname = (file_doc.file_name or file_url or "").lower()

    if fname.endswith(".csv"):
        with io.open(path, "r", encoding="utf-8-sig", newline="") as fh:
            return [list(r) for r in csv.reader(fh)]

    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _coerce(df, value):
    if value is None:
        return None

    if df.fieldtype in ("Float", "Currency", "Percent", "Int"):
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
            if not value:
                return None
        try:
            return int(flt(value)) if df.fieldtype == "Int" else flt(value)
        except Exception:
            return None

    if df.fieldtype == "Check":
        return 1 if str(value).strip().lower() in ("1", "y", "yes", "true") else 0

    return str(value).strip() or None


@frappe.whitelist()
def import_sa_rows(file_url, table):
    """
    Parse an uploaded Excel/CSV sheet into rows for one of the SystemAir child
    tables. Columns are matched on each field's label or fieldname ignoring
    case, spacing and punctuation, so a sheet carrying the grid headers imports
    as-is.

    Rows are returned rather than written: the quotation is usually still
    unsaved when the user imports, so the client appends them and reruns the
    pricing engine.
    """
    if not frappe.has_permission("Quotation", "write"):
        frappe.throw(_("Not permitted to import Quotation rows."), frappe.PermissionError)

    child_doctype = SA_IMPORT_TABLES.get(table)
    if not child_doctype:
        frappe.throw(_("Unknown table {0}.").format(table))

    rows = _read_sheet(file_url)
    if not rows:
        frappe.throw(_("The uploaded file is empty."))

    meta = frappe.get_meta(child_doctype)
    by_header = {}
    for df in meta.fields:
        if df.fieldtype in _LAYOUT_FIELDTYPES:
            continue
        for key in (df.label, df.fieldname):
            folded = _normalize_header(key)
            if folded:
                by_header.setdefault(folded, df)

    # Header row = whichever of the first 5 rows matches the most columns.
    header_idx, header_map, best = 0, {}, 0
    for idx, raw in enumerate(rows[:5]):
        mapping = {}
        for col, cell in enumerate(raw):
            df = by_header.get(_normalize_header(cell))
            if df is not None:
                mapping[col] = df
        if len(mapping) > best:
            header_idx, header_map, best = idx, mapping, len(mapping)

    if not header_map:
        found = ", ".join(str(c).strip() for c in rows[0] if c is not None)
        frappe.throw(
            _("No column in the file matches a {0} column. Headers found: {1}").format(
                child_doctype, found or _("(none)")
            )
        )

    unmatched = [
        str(cell).strip()
        for col, cell in enumerate(rows[header_idx])
        if col not in header_map and cell is not None and str(cell).strip()
    ]

    out = []
    for raw in rows[header_idx + 1:]:
        row = {}
        for col, df in header_map.items():
            if col >= len(raw):
                continue
            val = _coerce(df, raw[col])
            if val is not None and val != "":
                row[df.fieldname] = val
        if row:
            out.append(row)
        if len(out) >= MAX_IMPORT_ROWS:
            break

    return {
        "rows": out,
        "count": len(out),
        "matched": sorted({df.label or df.fieldname for df in header_map.values()}),
        "unmatched": unmatched,
        "truncated": len(out) >= MAX_IMPORT_ROWS,
    }
