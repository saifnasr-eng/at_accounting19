# -*- coding: utf-8 -*-
{
    "name": "AT Full Accounting — Enterprise Accounting Features for Community",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": (
        "Brings Odoo Enterprise accounting features to Community: asset "
        "management, deferred revenue/expense, bank reconciliation, "
        "follow-ups, and financial reports."
    ),
    "description": """
AT Full Accounting
==================

Adds the accounting capabilities that ship with the Enterprise edition of Odoo
to a Community installation, on top of the standard ``account`` module.

Available now
-------------
* Financial reports: Trial Balance and General Ledger, with initial balance,
  period movement and closing balance per account. Filter by date range,
  journal, account and posted/all entries. Printable as PDF.

Planned scope
-------------
* Asset management (depreciation boards, disposal, revaluation)
* Deferred revenue and deferred expense
* Bank statement reconciliation widget
* Customer follow-up levels and reminder letters
* Remaining financial reports: Balance Sheet, Profit & Loss, Cash Flow,
  Aged Partner Balance, Tax Report

This module is an independent implementation. It is not affiliated with,
endorsed by, or a redistribution of Odoo S.A.'s Enterprise edition.
""",
    "author": "Saif Nasr — Scalebox",
    "website": "https://github.com/saifnasr-eng/at_accounting19",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/report_templates.xml",
        "report/report_actions.xml",
        "wizard/financial_report_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
