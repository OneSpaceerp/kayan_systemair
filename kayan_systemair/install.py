import frappe

def after_install():
    """Called by bench after app installation."""
    create_item_groups()
    create_price_lists()
    create_roles()
    setup_workspace()
    frappe.db.commit()
    print("[kayan_systemair] Installation complete.")

def create_item_groups():
    if not frappe.db.exists("Item Group", "SystemAir Axial Fans"):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "SystemAir Axial Fans",
            "parent_item_group": "Products",
            "is_group": 0,
        }).insert(ignore_permissions=True)

def create_price_lists():
    for pl_name in ["Systemair Germany 2026", "Systemair Malaysia 2026"]:
        if not frappe.db.exists("Price List", pl_name):
            frappe.get_doc({
                "doctype": "Price List",
                "price_list_name": pl_name,
                "currency": "EUR",
                "selling": 1,
                "buying": 0,
                "enabled": 1,
            }).insert(ignore_permissions=True)

def create_roles():
    for role in ["SystemAir Sales User", "SystemAir Sales Manager", "SystemAir Admin"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
                "desk_access": 1,
            }).insert(ignore_permissions=True)

def setup_workspace():
    """Ensure workspace is visible after install."""
    pass  # Workspace loaded from fixtures/workspace JSON
