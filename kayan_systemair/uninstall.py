import frappe


def before_uninstall():
    """Run before the app is removed from a site."""
    frappe.logger().info("Uninstalling kayan_systemair...")


def after_uninstall():
    """Run after the app is removed from a site."""
    frappe.logger().info("kayan_systemair uninstalled successfully.")
