# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

"""
EBICS Utility Functions
=======================

This module provides utility functions for the EBICS integration,
including date handling, error translation, and common operations.
"""

from datetime import datetime, date
import frappe
from frappe import _

def prepare_ebics_date(date_param):
    """
    Convert date parameter to string format expected by EBICS client.
    
    The fintech EBICS client expects date parameters as strings in ISO format (YYYY-MM-DD).
    This function handles conversion from various input types.
    
    Args:
        date_param: Date parameter (string, date, or datetime object)
        
    Returns:
        str: Date in YYYY-MM-DD format
        
    Raises:
        ValueError: If date format is invalid or type is unsupported
    """
    if date_param is None:
        return None
        
    if isinstance(date_param, str):
        # Validate string format
        try:
            # Try to parse to ensure valid date
            parsed = datetime.strptime(date_param, "%Y-%m-%d")
            return date_param
        except ValueError:
            # Try alternative formats
            for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y%m%d"]:
                try:
                    parsed = datetime.strptime(date_param, fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            raise ValueError(
                _("Invalid date format: {0}. Expected YYYY-MM-DD").format(date_param)
            )
            
    elif isinstance(date_param, datetime):
        return date_param.strftime("%Y-%m-%d")
        
    elif isinstance(date_param, date):
        return date_param.strftime("%Y-%m-%d")
        
    else:
        raise ValueError(
            _("Invalid date type: {0}. Expected string, date, or datetime").format(
                type(date_param).__name__
            )
        )

def parse_ebics_date(date_string):
    """
    Parse EBICS date string to Python date object.
    
    Args:
        date_string: Date string in YYYY-MM-DD format
        
    Returns:
        date: Python date object
        
    Raises:
        ValueError: If date string is invalid
    """
    if not date_string:
        return None
        
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            _("Invalid EBICS date format: {0}. Expected YYYY-MM-DD").format(date_string)
        )

def prepare_date_range(from_date, to_date):
    """
    Prepare and validate a date range for EBICS operations.
    
    Args:
        from_date: Start date (various formats)
        to_date: End date (various formats)
        
    Returns:
        tuple: (from_date_str, to_date_str, from_date_obj, to_date_obj)
        
    Raises:
        ValueError: If dates are invalid or range is incorrect
    """
    # Convert to strings
    from_date_str = prepare_ebics_date(from_date)
    to_date_str = prepare_ebics_date(to_date)
    
    # Parse to date objects for validation
    from_date_obj = parse_ebics_date(from_date_str)
    to_date_obj = parse_ebics_date(to_date_str)
    
    # Validate range
    if from_date_obj > to_date_obj:
        raise ValueError(
            _("Invalid date range: 'From Date' ({0}) must be before or equal to 'To Date' ({1})").format(
                from_date_str, to_date_str
            )
        )
    
    # Check for future dates
    today = date.today()
    if to_date_obj > today:
        frappe.msgprint(
            _("Warning: 'To Date' ({0}) is in the future. Bank may not have data for future dates.").format(
                to_date_str
            ),
            indicator='orange'
        )
    
    return from_date_str, to_date_str, from_date_obj, to_date_obj

# EBICS Error Code Translations
EBICS_ERROR_TRANSLATIONS = {
    # Technical errors (06xxxx)
    "061001": {
        "en": "Authentication failed. Please verify your EBICS credentials.",
        "de": "Authentifizierung fehlgeschlagen. Bitte überprüfen Sie Ihre EBICS-Zugangsdaten.",
        "fr": "Échec de l'authentification. Veuillez vérifier vos identifiants EBICS."
    },
    "061002": {
        "en": "Invalid signature. Please regenerate your keys.",
        "de": "Ungültige Signatur. Bitte generieren Sie Ihre Schlüssel neu.",
        "fr": "Signature invalide. Veuillez régénérer vos clés."
    },
    "061099": {
        "en": "Internal authentication error. Please contact your bank.",
        "de": "Interner Authentifizierungsfehler. Bitte kontaktieren Sie Ihre Bank.",
        "fr": "Erreur d'authentification interne. Veuillez contacter votre banque."
    },
    
    # Transaction errors (09xxxx)
    "090003": {
        "en": "Unknown user. Please verify your User ID with the bank.",
        "de": "Unbekannter Benutzer. Bitte überprüfen Sie Ihre Benutzer-ID bei der Bank.",
        "fr": "Utilisateur inconnu. Veuillez vérifier votre ID utilisateur auprès de la banque."
    },
    "090004": {
        "en": "Invalid user state. Please ensure your EBICS account is activated.",
        "de": "Ungültiger Benutzerstatus. Bitte stellen Sie sicher, dass Ihr EBICS-Konto aktiviert ist.",
        "fr": "État utilisateur invalide. Assurez-vous que votre compte EBICS est activé."
    },
    "091001": {
        "en": "Unknown order type. This operation is not supported by your bank.",
        "de": "Unbekannter Auftragstyp. Diese Operation wird von Ihrer Bank nicht unterstützt.",
        "fr": "Type d'ordre inconnu. Cette opération n'est pas supportée par votre banque."
    },
    "091005": {
        "en": "No data available for the requested period.",
        "de": "Keine Daten für den angeforderten Zeitraum verfügbar.",
        "fr": "Aucune donnée disponible pour la période demandée."
    },
    "091006": {
        "en": "Unsupported data format. Please check your bank configuration.",
        "de": "Nicht unterstütztes Datenformat. Bitte überprüfen Sie Ihre Bankkonfiguration.",
        "fr": "Format de données non supporté. Veuillez vérifier votre configuration bancaire."
    },
    
    # Additional Swiss-specific errors
    "EBICS_INVALID_ORDER_TYPE": {
        "en": "Invalid order type. For Swiss banks, please use XE2 for payments and Z53 for statements.",
        "de": "Ungültiger Auftragstyp. Für Schweizer Banken verwenden Sie bitte XE2 für Zahlungen und Z53 für Auszüge.",
        "fr": "Type d'ordre invalide. Pour les banques suisses, utilisez XE2 pour les paiements et Z53 pour les relevés."
    },
    "EBICS_PROCESSING_ERROR": {
        "en": "The order is being processed by the bank. Please check your e-banking for status.",
        "de": "Der Auftrag wird von der Bank verarbeitet. Bitte prüfen Sie den Status in Ihrem E-Banking.",
        "fr": "L'ordre est en cours de traitement par la banque. Veuillez vérifier le statut dans votre e-banking."
    }
}

def translate_ebics_error(error_code, error_message=None):
    """
    Translate EBICS error code to user-friendly message.
    
    Args:
        error_code: EBICS error code
        error_message: Original error message (optional)
        
    Returns:
        str: Translated error message
    """
    # Get user language
    lang = frappe.local.lang or 'en'
    if lang not in ['en', 'de', 'fr']:
        lang = 'en'
    
    # Check if we have a translation
    if error_code in EBICS_ERROR_TRANSLATIONS:
        translation = EBICS_ERROR_TRANSLATIONS[error_code]
        if isinstance(translation, dict):
            return translation.get(lang, translation.get('en', str(error_message or error_code)))
        else:
            return translation
    
    # Check for partial matches (e.g., error message contains the code)
    if error_message:
        for code, translation in EBICS_ERROR_TRANSLATIONS.items():
            if code in str(error_message):
                if isinstance(translation, dict):
                    return translation.get(lang, translation.get('en', error_message))
                else:
                    return translation
    
    # Return original message if no translation found
    return error_message or error_code

def log_ebics_request(connection_name, method, params, response=None, error=None):
    """
    Log EBICS requests for debugging.
    
    Args:
        connection_name: Name of the EBICS connection
        method: EBICS method called (e.g., 'Z53', 'BTD')
        params: Parameters passed to the method
        response: Response received (optional)
        error: Error if request failed (optional)
    """
    log_entry = {
        'connection': connection_name,
        'method': method,
        'params': params,
        'timestamp': datetime.now().isoformat(),
        'success': error is None
    }
    
    if error:
        log_entry['error'] = str(error)
        log_entry['error_type'] = type(error).__name__
        
    # Don't log sensitive data
    if 'passphrase' in str(params):
        log_entry['params'] = '<redacted>'
        
    # Log to frappe error log for debugging
    if error:
        frappe.log_error(
            title=f"EBICS {method} Error - {connection_name}",
            message=frappe.as_json(log_entry, indent=2)
        )
    else:
        # Only log successful requests if debug mode is on
        if frappe.conf.developer_mode:
            frappe.logger().debug(f"EBICS {method} Success: {log_entry}")

def format_ebics_amount(amount):
    """
    Format amount for EBICS/SEPA standards.
    
    Args:
        amount: Decimal or float amount
        
    Returns:
        str: Formatted amount string
    """
    # SEPA requires exactly 2 decimal places
    return "{:.2f}".format(float(amount))

def validate_iban(iban):
    """
    Validate IBAN format.
    
    Args:
        iban: IBAN string
        
    Returns:
        bool: True if valid
    """
    if not iban:
        return False
        
    # Remove spaces and convert to uppercase
    iban = iban.replace(' ', '').upper()
    
    # Swiss IBAN should be 21 characters
    if iban.startswith('CH') and len(iban) != 21:
        return False
        
    # Basic validation - could be enhanced with checksum validation
    return True

def get_swiss_bank_holidays(year):
    """
    Get Swiss bank holidays for a given year.
    
    Args:
        year: Year (int)
        
    Returns:
        list: List of date objects representing bank holidays
    """
    # Basic Swiss bank holidays - could be enhanced with cantonal holidays
    holidays = [
        date(year, 1, 1),   # New Year
        date(year, 1, 2),   # Berchtold's Day
        date(year, 5, 1),   # Labour Day
        date(year, 8, 1),   # Swiss National Day
        date(year, 12, 25), # Christmas
        date(year, 12, 26), # Boxing Day
    ]
    
    # Add Easter-based holidays (would need proper calculation)
    # Good Friday, Easter Monday, Ascension Day, Whit Monday
    
    return holidays

def is_bank_working_day(check_date):
    """
    Check if a date is a bank working day in Switzerland.
    
    Args:
        check_date: Date to check
        
    Returns:
        bool: True if working day
    """
    if isinstance(check_date, str):
        check_date = parse_ebics_date(check_date)
        
    # Check weekend
    if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
        
    # Check holidays
    holidays = get_swiss_bank_holidays(check_date.year)
    if check_date in holidays:
        return False
        
    return True

# Tests
def run_tests():
    """Run unit tests for EBICS utilities."""
    print("Testing EBICS utilities...")
    
    # Test date conversion
    test_date = date(2025, 1, 15)
    assert prepare_ebics_date(test_date) == "2025-01-15"
    assert prepare_ebics_date("2025-01-15") == "2025-01-15"
    assert prepare_ebics_date("15.01.2025") == "2025-01-15"
    assert prepare_ebics_date(datetime(2025, 1, 15, 10, 30)) == "2025-01-15"
    
    # Test date parsing
    assert parse_ebics_date("2025-01-15") == date(2025, 1, 15)
    
    # Test date range
    from_str, to_str, from_obj, to_obj = prepare_date_range("2025-01-01", "2025-01-31")
    assert from_str == "2025-01-01"
    assert to_str == "2025-01-31"
    assert from_obj < to_obj
    
    print("✓ All tests passed!")

if __name__ == "__main__":
    run_tests()