"""
EBICS Control Panel Page
"""

import frappe

def get_context(context):
    """Page context for EBICS Control Panel"""
    context.no_cache = 1
    context.show_sidebar = True
    
    # Check permissions
    if not frappe.has_permission("EBICS Connection", "read"):
        raise frappe.PermissionError
    
    return context