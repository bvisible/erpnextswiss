# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ebicsLog(Document):
    pass

@frappe.whitelist()
def clear_ebics_logs():
    """Clear all EBICS logs - only for System Manager"""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Insufficient permissions to clear logs"))
    
    try:
        # Delete all ebics Log entries
        frappe.db.sql("DELETE FROM `tabebics Log`")
        frappe.db.commit()
        
        # Log this action
        frappe.log_error(
            message="All EBICS logs cleared by {}".format(frappe.session.user),
            title="EBICS Logs Cleared"
        )
        
        return {"success": True, "message": _("All EBICS logs have been cleared")}
    except Exception as e:
        frappe.log_error(
            message="Error clearing EBICS logs: {}".format(str(e)),
            title="EBICS Log Clear Error"
        )
        frappe.throw(_("Error clearing logs: {}").format(str(e)))