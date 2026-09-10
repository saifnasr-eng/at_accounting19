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

**Financial reports** — Trial Balance and General Ledger, printable as PDF from
*Accounting → Reporting → AT Financial Reports*.

- Initial balance, period debit/credit, and closing balance per account
- Filter by date range, journal, account, and posted-only vs. all entries
- Defaults to the company's current **fiscal year** (not the calendar year)
- Option to hide accounts that are flat at zero across the period
- Built entirely on `account.move.line` via the ORM — no Enterprise internals

## Planned scope

- Asset management (depreciation boards, disposal, revaluation)
- Deferred revenue and deferred expense
- Bank statement reconciliation widget
- Customer follow-up levels and reminder letters
- Remaining financial reports: Balance Sheet, Profit & Loss, Cash Flow,
  Aged Partner Balance, Tax Report

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
runtime was available where they were written. Statically validated: manifest
parses via `ast.literal_eval`, all Python compiles, all XML is well-formed, and
every internal xmlid / `report_name` / `AbstractModel` binding resolves. The
external references (`account.menu_finance_reports`,
`account.group_account_readonly`, `base.group_multi_company`) still need to be
confirmed on a real 19.0 install.

## Still to do

- Install on a 19.0 database and verify the two reports render
- `static/description/icon.png` (128×128) and `banner.png` — required by Odoo
  Apps, then re-add the `images` key to the manifest
- Feature models, views and access rules
