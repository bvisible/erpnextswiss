# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
	return {
		'fieldname': 'ebics_statement',
		# Don't define transactions to avoid field mapping errors
		# Our custom JavaScript will handle the display
		'transactions': []
	}