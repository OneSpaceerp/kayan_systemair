import frappe
from frappe.model.document import Document


class SystemAirImportLog(Document):
    # Import log is written programmatically — no user-facing validation needed.
    pass
