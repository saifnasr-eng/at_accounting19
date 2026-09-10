# at_accounting19

**AT Full Accounting** — Enterprise accounting features for Odoo 19 Community.

Technical name: `at_account_accountant` · Version: `19.0.1.0.0` · License: LGPL-3

## What this is

Adds the accounting capabilities that ship with the Enterprise edition of Odoo
to a Community installation, on top of the standard `account` module.

The technical name mirrors Odoo Enterprise's own `account_accountant` module so
its purpose is obvious to any Odoo developer. The original name `at_accounting`
is already taken on Odoo Apps for 19.0.

> This module is an independent implementation. It is not affiliated with,
> endorsed by, or a redistribution of Odoo S.A.'s Enterprise edition.

## Available now

**Financial reports** — four PDF reports from
*Accounting → Reporting → AT Financial Reports*:

| Report | What it shows |
|---|---|
| Trial Balance | Initial balance, period debit/credit, closing balance per account |
| General Ledger | Every entry per account, with a running balance |
| Balance Sheet | Assets vs. liabilities + equity, as of a date |
| Profit & Loss | Income, cost of revenue, expenses, gross and net profit |

Shared options: date range, journal filter, account filter, posted-only vs.
all entries, and hiding accounts that sit at zero.

Design notes:

- Defaults to the company's current **fiscal year**, not the calendar year
- The Balance Sheet is a **snapshot**: it ignores the start date and
  accumulates from the first entry up to the end date
- Odoo posts no year-end closing entry, so profit left sitting in income and
  expense accounts is **reclassified into equity** — split into *Previous
  Years Earnings* (before the fiscal year of the end date) and *Current Year
  Earnings*. Any `equity_unaffected` balance is shown alongside, so a company
  that does post closing entries is not double-counted.
- `off_balance` accounts are excluded from the Balance Sheet
- The Balance Sheet prints a warning when assets do not equal liabilities plus
  equity, rather than quietly showing a broken statement
- Built entirely on `account.move.line` via the ORM — no Enterprise internals

## Planned scope

- Asset management (depreciation boards, disposal, revaluation)
- Deferred revenue and deferred expense
- Bank statement reconciliation widget
- Customer follow-up levels and reminder letters
- Remaining financial reports: Cash Flow, Aged Partner Balance, Tax Report

## Layout

```
at_account_accountant/
├── __manifest__.py
├── __init__.py
├── models/            # feature models, imported from models/__init__.py
├── wizard/            # report option wizards + their views
├── report/            # report engines (AbstractModel) + QWeb templates
├── views/             # XML views, listed in the manifest "data" key
├── security/          # ir.model.access.csv and record rules
└── static/description/index.html   # Odoo Apps listing page
```

## Install

```bash
git clone https://github.com/saifnasr-eng/at_accounting19.git
# point Odoo's addons_path at the clone, then:
odoo -d <db> -i at_account_accountant
```

## Testing status

The reports have **not** been run against a live Odoo 19 instance yet — no Odoo
runtime was available where they were written. Run the static checks with:

```bash
python3 tools/validate_module.py
```

That verifies the manifest parses, every declared data file exists, all Python
compiles, all XML is well-formed, and every internal xmlid, `report_name`,
report `AbstractModel` and `report_type` resolves to something real. The
external references (`account.menu_finance_reports`,
`account.group_account_readonly`, `base.group_multi_company`) still need to be
confirmed on a real 19.0 install.

## Still to do

- Install on a 19.0 database and verify the two reports render
- `static/description/icon.png` (128×128) and `banner.png` — required by Odoo
  Apps, then re-add the `images` key to the manifest
- Feature models, views and access rules
