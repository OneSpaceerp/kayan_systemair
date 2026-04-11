import frappe
from frappe import _


def remind_price_list_update():
    """
    Weekly scheduler task: notify SystemAir Admin users if price lists
    have not been updated in the last 90 days.
    """
    from frappe.utils import add_days, getdate, nowdate

    threshold_date = add_days(nowdate(), -90)

    price_lists = ["Systemair Germany 2026", "Systemair Malaysia 2026"]

    for pl_name in price_lists:
        last_import = frappe.db.get_value(
            "SystemAir Import Log",
            {"price_list": pl_name, "status": "Completed"},
            "creation",
            order_by="creation desc",
        )

        if not last_import or getdate(last_import) < getdate(threshold_date):
            _send_price_list_reminder(pl_name)


def _send_price_list_reminder(price_list_name):
    """Send a desk notification to SystemAir Admin users about stale price list."""
    admin_users = frappe.db.sql(
        """
        SELECT DISTINCT u.name
        FROM `tabUser` u
        JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE hr.role = 'SystemAir Admin'
          AND u.enabled = 1
          AND u.name != 'Administrator'
        """,
        as_dict=True,
    )

    for user in admin_users:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": _("Price List Update Required"),
            "email_content": _(
                "The price list '{0}' has not been updated in the last 90 days. "
                "Please import the latest price list from the Price List Import page."
            ).format(price_list_name),
            "for_user": user.name,
            "document_type": "Price List",
            "document_name": price_list_name,
            "type": "Alert",
        }).insert(ignore_permissions=True)
