from __future__ import unicode_literals
import pdfkit, os, frappe
from frappe.model.document import Document
import os
import frappe
import json
from io import BytesIO, IOBase
import PyPDF2
import qrcode
from barcode import Code128, EAN13, EAN8, UPCA
from barcode.writer import ImageWriter
import base64
from barcode import get_barcode_class
from urllib.parse import unquote

class LabelPrinter(Document):
	pass

# creates a pdf based on a label printer and a html content
def create_pdf(label_printer, content, preview=False):
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
            .content-div {
                padding: 20px 20px 20px 20px;
                display: flex;
                align-items: center; 
            }
            .qr-div {
                flex: 0 0 auto;
                margin-right: 10px;
            }
            .text-div {
                flex: 1;
                text-align: left;
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
	if preview:
		return html_content
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
	frappe.local.response.filename = "{name}.pdf".format(name=label_reference.replace(" ", "-").replace("/", "-"))
	frappe.local.response.filecontent = create_pdf(label, svg_content)
	frappe.local.response.type = "pdf"

@frappe.whitelist()
def save_content_svg(content, label_reference, item):
	fname = os.path.join("/tmp", "{item}-{label_reference}-{0}.txt".format(frappe.generate_hash(), item=item, label_reference=label_reference))
	with open(fname, 'w') as f:
		f.write(content)
	return fname

@frappe.whitelist()
def generate_labels_for_products(label_details, selected_items, preview=False):
    label_details = json.loads(label_details)
    selected_items = json.loads(selected_items)

    pdfs = []
    errors = []
    html_preview = ""

    # get label printer details
    label_printer = frappe.get_doc("Label Printer", label_details.get("label_print"))
    type = label_details.get("type")

    for item_name in selected_items:
        item_name = unquote(item_name)
        item = frappe.get_doc("Item", item_name)

        # Determine the barcode value based on the 'value' and 'type' fields
        barcode_value = item.item_code  # default to item_code

        # Check if the selected type is one of EAN13, EAN8, or UPC
        if type in ["EAN", "EAN8", "EAN13", "UPC"] and label_details.get("value") == "Item barcode (if empty, use Item code)":
            if hasattr(item, "barcodes") and len(item.barcodes) > 0:
                selected_type_entry = next((entry for entry in item.barcodes if entry.barcode_type in type), None)
                if selected_type_entry:
                    barcode_value = selected_type_entry.barcode
                else:
                    errors += [("Item {0} : No suitable barcode found for type {1}<br>".format(item_name, type))]
                    continue
                    #raise ValueError(f"No suitable barcode found for item {item_name} for type {label_details.get('type')}")
            #else:
                #raise ValueError(f"No barcodes associated with item {item_name}")

        # Check if the barcode_value is numeric and the chosen type is EAN13
        if not barcode_value.isnumeric() and "EAN" in type:
            errors += [("Item {0} : Unable to generate EAN13 barcode for non-numeric value {1}<br>".format(item_name, barcode_value))]
            continue
            #raise ValueError("Unable to generate EAN13 barcode for non-numeric value: {}".format(barcode_value))
        if "EAN" in type:
            digits = int(type.replace("EAN", ""))
            if digits and len(barcode_value) != digits:
                errors += [("Item {0} : Unable to generate EAN barcode for value {1} with length {2}. Expected length: {3}<br>".format(item_name, barcode_value, len(barcode_value), digits))]
                continue
                #raise ValueError("Unable to generate EAN barcode for value {} with length {}. Expected length: {}".format(barcode_value, len(barcode_value), digits))

        # Generate barcode for the determined value
        barcode_img = generate_barcode_or_qr(barcode_value, type, label_details.get("bodebar_color"), label_details.get("codebar_height"), label_details.get("show_number"))
        barcode_img_tag = '<img style="height:{}px;" src="data:image/png;base64, {}"/>'.format(label_details.get("codebar_height"), barcode_img)

        # Get the quantity of labels for this item
        quantity = int(label_details.get("label_quantity", 1))

        for _ in range(quantity):
            content = label_details.get("content")
            content = content.replace("{price}", "{:.2f}".format(item.standard_rate) if item.standard_rate else "")
            content = content.replace("{reference}", item.item_code if item.item_code else "")
            content = content.replace("{unit}", item.stock_uom if item.stock_uom else "")
            content = content.replace("{brand}", item.brand if item.brand else "")
            content = content.replace("{category}", item.item_group if item.item_group else "")
            content = content.replace("{name}", item.item_name if item.item_name else "")
            content = content.replace("{description}", item.description if item.description else "")
            content = barcode_img_tag + content

            # Use the existing create_pdf function to generate the label
            if preview:
                html_preview = create_pdf(label_printer, content, preview=True)
                break
            else:
                pdf_content = create_pdf(label_printer, content)
                pdfs.append(pdf_content)
        if html_preview:
            break
    if preview:
        return {"pdf": html_preview, "errors": errors}
    # Combine all the generated labels into a single PDF
    if len(pdfs) > 0:
        combined_pdf_path = combine_pdfs(pdfs)
    else:
        combined_pdf_path = None

    return {"pdf": combined_pdf_path, "errors": errors}

def get_barcode(value, barcode_type, writer):
    """Renvoie un objet de code-barres basé sur le type fourni."""

    BARCODE_MAPPING = {
        "CODE128": Code128,
        "EAN8": EAN8,
        "EAN13": EAN13,
        "EAN": EAN13,
        "UPC": UPCA,
        "QR": "QR"  # ajouté pour la prise en charge du QR dans cette fonction
    }

    if barcode_type not in BARCODE_MAPPING:
        raise ValueError("Invalid barcode type")

    if barcode_type == "QR":
        # Génération de QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=writer.module_height,
            border=4
        )
        qr.add_data(value)
        qr.make(fit=True)
        img = qr.make_image(fill_color=writer.line_color, back_color="white")
        buffer = BytesIO()
        img.save(buffer, "PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    else:
        barcode_class = BARCODE_MAPPING[barcode_type]
        return barcode_class(value, writer=writer)

def generate_barcode_or_qr(value, type, color, height, show_number=True):
    """Génère un code-barres ou un QR code en fonction des paramètres fournis."""
    writer = ImageWriter()
    writer.line_color = color
    writer.module_height = height

    if not show_number:
        writer.font_size = 0

    barcode_obj = get_barcode(value, type, writer)
    
    if type == "QR":
        return barcode_obj  # C'est déjà une chaîne base64 pour le QR

    buffer = BytesIO()
    barcode_obj.write(buffer)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def combine_pdfs(pdfs):
    """Combinez plusieurs PDFs en un seul.
    :param pdfs: Liste des contenus PDF (chacun étant un stream ou un objet fichier).
    :return: Chemin du fichier PDF combiné sauvegardé sur le disque.
    """
    merger = PyPDF2.PdfMerger()

    for pdf in pdfs:
        # Convertir le contenu PDF en un objet BytesIO
        if not isinstance(pdf, (BytesIO, IOBase)):
            pdf = BytesIO(pdf)
    
        merger.append(pdf)

    # Définissez le chemin où vous souhaitez enregistrer le fichier PDF combiné
    # Vous pouvez ajuster ce chemin selon vos besoins
    output_path = os.path.join(frappe.get_site_path("public", "files"), "combined_labels.pdf")

    # Enregistrez le PDF combiné sur le disque
    with open(output_path, "wb") as f:
        merger.write(f)

    # Retournez le chemin du fichier PDF sauvegardé adapté pour l'URL correcte
    return "/files/combined_labels.pdf"

@frappe.whitelist()
def generate_employee_card(label_details, employee_name):
    label_details = json.loads(label_details)

    # get label printer details
    label_printer = frappe.get_doc("Label Printer", label_details.get("label_print"))
    employee = frappe.get_doc("Employee", employee_name)

    # Generate QR code for the employee name
    qr_img = generate_barcode_or_qr(employee_name, "QR", label_details.get("qr_color"), label_details.get("qr_height"))
    qr_img_tag = '<img style="height:{}px;" src="data:image/png;base64, {}"/>'.format(label_details.get("qr_height"), qr_img)

    content = label_details.get("content")
    content = content.replace("{name}", employee.employee_name if employee.employee_name else "")
    content = content.replace("{department}", employee.department if employee.department else "")
    content = content.replace("{designation}", employee.designation if employee.designation else "")
    content = content.replace("{employee_id}", employee.employee if employee.employee else "")
    content = content.replace("{date_of_joining}", employee.date_of_joining.strftime("%d/%m/%Y") if employee.date_of_joining else "")
    content = content.replace("{date_of_birth}", employee.date_of_birth.strftime("%d/%m/%Y") if employee.date_of_birth else "")
    content = content.replace("{blood_group}", employee.blood_group if employee.blood_group else "")

    # Add more content replacements if necessary
    content = f"""
        <div class="content-div">
            <div class="qr-div">
                {qr_img_tag}
            </div>
            <div class="text-div">
                {content}
            </div>
        </div>
        """


    # Use the existing create_pdf function to generate the label
    pdf_content = create_pdf(label_printer, content)

    # Save the generated PDF to the disk
    output_path = os.path.join(frappe.get_site_path("public", "files"), f"employee_card_{employee_name}.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_content)

    # Return the path of the saved PDF suitable for the correct URL
    return f"/files/employee_card_{employee_name}.pdf"
