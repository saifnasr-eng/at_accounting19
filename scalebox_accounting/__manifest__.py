# -*- coding: utf-8 -*-
{
    "name": "Full Accounting for Odoo Community - Financial Reports, Assets, "
            "Deferrals and Follow-ups",
    "version": "19.0.1.0.1",
    "category": "Accounting/Accounting",
    # Bank reconciliation is deliberately absent from this line: the module
    # does not implement it, and the description says so under "Not included".
    # A summary is what shows on the store's search results, so it is the last
    # place to promise something that is not there.
    "summary": (
        "Seven printable financial reports, asset depreciation with disposal "
        "and revaluation, deferred revenue and expense, and customer "
        "follow-ups - on top of Community accounting."
    ),
    "description": """
AT Full Accounting
==================

Adds the accounting capabilities that ship with the Enterprise edition of Odoo
to a Community installation, on top of the standard ``account`` module.

Available now
-------------
* Financial reports, all printable as PDF and filterable by date range,
  journal, account and posted/all entries:

  - Trial Balance — initial balance, period movement and closing balance
    per account
  - General Ledger — every entry per account with a running balance
  - Balance Sheet — assets, liabilities and equity as of a date, with
    previous-year and current-year earnings reclassified into equity
  - Profit & Loss — income, cost of revenue and expenses, with gross and
    net profit
  - Cash Flow Statement — operating, investing and financing activities,
    derived from the counterpart of every entry that touched cash
  - Aged Partner Balance — receivable or payable, bucketed by days overdue
  - Tax Report — base and tax amounts per sales and purchase tax

* Asset management — straight-line and declining-balance depreciation boards,
  posted to journal entries manually or by a scheduled action, plus disposal
  (sale or scrap, with gain/loss) and revaluation
* Deferred revenue and deferred expense, sharing the same board mechanics
* Customer follow-up levels, with a reminder posted to the partner's chatter

Not included
------------
* Bank statement reconciliation widget

This module is an independent implementation. It is not affiliated with,
endorsed by, or a redistribution of Odoo S.A.'s Enterprise edition.
""",
    "author": "Scalebox For Digital Services",
    "maintainer": "Scalebox For Digital Services",
    "website": "https://scalebox.scbox.pro",
    # OPL-1 (Odoo Proprietary License) rather than LGPL-3: LGPL lets anyone
    # redistribute the module for free, which cannot coexist with selling it.
    "license": "OPL-1",
    "price": 150.00,
    "currency": "USD",
    "support": "saifnasr100.sn@gmail.com",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/scalebox_accounting_security.xml",
        "data/ir_cron_data.xml",
        "report/report_templates.xml",
        "report/statement_templates.xml",
        "report/analysis_templates.xml",
        "report/report_actions.xml",
        "wizard/financial_report_wizard_views.xml",
        "wizard/asset_wizard_views.xml",
        "views/account_asset_views.xml",
        "views/account_followup_views.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
