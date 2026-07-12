import frappe
from frappe import _

# Model-level item groups created under the "SystemAir Fans" parent group.
# Named "{MODEL} Model" to match the Item Group.xlsx convention.
MODEL_GROUPS = [
    "AXC Model", "AXR Model", "AXS Model", "AXCP Model", "AXCPV Model",
    "AXCBF Model", "AJR Model", "AJ8 Model",
    "DVV Model", "DVAX Model",
    "TD Model", "VTR Model", "VTRN Model", "SWL Model",
    "K Model", "KD Model", "KW Model", "KDH Model", "KT Model",
    "KTO Model", "KTSB Model", "KTO Model",
    "CBFA Model", "CBRD Model",
    "BD Model", "BDT Model", "BDH Model",
    "STAC Model", "STAQ Model",
    "IMP Model", "IMPD Model",
    "RS Model", "RSI Model", "RSH Model",
    "CA Model", "CAWA Model",
    "CDX Model", "CDXB Model",
    "DO Model", "DOC Model", "DOZ Model",
    "RV Model", "RVF Model", "RVZ Model",
    "R Model", "RF Model",
    "ILB Model", "ILBR Model",
    "Accessories",
]


def after_install():
    """Run after the app is installed on a site."""
    create_item_groups()
    create_price_lists()
    create_roles()
    create_item_search_field_property_setter()
    frappe.db.commit()


def create_item_groups():
    """
    Create "SystemAir Fans" parent group plus all model-level child groups.
    Also keeps the original "SystemAir Axial Fans" leaf group for existing items.
    """
    parent_root = "Products"
    if not frappe.db.exists("Item Group", "Products"):
        parent_root = "All Item Groups"

    # Create the parent group (is_group=1 so children can nest under it)
    if not frappe.db.exists("Item Group", "SystemAir Fans"):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "SystemAir Fans",
            "parent_item_group": parent_root,
            "is_group": 1,
        }).insert(ignore_permissions=True)
        frappe.logger().info("Created Item Group: SystemAir Fans")

    # Create each model-level child group (is_group=0 = leaf)
    seen = set()
    for group_name in MODEL_GROUPS:
        if group_name in seen:
            continue
        seen.add(group_name)
        if not frappe.db.exists("Item Group", group_name):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": group_name,
                "parent_item_group": "SystemAir Fans",
                "is_group": 0,
            }).insert(ignore_permissions=True)
            frappe.logger().info(f"Created Item Group: {group_name}")

    # Keep backward-compat leaf for items created before this version
    if not frappe.db.exists("Item Group", "SystemAir Axial Fans"):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "SystemAir Axial Fans",
            "parent_item_group": "SystemAir Fans",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        frappe.logger().info("Created Item Group: SystemAir Axial Fans")


def create_price_lists():
    """Create Germany and Malaysia price lists."""
    price_lists = [
        {
            "price_list_name": "Systemair Germany 2026",
            "currency": "EUR",
            "selling": 1,
            "enabled": 1,
        },
        {
            "price_list_name": "Systemair Malaysia 2026",
            "currency": "EUR",
            "selling": 1,
            "enabled": 1,
        },
    ]

    for pl_data in price_lists:
        if frappe.db.exists("Price List", pl_data["price_list_name"]):
            continue
        doc = frappe.get_doc({"doctype": "Price List", **pl_data})
        doc.insert(ignore_permissions=True)
        frappe.logger().info(f"Created Price List: {pl_data['price_list_name']}")


def create_item_search_field_property_setter():
    """
    Add sa_article_no to Item search_fields so users can search items by
    Systemair article number in Link fields throughout the app.
    """
    desired_value = "item_name,sa_article_no"
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
        frappe.db.set_value("Property Setter", existing, "value", desired_value)
    else:
        frappe.get_doc({
            "doctype": "Property Setter",
            "doc_type": "Item",
            "doctype_or_field": "DocType",
            "field_name": "main",
            "property": "search_fields",
            "property_type": "Data",
            "value": desired_value,
        }).insert(ignore_permissions=True)


def create_roles():
    """Create the three custom SystemAir roles."""
    roles = [
        {
            "role_name": "SystemAir Sales User",
            "desk_access": 1,
            "two_factor_auth": 0,
        },
        {
            "role_name": "SystemAir Sales Manager",
            "desk_access": 1,
            "two_factor_auth": 0,
        },
        {
            "role_name": "SystemAir Admin",
            "desk_access": 1,
            "two_factor_auth": 0,
        },
    ]

    for role_data in roles:
        if frappe.db.exists("Role", role_data["role_name"]):
            continue
        doc = frappe.get_doc({"doctype": "Role", **role_data})
        doc.insert(ignore_permissions=True)
        frappe.logger().info(f"Created Role: {role_data['role_name']}")
