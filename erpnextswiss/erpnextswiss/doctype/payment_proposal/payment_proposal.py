# -*- coding: utf-8 -*-
# Copyright (c) 2018-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
import time
from erpnextswiss.erpnextswiss.common_functions import get_building_number, get_street_name, get_pincode, get_city, get_primary_address, split_address_to_street_and_building
import html          # used to escape xml content
from frappe.utils import cint, get_url_to_form, rounded
from unidecode import unidecode     # used to remove German/French-type special characters from bank identifieres

PAYMENT_REMARKS = "From Payment Proposal {0}"

class PaymentProposal(Document):
    def validate(self):
        # check company settigs
        company_address = get_primary_address(target_name=self.company, target_type="Company")
        if (not company_address
            or not company_address.address_line1
            or not company_address.pincode
            or not company_address.city):
                frappe.throw( _("Company address missing or incomplete.") )
        if self.pay_from_account:
            payment_account = frappe.get_doc('Account', self.pay_from_account)
            if not payment_account.iban:
                frappe.throw( _("IBAN missing in pay from account.") )
        # perform some checks to improve file quality/stability
        for purchase_invoice in self.purchase_invoices: 
            pinv = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
            # check addresses (mandatory in ISO 20022
            if not pinv.supplier_address:
                frappe.throw( _("Address missing for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
            # check target account info
            if purchase_invoice.payment_type == "ESR" or purchase_invoice.payment_type == "QRR":
                if not purchase_invoice.esr_reference or not purchase_invoice.esr_participation_number:
                    frappe.throw( _("{0}: missing transaction information (participant number or reference) in <a href=\"/desk#Form/Purchase Invoice/{1}\">{1}</a>").format(
                        purchase_invoice.payment_type, pinv.name) )
            elif purchase_invoice.payment_type == "SCOR":
                # SCOR requires IBAN and structured reference
                supl = frappe.get_doc("Supplier", pinv.supplier)
                if not supl.iban:
                    frappe.throw( _("SCOR: missing IBAN for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
                if not purchase_invoice.external_reference:
                    frappe.throw( _("SCOR: missing structured reference for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
            else:
                # Check if the purchase invoice has an ESR participation number first
                if not pinv.get('esr_participation_number'):
                    # If not, check the supplier's IBAN
                    supl = frappe.get_doc("Supplier", pinv.supplier)
                    if not supl.iban:
                        frappe.throw( _("Missing IBAN for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
        # check expense records
        for expense_claim in self.expenses:
            emp = frappe.get_doc("Employee", expense_claim.employee)
            if not emp.bank_ac_no:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no bank account number.").format(emp.name) )
        return
        
    def on_submit(self):
        if (len(self.purchase_invoices) + len(self.expenses) + len(self.salaries)) == 0:
            frappe.throw( _("No transactions found. You can remove this entry.") )
        # clean payments (to prevent accumulation on re-submit)
        self.payments = []
        # create the aggregated payment table
        # collect customers
        suppliers = []
        total = 0
        for purchase_invoice in self.purchase_invoices:
            if purchase_invoice.supplier not in suppliers:
                suppliers.append(purchase_invoice.supplier)
        # aggregate purchase invoices
        for supplier in suppliers:
            amount = 0
            references = []
            currency = ""
            address = ""
            payment_type = "SEPA"
            # try executing in 90 days (will be reduced by actual due dates)
            exec_date = datetime.strptime(self.date, "%Y-%m-%d") + timedelta(days=90)
            for purchase_invoice in self.purchase_invoices:
                if purchase_invoice.supplier == supplier:
                    currency = purchase_invoice.currency
                    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    address = pinv.supplier_address
                    references.append(purchase_invoice.external_reference)
                    # find if skonto applies
                    if purchase_invoice.skonto_date:
                        skonto_date = datetime.strptime(purchase_invoice.skonto_date, "%Y-%m-%d")
                    due_date = datetime.strptime(purchase_invoice.due_date, "%Y-%m-%d")
                    if (purchase_invoice.skonto_date) and (skonto_date.date() >= datetime.now().date()):  
                        this_amount = purchase_invoice.skonto_amount    
                        if exec_date.date() > skonto_date.date():
                            exec_date = skonto_date
                    else:
                        this_amount = purchase_invoice.amount
                        if exec_date.date() > due_date.date():
                            exec_date = due_date
                    payment_type = purchase_invoice.payment_type
                    if payment_type in ["ESR", "QRR", "SCOR"] or self.individual_payments == 1:
                        # run as individual payment (not aggregated)
                        supl = frappe.get_doc("Supplier", supplier)
                        addr = frappe.get_doc("Address", address)
                        # For QRR, use ESR participation number as IBAN if available
                        iban = supl.iban
                        if payment_type == "QRR" and purchase_invoice.esr_participation_number:
                            iban = purchase_invoice.esr_participation_number
                        elif payment_type == "ESR" and purchase_invoice.esr_participation_number and 'CH' in purchase_invoice.esr_participation_number:
                            # This is actually a QRR, use participation number as IBAN
                            iban = purchase_invoice.esr_participation_number
                            
                        self.add_payment(
                            receiver_name=supl.supplier_name, 
                            iban=iban, 
                            payment_type=payment_type,
                            address_line1=addr.address_line1, 
                            address_line2="{0} {1}".format(addr.pincode, addr.city), 
                            country=addr.country,
                            pincode=addr.pincode,
                            city=addr.city,
                            amount=this_amount, 
                            currency=currency, 
                            reference=purchase_invoice.external_reference, 
                            execution_date=skonto_date or due_date, 
                            esr_reference=purchase_invoice.esr_reference, 
                            esr_participation_number=purchase_invoice.esr_participation_number, 
                            bic=supl.bic,
                            receiver_id=supl.name
                        )
                        total += this_amount
                    else:
                        amount += this_amount
                    # mark sales invoices as proposed
                    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        
                        self.create_payment("Supplier", supplier, 
                            "Purchase Invoice", purchase_invoice.purchase_invoice, exec_date,
                            purchase_invoice.amount, self.company)
            # make sure execution date is valid
            if exec_date < datetime.now():
                exec_date = datetime.now()      # + timedelta(days=1)
            # add new payment record
            if amount > 0:
                supl = frappe.get_doc("Supplier", supplier)
                addr = frappe.get_doc("Address", address)
                if payment_type in ["ESR", "QRR", "SCOR"]:           # prevent if last invoice was by ESR/QRR/SCOR, but others are also present -> pay as IBAN
                    payment_type = "IBAN"
                self.add_payment(
                    receiver_name=supl.supplier_name, 
                    iban=supl.iban, 
                    payment_type=payment_type,
                    address_line1=addr.address_line1, 
                    address_line2="{0} {1}".format(addr.pincode, addr.city), 
                    country=addr.country, 
                    pincode=addr.pincode, 
                    city=addr.city,
                    amount=amount, 
                    currency=currency, 
                    reference=" ".join(references), 
                    execution_date=exec_date, 
                    bic=supl.bic, 
                    receiver_id=supl.name
                )
                total += amount
        # collect employees
        employees = []
        account_currency = frappe.get_value("Account", self.pay_from_account, 'account_currency')
        for expense_claim in self.expenses:
            if expense_claim.employee not in employees:
                employees.append(expense_claim.employee)
        # aggregate expense claims
        for employee in employees:
            amount = 0
            references = []
            currency = ""
            for expense_claim in self.expenses:
                if expense_claim.employee == employee:
                    amount += expense_claim.amount
                    currency = account_currency
                    references.append(expense_claim.expense_claim)
                    # mark expense claim as proposed
                    invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if cint(self.use_intermediate) == 1:
                        self.create_payment("Employee", employee, 
                            "Expense Claim", expense_claim.expense_claim, exec_date,
                            expense_claim.amount)
            # add new payment record
            emp = frappe.get_doc("Employee", employee)
            if not emp.permanent_address:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no address.").format(emp.name) )
            address_lines = (emp.permanent_address or "").split("\n")
            plz_city = address_lines[1].split(" ")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(
                receiver_name=emp.employee_name, 
                iban=emp.bank_ac_no,
                bic=emp.bic or '',
                payment_type="IBAN",
                address_line1=address_lines[0],
                address_line2=address_lines[1],
                country=cntry,
                pincode=plz_city[0],
                city=plz_city[1],
                amount=amount,
                currency=currency,
                reference=" ".join(references),
                execution_date=self.date
            )
            total += amount
        # add salaries
        for salary in self.salaries:
            # mark expense claim as proposed
            salary_slip = frappe.get_doc("Salary Slip", salary.salary_slip)
            salary_slip.is_proposed = 1
            salary_slip.save()
            # create payment on intermediate
            if self.use_intermediate == 1:
                self.create_payment("Employee", employee, 
                    "Salary Slip", salary.salary_slip, exec_date,
                    salary.amount)
            # add new payment record
            emp = frappe.get_doc("Employee", salary.employee)
            if not emp.permanent_address:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no address.").format(emp.name) )
            address_lines = emp.permanent_address.split("\n")
            plz_city = address_lines[1].split(" ")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(
                receiver_name=emp.employee_name, 
                iban=emp.bank_ac_no,
                bic=emp.bic or '',
                payment_type="IBAN",
                address_line1=address_lines[0],
                address_line2=address_lines[1],
                country=cntry,
                pincode=plz_city[0],
                city=plz_city[1],
                amount=salary.amount,
                currency=account_currency,
                reference=(unidecode(salary.salary_slip))[-35:],
                execution_date=salary.target_date,
                is_salary=1
            )
            total += salary.amount
        # update total
        self.total = total
        # save
        self.save()

    def on_cancel(self):
        # reset is_proposed
        for purchase_invoice in self.purchase_invoices:
            # un-mark sales invoices as proposed
            invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
            invoice.is_proposed = 0
            invoice.save()        
        for expense_claim in self.expenses:
            # un-mark expense claim as proposed
            invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
            invoice.is_proposed = 0
            invoice.save()   
        for salary_slip in self.salaries:
            # un-mark salary slip as proposed
            invoice = frappe.get_doc("Salary Slip", salary_slip.salary_slip)
            invoice.is_proposed = 0
            invoice.save()
            
        if cint(self.use_intermediate) == 1:
            # cancel payment entries
            payments = frappe.get_all("Payment Entry", 
                filters={'payment_type': "Pay",
                    'paid_from': self.intermediate_account,
                    'remarks': PAYMENT_REMARKS.format(self.name),
                    'docstatus': 1},
                fields=['name']
            )
            for p in payments:
                doc = frappe.get_doc("Payment Entry", p['name'])
                doc.cancel()
                
        return
    
    def add_payment(self, receiver_name, iban, payment_type, address_line1, 
        address_line2, country, pincode, city, amount, currency, reference, execution_date, 
        esr_reference=None, esr_participation_number=None, bic=None, is_salary=0,
        receiver_id=None):
            # prepare payment date
            if isinstance(execution_date,datetime):
                pay_date = execution_date
            else:
                pay_date = datetime.strptime(execution_date, "%Y-%m-%d")
            # assure that payment date is not in th past
            if pay_date.date() < datetime.now().date():
                pay_date = datetime.now().date()
            # append payment record
            new_payment = self.append('payments', {
                'receiver': receiver_name,
                'receiver_id': receiver_id,
                'iban': iban,
                'bic': bic,
                'payment_type': payment_type,
                'receiver_address_line1': address_line1,
                'receiver_address_line2': address_line2,
                'receiver_pincode': pincode,
                'receiver_city': city,
                'receiver_country': country,    
                'amount': amount,
                'currency': currency,
                'reference': "{0}...".format(reference[:136]) if len(reference) > 140 else reference,
                'execution_date': pay_date,
                'esr_reference': esr_reference,
                'esr_participation_number': esr_participation_number,
                'is_salary': is_salary 
            })
            return
    
    def create_payment(self, party_type, party_name, 
                            reference_type, reference_name, date,
                            amount, company):
        intermediate_currency = frappe.get_cached_value("Account", self.intermediate_account, 'account_currency')
        if reference_type == "Purchase Invoice":
            credit_to = frappe.get_value(reference_type, reference_name, "credit_to")
            # if the document is in a foreign currency, calculate to expected value
            if frappe.get_value(reference_type, reference_name, "currency") != intermediate_currency:
                amount = rounded(amount * frappe.get_value(reference_type, reference_name, "conversion_rate"), 2)
        elif reference_type == "Expense Claim":
            credit_to = frappe.get_value(reference_type, reference_name, "payable_account")
        elif reference_type == "Expense Claim":
            credit_to = frappe.get_value("Company", 
                frappe.get_value(reference_type, reference_name, "company"), "default_payroll_payable_account")
        # create new payment entry
        new_payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'company': company, 
            'payment_type': "Pay",
            'party_type': party_type,
            'party': party_name,
            'posting_date': date,
            'paid_from': self.intermediate_account,
            'paid_to': credit_to,
            'received_amount': amount,
            'paid_amount': amount,
            'reference_no': reference_name,
            'reference_date': date,
            'remarks': PAYMENT_REMARKS.format(self.name),
            'references': [{ 
                'reference_doctype': reference_type,
                'reference_name': reference_name,
                'allocated_amount': amount,
                'due_date': date,
                'total_amount': amount,
                'outstanding_amount': amount
            }]
        })
        inserted_payment_entry = new_payment_entry.insert()
        inserted_payment_entry.submit()
        frappe.db.commit()
        return inserted_payment_entry
        
    @frappe.whitelist()
    def create_bank_file(self):
        data = {}
        settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
        data['xml_version'] = settings.get("xml_version")
        data['xml_region'] = settings.get("banking_region")
        data['msgid'] = "MSG-" + time.strftime("%Y%m%d%H%M%S")                # message ID (unique, SWIFT-characters only)
        data['date'] = time.strftime("%Y-%m-%dT%H:%M:%S")                    # creation date and time ( e.g. 2010-02-15T07:30:00 )
        # number of transactions in the file
        transaction_count = 0
        # total amount of all transactions ( e.g. 15850.00 )  (sum of all amounts)
        control_sum = 0.0
        # define company address
        data['company'] = {
            'name': html.escape(self.company)
        }
        company_address = get_primary_address(target_name=self.company, target_type="Company")
        if company_address:
            data['company']['address_line1'] = html.escape(company_address.address_line1)
            data['company']['address_line2'] = "{0} {1}".format(html.escape(company_address.pincode), html.escape(company_address.city))
            data['company']['country_code'] = company_address['country_code']
            data['company']['pincode'] = html.escape(company_address.pincode)
            data['company']['city'] = html.escape(company_address.city)
            # crop lines if required (length limitation)
            data['company']['address_line1'] = data['company']['address_line1'][:35]
            data['company']['address_line2'] = data['company']['address_line2'][:35]
            data['company']['street'] = html.escape(get_street_name(data['company']['address_line1'])[:35])
            data['company']['building'] = html.escape(get_building_number(data['company']['address_line1'])[:5])
            data['company']['pincode'] = data['company']['pincode'][:16]
            data['company']['city'] = data['company']['city'][:35]
        ### Payment Information (PmtInf, B-Level)
        # payment information records (1 .. 99'999)
        payment_account = frappe.get_doc('Account', self.pay_from_account)
        if not payment_account.iban or not payment_account.bic:
            frappe.throw( _("Account {0} is missing IBAN and/or BIC".format(
                self.pay_from_account) ) )
        data['company']['iban'] = "{0}".format(payment_account.iban.replace(" ", ""))
        data['company']['bic'] = "{0}".format(payment_account.bic.replace(" ", ""))
        data['payments'] = []
        for payment in self.payments:
            payment_content = ""
            payment_record = {
                'id': "PMTINF-{0}-{1}".format(self.name, transaction_count),   # unique (in this file) identification for the payment ( e.g. PMTINF-01, PMTINF-PE-00005 )
                'method': "TRF",             # payment method (TRF or TRA, no impact in Switzerland)
                'batch': "true",             # batch booking (true or false; recommended true)
                'required_execution_date': payment.execution_date.strftime("%Y-%m-%d") if hasattr(payment.execution_date, 'strftime') else str(payment.execution_date),         # Requested Execution Date (e.g. 2010-02-22)
                'debtor': {                    # debitor (technically ignored, but recommended)  
                    'name': html.escape(self.company),
                    'account': "{0}".format(payment_account.iban.replace(" ", "")),
                    'bic': "{0}".format(payment_account.bic)
                },
                'instruction_id': "INSTRID-{0}-{1}".format(self.name, transaction_count),          # instruction identification
                'end_to_end_id': "{0}".format((payment.reference[:33] + '..') if len(payment.reference) > 35 else payment.reference.strip()),   # end-to-end identification (should be used and unique within B-level; payment entry name)
                'currency': payment.currency,
                'amount': round(payment.amount, 2),
                'creditor': {
                    'name': html.escape(payment.receiver),
                    'address_line1': html.escape(payment.receiver_address_line1[:35]),
                    'address_line2': html.escape(payment.receiver_address_line2[:35]),
                    'street': html.escape(get_street_name(payment.receiver_address_line1)[:35]),
                    'building': html.escape(get_building_number(payment.receiver_address_line1)[:5]),
                    'country_code': frappe.get_value("Country", payment.receiver_country, "code").upper(),
                    'pincode': html.escape((payment.receiver_pincode or "")[:16]),
                    'city': html.escape((payment.receiver_city or "")[:35])
                },
                'is_salary': payment.is_salary
            }
            if payment.payment_type == "SEPA":
                # service level code (e.g. SEPA)
                payment_record['service_level'] = "SEPA"
                payment_record['iban'] = payment.iban.replace(" ", "")
                payment_record['reference'] = payment.reference
            elif payment.payment_type == "QRR":
                # QRR payment type
                payment_record['service_level'] = "QRR"
                payment_record['esr_participation_number'] = payment.esr_participation_number.replace(" ", "")  # QR-IBAN
                payment_record['esr_reference'] = payment.esr_reference.replace(" ", "")  # QR-Reference
            elif payment.payment_type == "SCOR":
                # SCOR (Structured Creditor Reference) payment type
                payment_record['service_level'] = "SCOR"
                payment_record['iban'] = payment.iban.replace(" ", "")
                payment_record['reference'] = payment.reference
            elif payment.payment_type == "ESR":
                # Decision whether ESR or QRR
                if 'CH' in payment.esr_participation_number:
                    # It is a QRR
                    payment_record['service_level'] = "QRR"                    # only internal information
                    payment_record['esr_participation_number'] = payment.esr_participation_number.replace(" ", "")                    # handle esr_participation_number as QR-IBAN
                    payment_record['esr_reference'] = payment.esr_reference.replace(" ", "")                    # handle esr_reference as QR-Reference
                else:
                    # proprietary (nothing or CH01 for ESR)            
                    payment_record['local_instrument'] = "CH01"
                    payment_record['service_level'] = "ESR"                    # only internal information
                    payment_record['esr_participation_number'] = payment.esr_participation_number
                    payment_record['esr_reference'] = payment.esr_reference.replace(" ", "")
            else:
                payment_record['service_level'] = "IBAN"
                payment_record['iban'] = payment.iban.replace(" ", "")
                payment_record['reference'] = payment.reference
                payment_record['bic'] = (payment.bic or "").replace(" ", "")
            # once the payment is extracted for payment, submit the record
            transaction_count += 1
            control_sum += round(payment.amount, 2)
            data['payments'].append(payment_record)
        data['transaction_count'] = transaction_count
        data['control_sum'] = control_sum
        
        # render file
        single_payment = cint(self.get("single_payment"))
        if data['xml_version'] == "09" and not single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001-001-09.html', data)
        elif data['xml_version'] == "09" and single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001-001-09_single_payment.html', data)
        elif single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001_single_payment.html', data)
        else:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001.html', data)
        
        # apply unidecode if enabled
        if cint(settings.get("use_unidecode")) == 1:
            content = unidecode(content)
        
        return { 'content': content }
    
    def create_wise_file(self):
        data = {
            'payments': []
        }
        source_currency = frappe.get_cached_value("Account", self.pay_from_account, "account_currency")
        for payment in self.payments:
            data['payments'].append({
                'recipient': payment.receiver,
                'recipient_mail': "",
                'reference': payment.reference,
                'amount': rounded(payment.amount, 2),
                'source_currency': source_currency,
                'target_currency': payment.currency,
                'iban': payment.iban.replace(" ", "")
            })

        # render file
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/transferwise_payments.html', data)
        return { 'content': content }
        
    def add_creditor_info(self, payment):
        payment_content = ""
        # creditor information
        payment_content += make_line("        <Cdtr>") 
        # name of the creditor/supplier
        payment_content += make_line("          <Nm>" + html.escape(payment.receiver)  + "</Nm>")
        # address of creditor/supplier (should contain at least country and first address line
        payment_content += make_line("          <PstlAdr>")
        # street name
        payment_content += make_line("            <StrtNm>{0}</StrtNm>".format(html.escape(get_street_name(payment.receiver_address_line1))))
        # building number
        payment_content += make_line("            <BldgNb>{0}</BldgNb>".format(html.escape(get_building_number(payment.receiver_address_line1))))
        # postal code
        payment_content += make_line("            <PstCd>{0}</PstCd>".format(html.escape(get_pincode(payment.receiver_address_line2))))
        # town name
        payment_content += make_line("            <TwnNm>{0}</TwnNm>".format(html.escape(get_city(payment.receiver_address_line2))))
        country = frappe.get_doc("Country", payment.receiver_country)
        payment_content += make_line("            <Ctry>" + country.code.upper() + "</Ctry>")
        payment_content += make_line("          </PstlAdr>")
        payment_content += make_line("        </Cdtr>") 
        return payment_content
        
    @frappe.whitelist()
    def has_active_ebics_connection(self):
        # First, try to find a direct connection based on the bank account
        connections = frappe.db.sql("""
            SELECT `name`, `activated` 
            FROM `tabebics Connection`
            WHERE `activated` = 1
              AND `company` = %(company)s
            ORDER BY `creation` DESC
            LIMIT 1;
            """, {'company': self.company}, as_dict=True)
        
        if connections:
            return connections
    
    @frappe.whitelist()
    def attach_generated_file(self, file_content, file_name, file_type):
        """Attach a generated file to this Payment Proposal"""
        import base64
        from frappe.utils.file_manager import save_file
        
        # Convert content to base64 if it's not already
        if not file_content.startswith('data:'):
            # Encode the content
            encoded_content = base64.b64encode(file_content.encode()).decode()
            file_content = f"data:application/xml;base64,{encoded_content}"
        
        # Save the file
        file_doc = save_file(
            fname=file_name,
            content=file_content,
            dt=self.doctype,
            dn=self.name,
            is_private=0
        )
        
        # Update the checkbox based on file type
        if file_type == "CAMT" and not self.bank_camt_file_generated:
            frappe.db.set_value(self.doctype, self.name, 'bank_camt_file_generated', 1)
        elif file_type == "EBICS" and not self.bank_ebics_file_generated:
            frappe.db.set_value(self.doctype, self.name, 'bank_ebics_file_generated', 1)
        
        return file_doc.name
    
    @frappe.whitelist()
    def generate_payment_file_from_proposal(self):
        """Generate payment file (pain.001) from Payment Proposal payments"""
        import time
        import html
        from erpnextswiss.erpnextswiss.page.payment_export.payment_export import make_line
        
        data = {}
        settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
        data['xml_version'] = settings.get("xml_version")
        data['xml_region'] = settings.get("banking_region")
        data['msgid'] = "MSG-" + time.strftime("%Y%m%d%H%M%S")
        data['date'] = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Company information
        data['company'] = {
            'name': html.escape(self.company)
        }
        company_address = get_primary_address(target_name=self.company, target_type="Company")
        if company_address:
            data['company']['address_line1'] = html.escape(company_address.address_line1[:35])
            data['company']['address_line2'] = "{0} {1}".format(html.escape(company_address.pincode), html.escape(company_address.city))[:35]
            data['company']['country_code'] = frappe.get_value("Country", company_address.country, "code").upper()
            data['company']['pincode'] = html.escape(company_address.pincode[:16])
            data['company']['city'] = html.escape(company_address.city[:35])
            data['company']['street'] = html.escape(get_street_name(company_address.address_line1)[:35])
            data['company']['building'] = html.escape(get_building_number(company_address.address_line1)[:5])
        
        # Bank account information (part of company in this template)
        account = frappe.get_doc("Account", self.pay_from_account)
        data['company']['iban'] = (account.iban or "").replace(" ", "")
        data['company']['bic'] = account.bic or ""
        
        # Process payments
        payments_data = []
        control_sum = 0.0
        
        transaction_count = 0
        for payment in self.payments:
            # Get country code
            country_code = frappe.get_value("Country", payment.receiver_country, "code")
            if country_code:
                country_code = country_code.upper()
            else:
                country_code = "CH"  # Default to Switzerland
            
            # Build payment reference (end_to_end_id)
            reference = (payment.reference or '')[:35]
            if len(payment.reference or '') > 35:
                reference = reference[:33] + ".."
                
            payment_dict = {
                'id': "PMTINF-{0}-{1}".format(self.name, transaction_count),
                'method': 'TRF',
                'batch': 'true',
                'required_execution_date': payment.execution_date if payment.execution_date else self.date,
                'debtor': {
                    'name': self.company,
                    'account': data['company']['iban'],
                    'bic': data['company']['bic']
                },
                'instruction_id': "INSTRID-{0}-{1}".format(self.name, transaction_count),
                'end_to_end_id': html.escape(reference),
                'currency': payment.currency,
                'amount': rounded(payment.amount, 2),
                'creditor': {
                    'name': html.escape(payment.receiver),
                    'address_line1': html.escape((payment.receiver_address_line1 or '')[:35]),
                    'address_line2': html.escape((payment.receiver_address_line2 or '')[:35]),
                    'street': html.escape(get_street_name(payment.receiver_address_line1 or '')[:35]),
                    'building': html.escape(get_building_number(payment.receiver_address_line1 or '')[:5]),
                    'country_code': country_code,
                    'pincode': html.escape((payment.receiver_pincode or '')[:16]),
                    'city': html.escape((payment.receiver_city or '')[:35])
                },
                'is_salary': payment.is_salary
            }
            
            # Handle payment type specific fields
            if payment.payment_type == "SEPA":
                payment_dict['service_level'] = "SEPA"
                payment_dict['iban'] = (payment.iban or '').replace(" ", "")
                payment_dict['reference'] = html.escape(payment.reference or '')
            elif payment.payment_type == "QRR":
                payment_dict['service_level'] = "QRR"
                payment_dict['esr_participation_number'] = (payment.esr_participation_number or '').replace(" ", "")
                payment_dict['esr_reference'] = payment.esr_reference or ''
            elif payment.payment_type == "SCOR":
                payment_dict['service_level'] = "SCOR"
                payment_dict['iban'] = (payment.iban or '').replace(" ", "")
                payment_dict['reference'] = payment.esr_reference or ''
            elif payment.payment_type == "ESR":
                # Check if it's actually a QRR masquerading as ESR
                if payment.esr_participation_number and 'CH' in payment.esr_participation_number:
                    payment_dict['service_level'] = "QRR"
                    payment_dict['esr_participation_number'] = payment.esr_participation_number
                    payment_dict['esr_reference'] = payment.esr_reference or ''
                else:
                    payment_dict['local_instrument'] = "CH01"
                    payment_dict['service_level'] = "ESR"
                    payment_dict['esr_participation_number'] = payment.esr_participation_number or ''
                    payment_dict['esr_reference'] = payment.esr_reference or ''
            else:  # IBAN
                payment_dict['service_level'] = "IBAN"
                payment_dict['iban'] = (payment.iban or '').replace(" ", "")
                payment_dict['reference'] = html.escape(payment.reference or '')
                if payment.bic:
                    payment_dict['bic'] = payment.bic
            
            transaction_count += 1
            payments_data.append(payment_dict)
            control_sum += payment.amount
        
        data['transaction_count'] = len(payments_data)
        data['control_sum'] = rounded(control_sum, 2)
        data['payments'] = payments_data
        
        # Render the pain.001 template based on XML version and settings
        single_payment = cint(self.get("single_payment"))
        if data['xml_version'] == "09" and not single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001-001-09.html', data)
        elif data['xml_version'] == "09" and single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001-001-09_single_payment.html', data)
        elif single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001_single_payment.html', data)
        else:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001.html', data)
        
        # Apply unidecode if enabled
        if cint(settings.get("use_unidecode")) == 1:
            content = unidecode(content)
        
        return {'content': content}
    
    @frappe.whitelist()
    def create_payment_entries_from_proposal(self):
        """Create Payment Entries from Payment Proposal payments"""
        created_count = 0
        payment_entries = []
        
        for payment in self.payments:
            # Determine party type and name
            party_type = None
            party_name = payment.receiver_id
            
            # Try to identify if it's a Supplier or Employee
            if frappe.db.exists("Supplier", payment.receiver_id):
                party_type = "Supplier"
            elif frappe.db.exists("Employee", payment.receiver_id):
                party_type = "Employee"
            else:
                # Try to find by name
                supplier = frappe.db.get_value("Supplier", {"supplier_name": payment.receiver}, "name")
                if supplier:
                    party_type = "Supplier"
                    party_name = supplier
                else:
                    employee = frappe.db.get_value("Employee", {"employee_name": payment.receiver}, "name")
                    if employee:
                        party_type = "Employee"  
                        party_name = employee
            
            if not party_type:
                frappe.log_error(f"Could not determine party type for payment to {payment.receiver}", "Payment Entry Creation")
                continue
            
            # Get the appropriate payable account
            if party_type == "Supplier":
                paid_to = frappe.get_value("Company", self.company, "default_payable_account")
            else:  # Employee
                paid_to = frappe.get_value("Company", self.company, "default_payroll_payable_account")
            
            # Get company currency
            company_currency = frappe.get_value("Company", self.company, "default_currency")
            
            # Create Payment Entry
            payment_entry = frappe.get_doc({
                'doctype': 'Payment Entry',
                'payment_type': 'Pay',
                'posting_date': self.date,
                'company': self.company,
                'party_type': party_type,
                'party': party_name,
                'paid_from': self.pay_from_account,
                'paid_from_account_currency': frappe.get_value("Account", self.pay_from_account, "account_currency") or company_currency,
                'paid_to': paid_to,
                'paid_to_account_currency': frappe.get_value("Account", paid_to, "account_currency") or company_currency,
                'paid_amount': payment.amount,
                'received_amount': payment.amount,
                'reference_no': payment.reference,
                'reference_date': payment.execution_date or self.date,
                'remarks': f'Payment from Payment Proposal {self.name}',
                'transaction_type': payment.payment_type
            })
            
            # Add payment type specific fields
            if payment.payment_type == "QRR":
                payment_entry.esr_participant_number = payment.esr_participation_number
                payment_entry.esr_reference = payment.esr_reference
            elif payment.payment_type == "SCOR":
                payment_entry.esr_participant_number = payment.esr_participation_number
                payment_entry.esr_reference = payment.esr_reference
            elif payment.payment_type == "ESR":
                payment_entry.esr_participant_number = payment.esr_participation_number
                payment_entry.esr_reference = payment.esr_reference
            elif payment.payment_type == "IBAN" and payment.iban:
                payment_entry.iban = payment.iban
                if payment.bic:
                    payment_entry.bic = payment.bic
            
            # Set exchange rate if needed
            if payment.currency != frappe.get_value("Company", self.company, "default_currency"):
                from erpnext.setup.utils import get_exchange_rate
                payment_entry.source_exchange_rate = get_exchange_rate(payment.currency, 
                    frappe.get_value("Company", self.company, "default_currency"), self.date)
            
            # Insert the payment entry
            payment_entry.insert()
            
            # If we can find related purchase invoices, add references
            if party_type == "Supplier" and payment.reference:
                # Try to find a purchase invoice with this reference
                purchase_invoices = frappe.get_all("Purchase Invoice", 
                    filters={
                        "supplier": party_name,
                        "docstatus": 1,
                        "outstanding_amount": [">", 0],
                        "name": payment.reference
                    },
                    fields=["name", "grand_total", "outstanding_amount"])
                
                if not purchase_invoices:
                    # Try with external reference
                    purchase_invoices = frappe.get_all("Purchase Invoice", 
                        filters={
                            "supplier": party_name,
                            "docstatus": 1,
                            "outstanding_amount": [">", 0],
                            "bill_no": payment.reference
                        },
                        fields=["name", "grand_total", "outstanding_amount"])
                
                # Add references for found invoices
                for invoice in purchase_invoices:
                    payment_entry.append("references", {
                        "reference_doctype": "Purchase Invoice",
                        "reference_name": invoice.name,
                        "total_amount": invoice.grand_total,
                        "outstanding_amount": invoice.outstanding_amount,
                        "allocated_amount": min(payment.amount, invoice.outstanding_amount)
                    })
                    
                payment_entry.save()
            
            # Submit the payment entry
            payment_entry.submit()
            payment_entries.append(payment_entry.name)
            created_count += 1
            
        frappe.db.commit()
        
        return {
            'created': created_count,
            'payment_entries': payment_entries
        }
        
# this function will create a new payment proposal
@frappe.whitelist()
def create_payment_proposal(date=None, company=None, currency=None):
    if not date:
        # get planning days
        planning_days = int(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'planning_days'))
        date = datetime.now() + timedelta(days=planning_days) 
        if not planning_days:
            frappe.throw( _("Please configure the planning period in ERPNextSwiss Settings.") )
    # check companies (take first created if none specififed)
    if company == None:
        companies = frappe.get_all("Company", filters={}, fields=['name'], order_by='creation')
        company = companies[0]['name']
    # get all suppliers with open purchase invoices
    sql_query = ("""SELECT 
                  `tabPurchase Invoice`.`supplier` AS `supplier`, 
                  `tabPurchase Invoice`.`name` AS `name`,
                  /* if creditor currency = document currency, use outstanding amount, otherwise grand total (in currency) */
                  (IF (`tabPurchase Invoice`.`currency` = `tabAccount`.`account_currency`,
                   `tabPurchase Invoice`.`outstanding_amount`,
                   `tabPurchase Invoice`.`grand_total`
                   )) AS `outstanding_amount`,
                  `tabPurchase Invoice`.`due_date` AS `due_date`, 
                  `tabPurchase Invoice`.`currency` AS `currency`,
                  `tabPurchase Invoice`.`bill_no` AS `external_reference`,
                  (IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, 
                     `tabPurchase Invoice`.`due_date`, 
                     (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY))
                     )) AS `skonto_date`,
                  /* if creditor currency = document currency, use outstanding amount, otherwise grand total (in currency) */
                  (IF (`tabPurchase Invoice`.`currency` = `tabAccount`.`account_currency`,
                    (((100 - IFNULL(`tabPayment Terms Template`.`skonto_percent`, 0))/100) * `tabPurchase Invoice`.`outstanding_amount`),
                    (((100 - IFNULL(`tabPayment Terms Template`.`skonto_percent`, 0))/100) * `tabPurchase Invoice`.`grand_total`)
                    )) AS `skonto_amount`,
                  `tabPurchase Invoice`.`payment_type` AS `payment_type`,
                  `tabPurchase Invoice`.`esr_reference_number` AS `esr_reference`,
                  `tabSupplier`.`esr_participation_number` AS `esr_participation_number`,
                  `tabPurchase Invoice`.`currency` AS `currency`
                FROM `tabPurchase Invoice` 
                LEFT JOIN `tabPayment Terms Template` ON `tabPurchase Invoice`.`payment_terms_template` = `tabPayment Terms Template`.`name`
                LEFT JOIN `tabSupplier` ON `tabPurchase Invoice`.`supplier` = `tabSupplier`.`name`
                LEFT JOIN `tabAccount` ON `tabAccount`.`name` = `tabPurchase Invoice`.`credit_to`
                WHERE `tabPurchase Invoice`.`docstatus` = 1 
                  AND `tabPurchase Invoice`.`outstanding_amount` > 0
                  AND ((`tabPurchase Invoice`.`due_date` <= '{date}') 
                    OR ((IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, `tabPurchase Invoice`.`due_date`, (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)))) <= '{date}'))
                  AND `tabPurchase Invoice`.`is_proposed` = 0
                  AND `tabPurchase Invoice`.`company` = '{company}'
                GROUP BY `tabPurchase Invoice`.`name`;""".format(date=date, company=company))
    purchase_invoices = frappe.db.sql(sql_query, as_dict=True)
    # get all purchase invoices that pending
    total = 0.0
    invoices = []
    for invoice in purchase_invoices:
        if not currency or invoice.currency == currency:
            reference = invoice.external_reference or invoice.name
            new_invoice = { 
                'supplier': invoice.supplier,
                'purchase_invoice': invoice.name,
                'amount': invoice.outstanding_amount,
                'due_date': invoice.due_date,
                'currency': invoice.currency,
                'skonto_date': invoice.skonto_date,
                'skonto_amount': invoice.skonto_amount,
                'payment_type': invoice.payment_type,
                'esr_reference': invoice.esr_reference,
                'esr_participation_number': invoice.esr_participation_number,
                'external_reference': unidecode(reference)
            }
            total += invoice.skonto_amount
            invoices.append(new_invoice)
    # get all open expense claims
    sql_query = ("""SELECT `name`, 
                  `employee`, 
                  `total_sanctioned_amount` AS `amount`,
                  `payable_account` 
                FROM `tabExpense Claim`
                WHERE `docstatus` = 1 
                  AND `status` = "Unpaid" 
                  AND `is_proposed` = 0
                  AND `company` = '{company}';""".format(company=company))
    expense_claims = frappe.db.sql(sql_query, as_dict=True)          
    expenses = []
    if not currency or currency == frappe.get_cached_value("Company", company, "default_currency"):
        for expense in expense_claims:
            new_expense = { 
                'expense_claim': expense.name,
                'employee': expense.employee,
                'amount': expense.amount,
                'payable_account': expense.payable_account
            }
            total += expense.amount
            expenses.append(new_expense)
    # get all open salary slips
    salaries = []
    if cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "enable_salary_payment")) == 1:
        sql_query = ("""SELECT `tabSalary Slip`.`name`, 
                      `tabSalary Slip`.`employee`, 
                      `tabSalary Slip`.`net_pay` AS `amount`,
                      `tabCompany`.`default_payroll_payable_account` AS `payable_account`,
                      `tabSalary Slip`.`posting_date` AS `posting_date`
                    FROM `tabSalary Slip`
                    LEFT JOIN `tabCompany` ON `tabSalary Slip`.`company` = `tabCompany`.`name`
                    WHERE `tabSalary Slip`.`docstatus` = 1 
                      AND `tabSalary Slip`.`is_proposed` = 0
                      AND `tabSalary Slip`.`net_pay` > 0
                      AND `tabSalary Slip`.`company` = '{company}';""".format(company=company))
        salary_slips = frappe.db.sql(sql_query, as_dict=True)          
        # append salary slips
        if not currency or currency == frappe.get_cached_value("Company", company, "default_currency"):
            for salary_slip in salary_slips:
                new_salary = { 
                    'salary_slip': salary_slip.name,
                    'employee': salary_slip.employee,
                    'amount': salary_slip.amount,
                    'payable_account': salary_slip.payable_account,
                    'target_date': salary_slip.posting_date
                }
                total += salary_slip.amount
                salaries.append(new_salary)
    # create new record
    new_record = None
    now = datetime.now()
    date = now + timedelta(days=1)
    new_proposal = frappe.get_doc({
        'doctype': "Payment Proposal",
        'title': "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
        'date': "{year:04d}-{month:02d}-{day:02d}".format(year=date.year, month=date.month, day=date.day),
        'purchase_invoices': invoices,
        'expenses': expenses,
        'salaries': salaries,
        'company': company,
        'total': total
    })
    proposal_record = new_proposal.insert(ignore_permissions=True)      # ignore permissions, as noone has create permission to prevent the new button
    new_record = proposal_record.name
    frappe.db.commit()
    return get_url_to_form("Payment Proposal", new_record)

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"


"""
Allow to release purchase invoices (switch to next revision, before that exists, so it can be cancelled)
"""
@frappe.whitelist()
def release_from_payment_proposal(purchase_invoice):
    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice)
    if pinv.amended_from:
        parts = pinv.name.split("-")
        new_name = "{0}-{1}".format("-".join(parts[:-1]), (cint(parts[-1]) + 1))
    else:
        new_name = "{0}-1".format(pinv.name)
    frappe.db.sql("""UPDATE `tabPayment Proposal Purchase Invoice` 
        SET `purchase_invoice` = "{new_name}" 
        WHERE `purchase_invoice` = "{old_name}";""".format(new_name=new_name, old_name=pinv.name))
    frappe.db.commit()
    return
