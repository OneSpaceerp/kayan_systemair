import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


def assemble_model_code(doc):
    """
    Assemble the SystemAir type-key model code from the fan's attributes.

    Example output: AXC 355-6/10°-2(B)-PV MC
    """
    code = f"{doc.fan_model} {doc.nominal_diameter}"
    code += f"-{doc.num_blades}/{doc.blade_angle}\u00b0"
    code += f"-{doc.num_poles}"
    if doc.smoke_rating and doc.smoke_rating != "None":
        code += f"({doc.smoke_rating})"
    if doc.guide_vane:
        code += "-PV"
    if doc.medium_casing:
        code += " MC"
    if doc.config_suffix and doc.config_suffix != "None":
        code += doc.config_suffix
    if doc.reversible:
        code += "-TR"
    return code


class SystemAirFanItem(Document):
    # pylint: disable=no-member

    def validate(self):
        """Assemble model code, check item existence, fetch prices and weight."""
        self._validate_required_fields()
        self.model_code = assemble_model_code(self)
        self._check_item_exists()
        self._fetch_prices()
        self._fetch_weight()

    def on_submit(self):
        """Create ERPNext Item if it doesn't exist yet."""
        if not self.item_exists:
            self._create_erp_item()

    def on_cancel(self):
        """Nothing to reverse on cancel — the ERPNext Item remains."""
        pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_required_fields(self):
        """Validate that all required type-key fields are present."""
        if not self.fan_model:
            frappe.throw(_("Axial Fan Model is required."))
        if not self.nominal_diameter:
            frappe.throw(_("Nominal Fan Diameter is required."))
        if not self.num_blades or int(self.num_blades) <= 0:
            frappe.throw(_("Number of Blades must be a positive integer."))
        if not self.blade_angle:
            frappe.throw(_("Blade Angle is required."))
        if not self.num_poles:
            frappe.throw(_("Number of Poles is required."))

    def _check_item_exists(self):
        """Check if an ERPNext Item with model_code already exists."""
        existing = frappe.db.get_value(
            "Item", {"item_code": self.model_code}, "name"
        )
        if existing:
            self.item_exists = 1
            self.erp_item = existing
        else:
            self.item_exists = 0
            self.erp_item = None

    def _fetch_prices(self):
        """Fetch Germany and Malaysia list prices from Item Price."""
        self.germany_price = flt(_get_list_price(
            self.model_code, "Systemair Germany 2026"
        ))
        self.malaysia_price = flt(_get_list_price(
            self.model_code, "Systemair Malaysia 2026"
        ))

    def _fetch_weight(self):
        """Fetch approximate weight from SystemAir Weight Table."""
        diameter = int(flt(self.nominal_diameter)) if self.nominal_diameter else 0
        if not diameter:
            return
        result = frappe.db.get_value(
            "SystemAir Weight Table",
            {"nominal_diameter": diameter},
            ["min_weight_kg", "max_weight_kg"],
            as_dict=True,
        )
        if result:
            # Use midpoint of weight range as the approximate weight
            min_w = flt(result.min_weight_kg)
            max_w = flt(result.max_weight_kg)
            self.approx_weight = flt((min_w + max_w) / 2.0, 2)

    def _create_erp_item(self):
        """Create a new ERPNext Item from this fan item's data."""
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": self.model_code,
            "item_name": self.model_code,
            "item_group": "SystemAir Axial Fans",
            "stock_uom": "Nos",
            "is_purchase_item": 1,
            "is_sales_item": 1,
            "is_stock_item": 0,
            "description": self._build_description(),
            # Custom SA fields
            "sa_nominal_diameter": str(self.nominal_diameter),
            "sa_num_blades": int(self.num_blades) if self.num_blades else 0,
            "sa_blade_angle": self.blade_angle or "",
            "sa_num_poles": str(self.num_poles) if self.num_poles else "",
            "sa_smoke_rating": self.smoke_rating or "",
            "sa_weight_kg": flt(self.approx_weight),
            "sa_product_family": self.product_group or "",
            "sa_primary_factory": self.primary_factory or "",
        })
        item.insert(ignore_permissions=True)

        # Link back to the new item
        self.db_set("item_exists", 1)
        self.db_set("erp_item", item.name)

        frappe.msgprint(
            _("ERPNext Item <b>{0}</b> created successfully.").format(item.item_code),
            title=_("Item Created"),
            indicator="green",
        )

    def _build_description(self):
        """Build a description string for the new ERPNext Item."""
        parts = [
            f"SystemAir Axial Fan — {self.model_code}",
        ]
        if self.fan_type_desc:
            parts.append(self.fan_type_desc)
        if self.airflow_ls:
            parts.append(f"Airflow: {flt(self.airflow_ls, 2)} l/s")
        if self.esp_pa:
            parts.append(f"ESP: {flt(self.esp_pa, 2)} Pa")
        if self.input_power_kw:
            parts.append(f"Power: {flt(self.input_power_kw, 3)} kW")
        if self.speed_rpm:
            parts.append(f"Speed: {self.speed_rpm} rpm")
        return " | ".join(parts)


def _get_list_price(model_code, price_list):
    """
    Fetch a price from Item Price for the given model_code and price_list.
    Returns 0.0 if not found.
    """
    # Exact match
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": model_code, "price_list": price_list, "selling": 1},
        "price_list_rate",
    )
    if price:
        return flt(price)

    # Fuzzy fallback: item_name LIKE %model_code%
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
        (price_list, f"%{model_code}%"),
        as_dict=True,
    )
    if results:
        return flt(results[0].price_list_rate)

    return 0.0
