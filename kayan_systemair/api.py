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

MAX_IMPORT_ROWS = 2000

# Consecutive rows without a key value that end the import.
BLANK_ROW_LIMIT = 15

# Headers used by the Kayan COST workbook that do not match a field label or
# fieldname. Keys are folded the same way headers are (letters + digits).
SA_HEADER_ALIASES = {
    # COST carries both "SN" (F-01, the tag) and "Fan Ref. (SN)" (FAF-...).
    # The latter matches sa_sn by label; the tag belongs in location, whose
    # own "Location" column in that workbook is blank.
    "sn": "location",
    "flowls": "airflow_ls",
    "esppa": "esp_pa",
}

# Columns deliberately left out rather than reported as unmatched.
SA_IGNORED_HEADERS = {
    # Ambiguous list price, blank for every AXC row; list prices are fetched
    # from the Item master instead.
    "globleprice",
    # Stored as an Excel fraction (0.58 for 58%), which would import as 0.58%.
    # The quotation's own default discount fills each row instead.
    "discount",
}


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


def _item_resolver():
    """
    Resolve whatever a sheet calls an item to a real Item name.

    Items on this site are named by article number (235403) while the COST
    workbook's "Item Code (Model)" column carries the model name
    ("MUB 042 400EV Multibox"), so importing that column straight into the
    item_code Link produced "Item ... not found".

    Tries, in order: the code as an Item name, the article as an Item name,
    the article against Item.sa_article_no, then the code against
    Item.item_name. Results are cached because a sheet repeats models heavily.
    """
    cache = {}

    def resolve(code, article):
        key = (code, article)
        if key in cache:
            return cache[key]

        found = None
        for candidate in (code, article):
            if candidate and frappe.db.exists("Item", candidate):
                found = candidate
                break
        if not found and article:
            found = frappe.db.get_value("Item", {"sa_article_no": article}, "name")
        if not found and code:
            found = frappe.db.get_value("Item", {"item_name": code}, "name")

        cache[key] = found
        return found

    return resolve


SA_FAN_ITEM_GROUP = "SystemAir Axial Fans"


def _ensure_sa_item_group():
    if frappe.db.exists("Item Group", SA_FAN_ITEM_GROUP):
        return SA_FAN_ITEM_GROUP
    parent = "Products" if frappe.db.exists("Item Group", "Products") else "All Item Groups"
    frappe.get_doc({
        "doctype": "Item Group",
        "item_group_name": SA_FAN_ITEM_GROUP,
        "parent_item_group": parent,
        "is_group": 0,
    }).insert(ignore_permissions=True)
    return SA_FAN_ITEM_GROUP


def _fan_item_creator():
    """
    Create Items for configured fans the price lists do not carry.

    AXC fans are made to order -- the model string encodes diameter, blades,
    blade angle, poles and motor -- so they appear in no flat price list and
    Price List Import can never create them. The COST sheet is the only source
    that has them, which is why creation belongs here.

    Follows the convention already on site: the Item is named by article
    number (235403) with the model string as item_name.
    """
    from kayan_systemair.kayan_systemair.page.price_list_import.price_list_import import (
        _get_or_create_item,
        _sanitize_item_name,
    )

    group = _ensure_sa_item_group()
    cache = {}
    errors = []

    def create(code, article, row):
        key = (code, article)
        if key in cache:
            return cache[key]

        name = (article or "").strip() or _sanitize_item_name(code or "")
        if not name:
            cache[key] = None
            return None

        try:
            created = _get_or_create_item(
                item_name=name,
                article_no=(article or "").strip(),
                item_group=group,
                type_of_fan=row.get("fan_type") or "",
                primary_factory=row.get("origin") or "",
                temperature_rate=row.get("smoke_rating") or "",
                display_name=(code or name),
            )
        except Exception as exc:
            frappe.log_error(
                frappe.get_traceback(),
                "kayan_systemair: could not create Item for %s" % (code or article),
            )
            errors.append("%s: %s" % (name, exc))
            created = None

        cache[key] = created
        return created

    create.errors = errors
    return create


@frappe.whitelist()
def import_sa_rows(file_url, table, create_missing_items=1):
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
        # Read-only fields (cif, ddp_cost, unit_price_eur ...) are produced by
        # the pricing engine. A sheet column that happens to share their name
        # must not seed them.
        if df.fieldtype in _LAYOUT_FIELDTYPES or df.read_only:
            continue
        for key in (df.label, df.fieldname):
            folded = _normalize_header(key)
            if folded:
                by_header.setdefault(folded, df)

    # Header row = whichever of the first 5 rows matches the most columns.
    def _resolve(cell):
        key = _normalize_header(cell)
        if not key or key in SA_IGNORED_HEADERS:
            return None
        df = by_header.get(key)
        if df is None and key in SA_HEADER_ALIASES:
            df = meta.get_field(SA_HEADER_ALIASES[key])
        return df

    header_idx, header_map, best = 0, {}, 0
    for idx, raw in enumerate(rows[:5]):
        mapping = {}
        for col, cell in enumerate(raw):
            df = _resolve(cell)
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
        if col not in header_map
        and cell is not None
        and str(cell).strip()
        and _normalize_header(cell) not in SA_IGNORED_HEADERS
    ]

    # A real data row carries the key column. Sheets like the COST workbook
    # continue past the fan list with dropdown lookup values, which would
    # otherwise arrive as hundreds of junk rows, so stop once the key column
    # has been blank for a while.
    key_col = next(
        (c for c, df in header_map.items() if df.fieldname == "item_code"), None
    )

    # Creating Items writes to the Item master, so it needs its own permission
    # rather than riding on Quotation write access.
    can_create = bool(frappe.parse_json(create_missing_items)) and frappe.has_permission(
        "Item", "create"
    )
    create_item = _fan_item_creator() if can_create else None

    out = []
    created = []
    unresolved = []
    resolve_item = _item_resolver()
    blank_streak = 0
    for raw in rows[header_idx + 1:]:
        row = {}
        has_key = True
        if key_col is not None:
            cell = raw[key_col] if key_col < len(raw) else None
            has_key = cell is not None and str(cell).strip() != ""

        if has_key:
            for col, df in header_map.items():
                if col >= len(raw):
                    continue
                val = _coerce(df, raw[col])
                if val is not None and val != "":
                    row[df.fieldname] = val

        if row:
            blank_streak = 0
            code = row.get("item_code")
            article = row.get("sa_article_no")
            if code or article:
                resolved = resolve_item(code, article)
                if not resolved and create_item:
                    resolved = create_item(code, article, row)
                    if resolved:
                        created.append(resolved)
                if resolved:
                    row["item_code"] = resolved
                else:
                    # Keep whatever the sheet said rather than blanking it:
                    # item_code is mandatory, so a blank blocks the save of the
                    # whole quotation, which is worse than a value pointing at
                    # an Item that has not been created yet. These are reported
                    # back so the missing Items can be imported.
                    unresolved.append(code or article)
                    if not code and article:
                        row["item_code"] = article
            out.append(row)
            if len(out) >= MAX_IMPORT_ROWS:
                break
        else:
            blank_streak += 1
            if blank_streak >= BLANK_ROW_LIMIT:
                break

    return {
        "rows": out,
        "count": len(out),
        "matched": sorted({df.label or df.fieldname for df in header_map.values()}),
        "unmatched": unmatched,
        "truncated": len(out) >= MAX_IMPORT_ROWS,
        # Distinct items the sheet named that match no Item record. Their rows
        # still import, with item_code left blank rather than pointing at a
        # record that does not exist.
        "unresolved": sorted({u for u in unresolved if u})[:25],
        "unresolved_count": len({u for u in unresolved if u}),
        "created": sorted(set(created))[:25],
        "created_count": len(set(created)),
        "create_errors": (getattr(create_item, "errors", []) or [])[:5],
    }


@frappe.whitelist()
def repair_sa_item_codes(quotation, create_missing_items=1):
    """
    Re-resolve item_code on an existing SA quotation's sa_items rows.

    Quotations imported before item resolution existed hold the sheet's model
    name ("MUB 042 400EV Multibox") where the Item is keyed by article number
    ("235403"). This fixes those in place instead of re-importing, using the
    same resolver the importer uses.

    Only rows that resolve to a real Item are changed; anything still
    unresolved is left alone and reported, since those Items genuinely do not
    exist yet and need Price List Import.
    """
    if not frappe.has_permission("Quotation", "write", doc=quotation):
        frappe.throw(_("Not permitted to edit this Quotation."), frappe.PermissionError)

    doc = frappe.get_doc("Quotation", quotation)
    resolve = _item_resolver()
    can_create = bool(frappe.parse_json(create_missing_items)) and frappe.has_permission(
        "Item", "create"
    )
    create_item = _fan_item_creator() if can_create else None

    changed = 0
    created = []
    unresolved = []
    for row in doc.get("sa_items") or []:
        code = row.get("item_code")
        article = row.get("sa_article_no")
        if not (code or article):
            continue
        resolved = resolve(code, article)
        if not resolved and create_item:
            resolved = create_item(code, article, row)
            if resolved:
                created.append(resolved)
        if resolved:
            if resolved != code:
                row.item_code = resolved
                changed += 1
        else:
            unresolved.append(code or article)

    if changed:
        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()

    distinct = sorted({u for u in unresolved if u})
    return {
        "changed": changed,
        "created": sorted(set(created))[:25],
        "created_count": len(set(created)),
        "create_errors": (getattr(create_item, "errors", []) or [])[:5] if create_item else [],
        "can_create": can_create,
        "unresolved": distinct[:25],
        "unresolved_count": len(distinct),
    }


@frappe.whitelist()
def download_sa_table(table, quotation=None):
    """
    Download an SA child table as .xlsx, or an empty template when there is
    nothing to export.

    Columns are exactly the fields import_sa_rows accepts -- non-layout and
    not read-only -- so a downloaded file can be filled in and uploaded
    straight back without reshaping it. Read-only columns are excluded on
    purpose: the pricing engine owns them and the importer ignores them.
    """
    child_doctype = SA_IMPORT_TABLES.get(table)
    if not child_doctype:
        frappe.throw(_("Unknown table {0}.").format(table))

    meta = frappe.get_meta(child_doctype)
    fields = [
        df
        for df in meta.fields
        if df.fieldtype not in _LAYOUT_FIELDTYPES and not df.read_only
    ]

    rows = []
    if quotation:
        if not frappe.has_permission("Quotation", "read", doc=quotation):
            frappe.throw(
                _("Not permitted to read this Quotation."), frappe.PermissionError
            )
        rows = frappe.get_doc("Quotation", quotation).get(table) or []

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = child_doctype[:31]
    ws.append([df.label or df.fieldname for df in fields])

    for row in rows:
        ws.append([row.get(df.fieldname) for df in fields])

    # Give the header row a sensible width so the template is usable as-is.
    for idx, df in enumerate(fields, start=1):
        label = df.label or df.fieldname
        ws.column_dimensions[
            openpyxl.utils.get_column_letter(idx)
        ].width = min(max(len(label) + 2, 12), 40)

    buf = io.BytesIO()
    wb.save(buf)
    wb.close()

    frappe.response["filename"] = "%s-%s.xlsx" % (
        table,
        quotation if rows else "template",
    )
    frappe.response["filecontent"] = buf.getvalue()
    frappe.response["type"] = "binary"
