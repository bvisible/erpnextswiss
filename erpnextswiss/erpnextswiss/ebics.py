# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
# Sync can be externally triggered by
#  $ bench execute erpnextswiss.erpnextswiss.ebics.sync --kwargs "{'debug': True}"
#  $ bench execute erpnextswiss.erpnextswiss.ebics.sync_connection --kwargs "{'connection': 'MyBank', 'debug': True}"
#
# MIGRATION COMPLETE: Using ebics-api-client instead of fintech

import frappe
from frappe.utils import add_days
from datetime import datetime, date
from erpnextswiss.erpnextswiss.ebics_utils import prepare_ebics_date, prepare_date_range, translate_ebics_error, log_ebics_request

def sync(debug=False):
    if debug:
        print("Starting sync...")
    enabled_connections = frappe.get_all("ebics Connection", filters={'enable_sync': 1}, fields=['name'])
    if debug:
        print("Sync enabled for {0}".format(enabled_connections))
        
    for connection in enabled_connections:
        if debug:
            print("Syncing {0}".format(connection['name']))
        sync_connection(connection['name'], debug)
        
    if debug:
        print("Sync completed")
    return
            
def sync_connection(connection, debug=False):
    if not frappe.db.exists("ebics Connection", connection):
        print("Connection not found. Please check {0}.".format(connection) )
        return
        
    conn = frappe.get_doc("ebics Connection", connection)
    if not conn.synced_until:
        # try to sync last week
        date = add_days(datetime.today(), -7).date()
    else:
        date = add_days(conn.synced_until, 1)
    
    while date <= datetime.today().date():
        if debug:
            print("Syncing {0}...".format(date.strftime("%Y-%m-%d")))
            
        conn.get_transactions(date.strftime("%Y-%m-%d"))
        # note: sync date update happens in the transaction record when there are results
        
        date = add_days(date, 1)
    
    return

@frappe.whitelist()
def sync_connection_ui(connection_name, debug=False):
    """Wrapper for sync_connection that can be called from the UI"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
            
        conn = frappe.get_doc("ebics Connection", connection_name)
        if not conn.activated:
            frappe.throw("Connection is not activated")
            
        if not conn.enable_sync:
            frappe.throw("Sync is not enabled for this connection")
            
        # Get initial statistics
        initial_count = frappe.db.count("ebics Statement", filters={'ebics_connection': connection_name})
        pending_count = frappe.db.count("ebics Statement", filters={'ebics_connection': connection_name, 'status': 'Pending'})
        completed_count = frappe.db.count("ebics Statement", filters={'ebics_connection': connection_name, 'status': 'Completed'})
        
        # Calculate sync date range
        today = datetime.today().date()
        if not conn.synced_until:
            # try to sync last week
            start_date = add_days(today, -7).date()
            last_sync_info = "Never synchronized before"
        else:
            # If last sync was today, allow re-sync of today
            if conn.synced_until >= today:
                start_date = today
                last_sync_info = "Last synchronized: {0} (re-syncing today)".format(conn.synced_until.strftime("%d.%m.%Y"))
            else:
                start_date = add_days(conn.synced_until, 1)
                last_sync_info = "Last synchronized: {0}".format(conn.synced_until.strftime("%d.%m.%Y"))
        
        # Count days to sync
        days_to_sync = (today - start_date).days + 1  # +1 to include today
        
        # Perform sync
        date = start_date
        statements_created = 0
        errors = []
        days_processed = 0
        
        while date <= today:
            days_processed += 1
            if debug:
                print("Syncing {0}...".format(date.strftime("%Y-%m-%d")))
                
            try:
                conn.get_transactions(date.strftime("%Y-%m-%d"))
                # Check if a statement was created for this date
                if frappe.db.exists("ebics Statement", 
                    {'ebics_connection': connection_name, 'date': date.strftime("%Y-%m-%d")}):
                    statements_created += 1
            except Exception as e:
                error_msg = "Error on {0}: {1}".format(date.strftime("%d.%m.%Y"), str(e))
                errors.append(error_msg)
                if debug:
                    print(error_msg)
                    
            date = add_days(date, 1)
        
        # Get final statistics
        final_count = frappe.db.count("ebics Statement", filters={'ebics_connection': connection_name})
        new_statements = final_count - initial_count
        
        # Count transactions
        total_transactions = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabebics Statement Transaction`
            WHERE parent IN (
                SELECT name FROM `tabebics Statement` 
                WHERE ebics_connection = %(conn)s
            )
        """, {'conn': connection_name}, as_dict=True)[0]['count']
        
        pending_transactions = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabebics Statement Transaction`
            WHERE status = 'Pending' AND parent IN (
                SELECT name FROM `tabebics Statement` 
                WHERE ebics_connection = %(conn)s
            )
        """, {'conn': connection_name}, as_dict=True)[0]['count']
        
        # Build detailed HTML message
        message_html = """
        <table class="table table-bordered" style="margin-top: 10px;">
            <thead>
                <tr>
                    <th colspan="2" style="background-color: #f5f5f5;">Sync Summary</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="width: 50%;"><strong>Last Synchronization</strong></td>
                    <td>{last_sync}</td>
                </tr>
                <tr>
                    <td><strong>Days Processed</strong></td>
                    <td>{days_processed} of {days_to_sync}</td>
                </tr>
                <tr>
                    <td><strong>New Statements Imported</strong></td>
                    <td><span class="badge badge-primary">{new_statements}</span></td>
                </tr>
            </tbody>
        </table>
        
        <table class="table table-bordered" style="margin-top: 10px;">
            <thead>
                <tr>
                    <th colspan="3" style="background-color: #f5f5f5;">Total Statistics</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="width: 33%;"><strong>Total Statements</strong></td>
                    <td style="width: 33%;"><strong>Pending</strong></td>
                    <td style="width: 34%;"><strong>Completed</strong></td>
                </tr>
                <tr>
                    <td>{total_statements}</td>
                    <td><span class="badge badge-warning">{pending_statements}</span></td>
                    <td><span class="badge badge-success">{completed_statements}</span></td>
                </tr>
                <tr>
                    <td><strong>Total Transactions</strong></td>
                    <td><strong>Pending</strong></td>
                    <td><strong>Processed</strong></td>
                </tr>
                <tr>
                    <td>{total_transactions}</td>
                    <td><span class="badge badge-warning">{pending_transactions}</span></td>
                    <td><span class="badge badge-success">{processed_transactions}</span></td>
                </tr>
            </tbody>
        </table>
        """.format(
            last_sync=last_sync_info,
            days_processed=days_processed,
            days_to_sync=days_to_sync,
            new_statements=new_statements,
            total_statements=final_count,
            pending_statements=pending_count + new_statements,
            completed_statements=completed_count,
            total_transactions=total_transactions,
            pending_transactions=pending_transactions,
            processed_transactions=total_transactions - pending_transactions
        )
        
        if errors:
            message_html += """
            <table class="table table-bordered" style="margin-top: 10px;">
                <thead>
                    <tr>
                        <th style="background-color: #f8d7da; color: #721c24;">Errors Encountered</th>
                    </tr>
                </thead>
                <tbody>
            """
            for error in errors[:5]:
                message_html += "<tr><td>{0}</td></tr>".format(error)
            if len(errors) > 5:
                message_html += "<tr><td><em>... and {0} more errors</em></td></tr>".format(len(errors) - 5)
            message_html += """
                </tbody>
            </table>
            """
        
        return {
            'success': True,
            'count': new_statements,
            'message': message_html,
            'details': {
                'new_statements': new_statements,
                'total_statements': final_count,
                'pending_statements': pending_count + new_statements,
                'completed_statements': completed_count,
                'total_transactions': total_transactions,
                'pending_transactions': pending_transactions,
                'days_processed': days_processed,
                'days_to_sync': days_to_sync,
                'errors': len(errors)
            }
        }
        
    except Exception as e:
        frappe.log_error("EBICS Sync Error", str(e))
        return {
            'success': False,
            'error': str(e),
            'message': "Synchronization failed: {0}".format(str(e))
        }

@frappe.whitelist()
def sync_date_range(connection_name, from_date, to_date):
    """Sync EBICS statements for a specific date range"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        # Convert dates using utility function
        from_date_str, to_date_str, from_date_obj, to_date_obj = prepare_date_range(from_date, to_date)
        
        # Calculate days to sync
        days_to_sync = (to_date_obj - from_date_obj).days + 1
        
        # Get initial counts
        initial_count = frappe.db.count("ebics Statement", {'ebics_connection': connection_name})
        pending_count = frappe.db.count("ebics Statement", {'ebics_connection': connection_name, 'status': 'Pending'})
        completed_count = frappe.db.count("ebics Statement", {'ebics_connection': connection_name, 'status': 'Completed'})
        
        # Perform sync
        date = from_date_obj
        statements_created = 0
        errors = []
        days_processed = 0
        
        # Check if we should force daily sync
        if hasattr(frappe.flags, 'force_daily_sync') and frappe.flags.force_daily_sync:
            date = from_date_obj
        else:
            try:
                # Call get_transactions_range which should handle the full range
                conn.get_transactions_range(from_date_str, to_date_str)
                days_processed = days_to_sync
                
                # Count statements created in the range
                statements_created = frappe.db.count("ebics Statement", {
                    'ebics_connection': connection_name,
                    'date': ['between', [from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")]]
                })
            except AttributeError:
                date = from_date
            
            while date <= to_date:
                days_processed += 1
                
                try:
                    conn.get_transactions(date.strftime("%Y-%m-%d"))
                    # Check if a statement was created for this date
                    if frappe.db.exists("ebics Statement", 
                        {'ebics_connection': connection_name, 'date': date.strftime("%Y-%m-%d")}):
                        statements_created += 1
                except Exception as e:
                    error_msg = "Error on {0}: {1}".format(date.strftime("%d.%m.%Y"), str(e))
                    errors.append(error_msg)
                    
                date = add_days(date, 1)
        
        # Update sync date if needed
        if to_date > (conn.synced_until or datetime(1900, 1, 1).date()):
            conn.synced_until = to_date
            conn.save()
            frappe.db.commit()
        
        # Get final counts
        final_count = frappe.db.count("ebics Statement", {'ebics_connection': connection_name})
        new_statements = final_count - initial_count
        
        # Prepare result message
        message = f"""
## Sync Summary

**Date Range:** {from_date.strftime("%d.%m.%Y")} to {to_date.strftime("%d.%m.%Y")}  
**Days Processed:** {days_processed} of {days_to_sync}  
**New Statements Imported:** {new_statements}

### Total Statistics
- **Total Statements:** {final_count}
- **Pending:** {frappe.db.count("ebics Statement", {'ebics_connection': connection_name, 'status': 'Pending'})}
- **Completed:** {frappe.db.count("ebics Statement", {'ebics_connection': connection_name, 'status': 'Completed'})}

### Total Transactions
- **Total:** {frappe.db.sql("SELECT COUNT(*) FROM `tabebics Statement Transaction` WHERE parent IN (SELECT name FROM `tabebics Statement` WHERE ebics_connection = %s)", (connection_name,))[0][0]}
- **Pending:** {frappe.db.sql("SELECT COUNT(*) FROM `tabebics Statement Transaction` WHERE status = 'Pending' AND parent IN (SELECT name FROM `tabebics Statement` WHERE ebics_connection = %s)", (connection_name,))[0][0]}
- **Processed:** {frappe.db.sql("SELECT COUNT(*) FROM `tabebics Statement Transaction` WHERE status = 'Completed' AND parent IN (SELECT name FROM `tabebics Statement` WHERE ebics_connection = %s)", (connection_name,))[0][0]}
"""
        
        if errors:
            message += f"\n### Errors Encountered\n"
            for error in errors:
                message += f"- {error}\n"
        
        return {
            'success': True,
            'message': message,
            'stats': {
                'initial_count': initial_count,
                'final_count': final_count,
                'new_statements': new_statements,
                'days_processed': days_processed,
                'days_to_sync': days_to_sync,
                'errors': len(errors)
            }
        }
        
    except Exception as e:
        frappe.log_error("EBICS Date Range Sync Error", str(e))
        return {
            'success': False,
            'message': "Synchronization failed: {0}".format(str(e))
        }

@frappe.whitelist()
def preview_sync_range_detailed(connection_name, from_date, to_date, debug=False):
    """Enhanced preview that actually calls EBICS to get real data"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        # Convert dates using utility function
        from_date_str, to_date_str, from_date_obj, to_date_obj = prepare_date_range(from_date, to_date)
        
        # Get existing statements in the date range
        existing_statements = frappe.db.sql("""
            SELECT date, bank_statement_id, status, name
            FROM `tabebics Statement` 
            WHERE ebics_connection = %s 
            AND date >= %s 
            AND date <= %s
            ORDER BY date DESC
        """, (connection_name, from_date_obj, to_date_obj), as_dict=True)

        existing_dates = {stmt['date'].strftime("%Y-%m-%d") for stmt in existing_statements}

        available_statements = []
        total_available = 0
        statements_in_range = 0
        statements_to_import = 0
        date_summary = {}
        
        try:
            client = conn.get_client()
            bank_config = conn.get_bank_config()

            # Make the EBICS call
            if conn.ebics_version == "H005":
                from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
                Z53_format = BusinessTransactionFormat(
                    service=bank_config.statement_service_h005 or 'EOP',
                    msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                    scope=bank_config.statement_scope_h005 or 'CH',
                    version=bank_config.statement_version_h005 or '04',
                    container=bank_config.statement_container_h005 or 'ZIP'
                )
                data = client.BTD(Z53_format, start_date=from_date_str, end_date=to_date_str)
            else:
                data = client.Z53(start=from_date_str, end=to_date_str)
                
            client.confirm_download()
            
            total_available = len(data)
            
            # Analyze the returned data
            for account, content in data.items():
                try:
                    
                    from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta
                    meta = read_camt053_meta(content)
                    stmt_date = meta.get('statement_date')
                    
                    if stmt_date:
                        # Count by date
                        if stmt_date not in date_summary:
                            date_summary[stmt_date] = {'count': 0, 'in_range': False, 'exists': False}
                        date_summary[stmt_date]['count'] += 1
                        
                        # Check if in requested range
                        stmt_date_obj = datetime.strptime(stmt_date, "%Y-%m-%d").date()
                        if from_date_obj <= stmt_date_obj <= to_date_obj:
                            statements_in_range += 1
                            date_summary[stmt_date]['in_range'] = True
                            
                            # Check if already exists
                            if stmt_date not in existing_dates:
                                statements_to_import += 1
                            else:
                                date_summary[stmt_date]['exists'] = True
                except Exception as e:
                    frappe.log_error("Preview Parse Error", f"Error parsing account {account}: {str(e)}\n{frappe.get_traceback()}")
                    
        except Exception as e:
            frappe.log_error("Preview EBICS Error", str(e))
            # Fall back to estimation if EBICS call fails
            return {
                'existing_count': len(existing_statements),
                'days_in_range': (to_date_obj - from_date_obj).days + 1,
                'potential_new': 'Error checking EBICS',
                'from_date': from_date_obj.strftime("%d.%m.%Y"),
                'to_date': to_date_obj.strftime("%d.%m.%Y"),
                'recent_statements': existing_statements[:10],
                'error': str(e)
            }
        
        # Prepare detailed date breakdown
        date_breakdown = []
        for date_str in sorted(date_summary.keys(), reverse=True):
            info = date_summary[date_str]
            date_breakdown.append({
                'date': date_str,
                'count': info['count'],
                'in_range': info['in_range'],
                'exists': info['exists']
            })
        
        return {
            'existing_count': len(existing_statements),
            'days_in_range': (to_date_obj - from_date_obj).days + 1,
            'total_available_from_bank': total_available,
            'statements_in_range': statements_in_range,
            'statements_to_import': statements_to_import,
            'from_date': from_date_obj.strftime("%d.%m.%Y"),
            'to_date': to_date_obj.strftime("%d.%m.%Y"),
            'recent_statements': existing_statements[:10],
            'date_breakdown': date_breakdown[:20],  # Show top 20 dates
            'potential_new': statements_to_import  # Keep for compatibility
        }
        
    except Exception as e:
        frappe.log_error("Preview Sync Range Error", str(e))
        frappe.throw(str(e))

@frappe.whitelist()
def sync_date_range_advanced(connection_name, from_date, to_date, sync_mode='Range', debug=False):
    """Advanced sync with mode selection and debug options"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        # Use appropriate sync method based on mode
        if sync_mode == 'Range':
            # Call the sync_date_range method
            return sync_date_range(connection_name, from_date, to_date)
        else:
            # Daily mode - force day-by-day sync using the old logic            
            # Switch to use the regular sync logic but with date range
            frappe.flags.force_daily_sync = True
            result = sync_date_range(connection_name, from_date, to_date)
            frappe.flags.force_daily_sync = False
            
            return result
            
    except Exception as e:
        frappe.log_error("Advanced Sync Error", str(e))
        return {
            'success': False,
            'message': str(e)
        }

@frappe.whitelist()
def diagnose_ebics_availability(connection_name, test_months=3):
    """Diagnose what date ranges are available from EBICS"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        conn = frappe.get_doc("ebics Connection", connection_name)
        client = conn.get_client()
        bank_config = conn.get_bank_config()
        
        results = {
            'connection': connection_name,
            'bank': conn.url,
            'test_results': [],
            'available_ranges': [],
            'latest_available': None,
            'oldest_available': None
        }
        
        # Test different date ranges to find what's available
        today = datetime.today().date()
        
        # Test past months
        for months_ago in range(test_months):
            test_date = add_days(today, -30 * months_ago)
            try:
                if conn.ebics_version == "H005":
                    from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
                    Z53_format = BusinessTransactionFormat(
                        service=bank_config.statement_service_h005 or 'EOP',
                        msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                        scope=bank_config.statement_scope_h005 or 'CH',
                        version=bank_config.statement_version_h005 or '04',
                        container=bank_config.statement_container_h005 or 'ZIP'
                    )
                    data = client.BTD(Z53_format, start_date=prepare_ebics_date(test_date), end_date=prepare_ebics_date(test_date))
                else:
                    data = client.Z53(start=prepare_ebics_date(test_date), end=prepare_ebics_date(test_date))
                    
                client.confirm_download()
                
                if data:
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'available',
                        'count': len(data)
                    })
                    if not results['latest_available'] or test_date > datetime.strptime(results['latest_available'], "%Y-%m-%d").date():
                        results['latest_available'] = test_date.strftime("%Y-%m-%d")
                    if not results['oldest_available'] or test_date < datetime.strptime(results['oldest_available'], "%Y-%m-%d").date():
                        results['oldest_available'] = test_date.strftime("%Y-%m-%d")
                else:
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'no_data',
                        'count': 0
                    })
            except erpnextswiss.erpnextswiss.ebics_api.EbicsFunctionalError as err:
                if "EBICS_NO_DOWNLOAD_DATA_AVAILABLE" in str(err):
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'no_data',
                        'error': 'No data available'
                    })
                else:
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'error',
                        'error': str(err)
                    })
        
        # Test future dates (including July 2025)
        for months_ahead in range(1, 4):
            test_date = add_days(today, 30 * months_ahead)
            try:
                if conn.ebics_version == "H005":
                    from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
                    Z53_format = BusinessTransactionFormat(
                        service=bank_config.statement_service_h005 or 'EOP',
                        msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                        scope=bank_config.statement_scope_h005 or 'CH',
                        version=bank_config.statement_version_h005 or '04',
                        container=bank_config.statement_container_h005 or 'ZIP'
                    )
                    data = client.BTD(Z53_format, start_date=prepare_ebics_date(test_date), end_date=prepare_ebics_date(test_date))
                else:
                    data = client.Z53(start=prepare_ebics_date(test_date), end=prepare_ebics_date(test_date))
                    
                client.confirm_download()
                
                if data:
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'available',
                        'count': len(data)
                    })
                    if not results['latest_available'] or test_date > datetime.strptime(results['latest_available'], "%Y-%m-%d").date():
                        results['latest_available'] = test_date.strftime("%Y-%m-%d")
                else:
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'no_data',
                        'count': 0
                    })
            except erpnextswiss.erpnextswiss.ebics_api.EbicsFunctionalError as err:
                if "EBICS_NO_DOWNLOAD_DATA_AVAILABLE" in str(err):
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'no_data',
                        'error': 'No data available'
                    })
                else:
                    results['test_results'].append({
                        'date': test_date.strftime("%Y-%m-%d"),
                        'status': 'error',
                        'error': str(err)
                    })
        
        # Test specifically July 2025
        july_2025 = datetime(2025, 7, 15).date()
        try:
            if conn.ebics_version == "H005":
                from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
                Z53_format = BusinessTransactionFormat(
                    service=bank_config.statement_service_h005 or 'EOP',
                    msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                    scope=bank_config.statement_scope_h005 or 'CH',
                    version=bank_config.statement_version_h005 or '04',
                    container=bank_config.statement_container_h005 or 'ZIP'
                )
                data = client.BTD(Z53_format, start_date=prepare_ebics_date(july_2025), end_date=prepare_ebics_date(july_2025))
            else:
                data = client.Z53(start=prepare_ebics_date(july_2025), end=prepare_ebics_date(july_2025))
                
            client.confirm_download()
            
            results['july_2025_test'] = {
                'status': 'available' if data else 'no_data',
                'count': len(data) if data else 0
            }
        except Exception as e:
            results['july_2025_test'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return results
        
    except Exception as e:
        frappe.log_error("EBICS Diagnosis Error", str(e))
        return {
            'error': str(e)
        }

@frappe.whitelist()
def get_all_available_statements(connection_name, debug=False):
    """Get all available statements from EBICS without date restrictions"""
    try:
        from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
        
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        conn = frappe.get_doc("ebics Connection", connection_name)
        client = conn.get_client()
        bank_config = conn.get_bank_config()

        # Make EBICS call without specific dates - this gets all available
        try:
            if conn.ebics_version == "H005":
                from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
                Z53_format = BusinessTransactionFormat(
                    service=bank_config.statement_service_h005 or 'EOP',
                    msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                    scope=bank_config.statement_scope_h005 or 'CH',
                    version=bank_config.statement_version_h005 or '04',
                    container=bank_config.statement_container_h005 or 'ZIP'
                )
                # Call without date parameters to get all available
                data = client.BTD(Z53_format)
            else:
                # For H004, call Z53 without dates
                data = client.Z53()
                
            client.confirm_download()
            
            if not data:
                return {
                    'total_found': 0,
                    'new_statements': 0,
                    'existing_statements': 0,
                    'date_range': 'No data available',
                    'dates_summary': []
                }
            
            # Analyze the data
            dates_summary = {}
            total_found = len(data)
            new_statements = 0
            existing_statements = 0
            
            for account, content in data.items():
                try:
                    from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta
                    meta = read_camt053_meta(content)
                    stmt_date = meta.get('statement_date')
                    bank_statement_id = meta.get('msgid')
                    
                    if stmt_date:
                        if stmt_date not in dates_summary:
                            dates_summary[stmt_date] = {'count': 0, 'exists': False}
                        dates_summary[stmt_date]['count'] += 1
                        
                        # Check if already exists
                        if bank_statement_id and frappe.db.exists('ebics Statement', {'bank_statement_id': bank_statement_id}):
                            existing_statements += 1
                            dates_summary[stmt_date]['exists'] = True
                        else:
                            new_statements += 1
                            
                except Exception as e:
                    frappe.log_error("EBICS Parse Error", str(e))
            
            # Sort dates and create summary
            sorted_dates = sorted(dates_summary.keys())
            date_range = ""
            if sorted_dates:
                date_range = f"{sorted_dates[0]} to {sorted_dates[-1]}"
            
            dates_list = []
            for date in sorted_dates:
                dates_list.append({
                    'date': date,
                    'count': dates_summary[date]['count'],
                    'exists': dates_summary[date]['exists']
                })
            
            return {
                'total_found': total_found,
                'new_statements': new_statements,
                'existing_statements': existing_statements,
                'date_range': date_range,
                'dates_summary': dates_list
            }
            
        except erpnextswiss.erpnextswiss.ebics_api.EbicsFunctionalError as err:
            error_msg = str(err)
            if "EBICS_NO_DOWNLOAD_DATA_AVAILABLE" in error_msg:
                return {
                    'total_found': 0,
                    'new_statements': 0,
                    'existing_statements': 0,
                    'date_range': 'No data available from bank',
                    'dates_summary': []
                }
            else:
                frappe.throw("EBICS Error: {0}".format(error_msg))
                
    except Exception as e:
        frappe.log_error("Get All Available Error", str(e))
        frappe.throw(str(e))

@frappe.whitelist()
def import_all_available(connection_name, debug=False):
    """Import all available statements from EBICS"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        conn = frappe.get_doc("ebics Connection", connection_name)
        client = conn.get_client()
        bank_config = conn.get_bank_config()

        # Get all available data
        if conn.ebics_version == "H005":
            from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
            Z53_format = BusinessTransactionFormat(
                service=bank_config.statement_service_h005 or 'EOP',
                msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                scope=bank_config.statement_scope_h005 or 'CH',
                version=bank_config.statement_version_h005 or '04',
                container=bank_config.statement_container_h005 or 'ZIP'
            )
            data = client.BTD(Z53_format)
        else:
            data = client.Z53()
            
        client.confirm_download()
        
        if not data:
            return {
                'success': True,
                'message': 'No statements available from bank',
                'imported': 0
            }
        
        # Import all statements
        imported = 0
        skipped = 0
        errors = []
        latest_date = None
        
        for account, content in data.items():
            try:
                from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta
                meta = read_camt053_meta(content)
                bank_statement_id = meta.get('msgid')
                statement_date = meta.get('statement_date')
                
                # Track latest date
                if statement_date:
                    stmt_date_obj = datetime.strptime(statement_date, "%Y-%m-%d").date()
                    if not latest_date or stmt_date_obj > latest_date:
                        latest_date = stmt_date_obj
                
                # Check for duplicates
                if bank_statement_id and frappe.db.exists('ebics Statement', {'bank_statement_id': bank_statement_id}):
                    skipped += 1
                    continue
                
                # Create statement
                stmt = frappe.get_doc({
                    'doctype': 'ebics Statement',
                    'ebics_connection': connection_name,
                    'file_name': account,
                    'xml_content': content,
                    'date': statement_date or datetime.today().strftime("%Y-%m-%d"),
                    'company': conn.company
                })
                stmt.insert()
                frappe.db.commit()
                stmt.parse_content(debug=debug)
                stmt.process_transactions()
                imported += 1
                
            except Exception as e:
                errors.append(f"Error importing {account}: {str(e)}")
                frappe.log_error("Import Error", str(e))
        
        # Update synced_until date
        if latest_date:
            conn.synced_until = latest_date
            conn.save()
            frappe.db.commit()
        
        message = f"""
        <h5>Import Complete</h5>
        <p><strong>Statements Imported:</strong> {imported}</p>
        <p><strong>Statements Skipped (already exist):</strong> {skipped}</p>
        <p><strong>Total Processed:</strong> {len(data)}</p>
        """
        
        if latest_date:
            message += f"<p><strong>Synced Until:</strong> {latest_date.strftime('%d.%m.%Y')}</p>"
        
        if errors:
            message += f"<hr><p class='text-danger'><strong>Errors:</strong> {len(errors)}</p>"
            for error in errors[:5]:
                message += f"<p class='text-muted'>{error}</p>"
        
        return {
            'success': True,
            'message': message,
            'imported': imported,
            'skipped': skipped,
            'errors': len(errors)
        }
        
    except Exception as e:
        frappe.log_error("Import All Error", str(e))
        return {
            'success': False,
            'message': str(e)
        }

@frappe.whitelist()
def preview_sync_range(connection_name, from_date, to_date):
    """Preview what will be synchronized for a date range"""
    try:
        if not frappe.db.exists("ebics Connection", connection_name):
            frappe.throw("Connection not found: {0}".format(connection_name))
        
        # Convert dates if needed
        if isinstance(from_date, str):
            from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        if isinstance(to_date, str):
            to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        
        # Count existing statements in the date range
        existing_count = frappe.db.sql("""
            SELECT COUNT(*) 
            FROM `tabebics Statement` 
            WHERE ebics_connection = %s 
            AND date >= %s 
            AND date <= %s
        """, (connection_name, from_date, to_date))[0][0]
        
        # Calculate days in range
        days_in_range = (to_date - from_date).days + 1
        
        # Estimate potential new statements (this is just an estimate)
        # We can't know for sure without actually calling EBICS
        potential_new = days_in_range - existing_count
        if potential_new < 0:
            potential_new = 0
        
        return {
            'existing_count': existing_count,
            'days_in_range': days_in_range,
            'potential_new': potential_new,
            'from_date': from_date.strftime("%d.%m.%Y"),
            'to_date': to_date.strftime("%d.%m.%Y")
        }
        
    except Exception as e:
        frappe.log_error("Preview Sync Range Error", str(e))
        return {
            'error': str(e)
        }
