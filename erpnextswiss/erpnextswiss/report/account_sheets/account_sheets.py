from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
        {"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 120},
        {"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 120},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": _("Against"), "fieldname": "against", "fieldtype": "Data", "width": 100},
        {"label": _("Voucher type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 140},
        {"label": _("Voucher"), "fieldname": "voucher", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 200},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 600},
        #{"label": _("Docstatus"), "fieldname": "docstatus", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters):
    account_conditions = ""
    transaction_conditions = ""
    if filters.from_account:
        account_number_from = frappe.db.get_value("Account", filters.from_account, "account_number")
        account_conditions += " AND `account_number` >= {0} ".format(account_number_from)
    if filters.to_account:
        account_number_to = frappe.db.get_value("Account", filters.to_account, "account_number")
        account_conditions += " AND `account_number` <= {0} ".format(account_number_to)
    if filters.cost_center:
        transaction_conditions += """ AND `cost_center` = "{0}" """.format(filters.cost_center)
    
    docstatus_condition = ""
    if not filters.get('include_cancelled'):
        docstatus_condition = " AND temp.`docstatus` = 1 "

    accounts = frappe.db.sql("""SELECT `name`
        FROM `tabAccount`
        WHERE `disabled` = 0
          AND `is_group` = 0
          AND `company` = "{company}"
          {conditions}
          ORDER BY `name` ASC;""".format(company=filters.company, conditions=account_conditions), as_dict=True)
    
    data = []

    # Créer une table temporaire pour contenir les docstatus des différents documents
    frappe.db.sql("""
        CREATE TEMPORARY TABLE IF NOT EXISTS temp_docstatus AS
        (SELECT `name` AS `voucher_no`, `docstatus` FROM `tabSales Invoice`
         UNION ALL
         SELECT `name` AS `voucher_no`, `docstatus` FROM `tabPurchase Invoice`
         UNION ALL
         SELECT `name` AS `voucher_no`, `docstatus` FROM `tabJournal Entry`
         UNION ALL
         SELECT `name` AS `voucher_no`, `docstatus` FROM `tabPayment Entry`
         UNION ALL
         SELECT `name` AS `voucher_no`, `docstatus` FROM `tabPeriod Closing Voucher`
         -- Ajouter d'autres tables si nécessaire
        )
    """)

    for account in accounts:
        positions = frappe.db.sql("""
            SELECT 
                gle.`posting_date` AS `posting_date`,
                gle.`debit` AS `debit`,
                gle.`credit` AS `credit`,
                gle.`remarks` AS `remarks`,
                gle.`voucher_type` AS `voucher_type`,
                gle.`voucher_no` AS `voucher`,
                gle.`against` AS `against`,
                COALESCE(temp.`docstatus`, -1) AS `docstatus`
            FROM `tabGL Entry` gle
            LEFT JOIN `temp_docstatus` temp ON temp.`voucher_no` = gle.`voucher_no`
            WHERE gle.`account` = "{account}"
              AND DATE(gle.`posting_date`) >= "{from_date}"
              AND DATE(gle.`posting_date`) <= "{to_date}"
              {conditions}
              {docstatus_condition}
            ORDER BY gle.`posting_date` ASC;
        """.format(conditions=transaction_conditions, docstatus_condition=docstatus_condition,
                   account=account['name'], from_date=filters.from_date, to_date=filters.to_date), as_dict=True)

        opening_balance_conditions = transaction_conditions + docstatus_condition
        opening_balance = frappe.db.sql("""SELECT 
                    IFNULL(SUM(`debit`), 0) AS `debit`,
                    IFNULL(SUM(`credit`), 0) AS `credit`
                FROM `tabGL Entry`
                LEFT JOIN `temp_docstatus` temp ON temp.`voucher_no` = `tabGL Entry`.`voucher_no`
                WHERE `tabGL Entry`.`account` = "{account}"
                  AND DATE(`tabGL Entry`.`posting_date`) < "{from_date}"
                  {conditions};""".format(conditions=opening_balance_conditions,
                                          account=account['name'], from_date=filters.from_date), as_dict=True)[0]
        if opening_balance['debit'] > opening_balance['credit']:
            opening_debit = opening_balance['debit'] - opening_balance['credit']
            opening_credit = 0
        else:
            opening_debit = 0
            opening_credit = opening_balance['credit'] - opening_balance['debit']
        opening_balance = opening_debit - opening_credit
        data.append({
            'date': filters.from_date, 
            'debit': opening_debit,
            'credit': opening_credit,
            'balance': opening_balance,
            'remarks': _("Opening")
        })
        # get positions
        positions = frappe.db.sql("""SELECT 
                `posting_date` AS `posting_date`,
                `debit` AS `debit`,
                `credit` AS `credit`,
                `remarks` AS `remarks`,
                `voucher_type` AS `voucher_type`,
                `voucher_no` AS `voucher`,
                `against` AS `against`
            FROM `tabGL Entry`
            WHERE `account` = "{account}"
              AND `docstatus` = 1
              AND DATE(`posting_date`) >= "{from_date}"
              AND DATE(`posting_date`) <= "{to_date}"
              {conditions}
            ORDER BY `posting_date` ASC;""".format(conditions=transaction_conditions,
            account=account['name'], from_date=filters.from_date, to_date=filters.to_date), as_dict=True)
        for position in positions:
            opening_debit += position['debit']
            opening_credit += position['credit']
            opening_balance = opening_balance - position['credit'] + position['debit']
            if "," in (position['against'] or ""):
                against = "{0} (...)".format((position['against'] or "").split(" ")[0])
            else:
                against = (position['against'] or "").split(" ")[0]
            if len(position['remarks'] or "") > 30:
                remarks = "{0}...".format(position['remarks'][:30])
            else:
                remarks = position['remarks']
            # replace line feed (for export)
            remarks = remarks.replace("\n", "") if remarks else ""
            data.append({
                'date': filters.from_date,
                'debit': opening_debit,
                'credit': opening_credit,
                'balance': opening_balance,
                'remarks': _("Opening")
            })

            for position in positions:
                opening_debit += position['debit']
                opening_credit += position['credit']
                opening_balance = opening_balance - position['credit'] + position['debit']
                if "," in (position['against'] or ""):
                    against = "{0} (...)".format((position['against'] or "").split(" ")[0])
                else:
                    against = (position['against'] or "").split(" ")[0]
                if len(position['remarks'] or "") > filters.remark_max_length:
                    remarks = "{0}...".format(position['remarks'][:filters.remark_max_length])
                else:
                    remarks = position['remarks']
                data.append({
                    'date': position['posting_date'],
                    'debit': position['debit'],
                    'credit': position['credit'],
                    'balance': opening_balance,
                    'voucher_type': position['voucher_type'],
                    'voucher': position['voucher'],
                    'against': against,
                    'remarks': _(remarks),
                    #'docstatus': position['docstatus'] if position['docstatus'] != -1 else _("Unknown")
                })

            data.append({
                'date': filters.to_date,
                'debit': opening_debit,
                'credit': opening_credit,
                'balance': opening_balance,
                'remarks': _("Closing")
            })

    return data
