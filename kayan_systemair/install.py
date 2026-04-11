import frappe
from frappe import _


def after_install():
    """Run after the app is installed on a site."""
    create_item_group()
    create_price_lists()
    create_roles()
    frappe.db.commit()


def create_item_group():
    """Create 'SystemAir Axial Fans' item group under Products."""
    if frappe.db.exists("Item Group", "SystemAir Axial Fans"):
        return

    # Find parent group
    parent = "Products"
    if not frappe.db.exists("Item Group", "Products"):
        parent = "All Item Groups"

    doc = frappe.get_doc({
        "doctype": "Item Group",
        "item_group_name": "SystemAir Axial Fans",
        "parent_item_group": parent,
        "is_group": 0,
    })
    doc.insert(ignore_permissions=True)
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
