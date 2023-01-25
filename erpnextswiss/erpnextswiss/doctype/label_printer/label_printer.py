# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#//// all file
from __future__ import unicode_literals
import pdfkit, os, frappe
from frappe.model.document import Document

class LabelPrinter(Document):
	pass

# creates a pdf based on a label printer and a html content
def create_pdf(label_printer, content):
	# create temporary file
	fname = os.path.join("/tmp", "frappe-pdf-{0}.pdf".format(frappe.generate_hash()))

	options = {
		'page-width': '{0}mm'.format(label_printer.width),
		'page-height': '{0}mm'.format(label_printer.height),
		'margin-top': '0mm',
		'margin-bottom': '0mm',
		'margin-left': '0mm',
		'margin-right': '0mm' }

	css_content = """
		p {
			line-height: 1!important;
   			margin-bottom: 0!important;
			margin-top: 3px!important;
		}
		p:first-of-type {
			margin-top: -10px!important;
		}
		"""

	html_content = """
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="utf-8">
		<style>
			{css_content}
		</style>
	</head>
	<body style="text-align:center;">
		{content}
	<body>
	</html>
	""".format(content=content, css_content=css_content)

	pdfkit.from_string(html_content, fname, options=options or {})

	with open(fname, "rb") as fileobj:
		filedata = fileobj.read()

	cleanup(fname)

	return filedata

def cleanup(fname):
	if os.path.exists(fname):
		os.remove(fname)
		return 1
	return

@frappe.whitelist()
def download_label(label_reference, file_content):
	label = frappe.get_doc("Label Printer", label_reference)
	with open(file_content, 'r') as f:
		svg_content = f.read()
	#frappe.log_error("before")
	#frappe.log_error("delete", cleanup(file_content))
	#frappe.log_error("after")
	frappe.local.response.filename = "{name}.pdf".format(name=label_reference.replace(" ", "-").replace("/", "-"))
	frappe.local.response.filecontent = create_pdf(label, svg_content)
	frappe.local.response.type = "pdf"

@frappe.whitelist()
def save_content_svg(content, label_reference, item):
	fname = os.path.join("/tmp", "{item}-{label_reference}-{0}.txt".format(frappe.generate_hash(), item=item, label_reference=label_reference))
	with open(fname, 'w') as f:
		f.write(content)
	return fname
