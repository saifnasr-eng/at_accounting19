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

## Features

### Financial reports

Seven PDF reports from *Accounting → Reporting → AT Financial Reports*:

| Report | What it shows |
|---|---|
| Trial Balance | Initial balance, period debit/credit, closing balance per account |
| General Ledger | Every entry per account, with a running balance |
| Balance Sheet | Assets vs. liabilities + equity, as of a date |
| Profit & Loss | Income, cost of revenue, expenses, gross and net profit |
| Cash Flow | Operating, investing and financing activities |
| Aged Partner Balance | Receivable or payable, bucketed by days overdue |
| Tax Report | Base and tax amounts per sales and purchase tax |

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
- Cash flow has no stored category to read, so it is **derived**: every entry
  that touched cash is classified by what its non-cash lines hit. Whatever the
  mapping misses is shown as an explicit *Unclassified* line rather than
  silently dropped.
- The Balance Sheet and Cash Flow both **print a warning** when they fail to
  reconcile, rather than quietly showing a broken statement
- Section subtotals sum every row *including* rows hidden at zero, so the
  hide-zero option can never change a reported total
- Built entirely on `account.move.line` via the ORM — no Enterprise internals

### Assets and deferrals

*Accounting → AT Assets*. One model (`at.account.asset`) covers fixed assets,
deferred revenue and deferred expense — they differ only in which account is
debited and which is credited.

- **Straight line** and **declining balance** depreciation
- Declining balance switches to the straight-line amount once that is larger,
  which is what lets the asset actually reach its salvage value
- The final period absorbs rounding, so a board always totals its depreciable
  value to the cent
- Salvage value is held back and left as the residual book value
- Recomputing a board **keeps periods already posted** and rebuilds the rest
- Board lines with an entry cannot be deleted; an asset with posted entries
  cannot be reset to draft; an asset closes itself once fully posted
- A daily cron can post due periods. **It ships disabled** — nothing reaches
  the ledger until someone turns it on.

### Customer follow-ups

*Accounting → Configuration → Follow-up Levels*. Each level triggers once a
partner's oldest overdue invoice passes the number of days you set. The
reminder is posted to the partner's chatter, optionally emailing them.

## Layout

```
at_account_accountant/
├── __manifest__.py
├── models/            # assets, deferrals, follow-up levels
├── wizard/            # report option wizard + view
├── report/            # report engines (AbstractModel) + QWeb templates
├── views/             # asset and follow-up views, menus
├── security/          # access rights and multi-company record rules
├── data/              # depreciation cron (disabled by default)
├── tests/             # Odoo unit tests
└── static/description/index.html   # Odoo Apps listing page
```

## Install

```bash
git clone https://github.com/saifnasr-eng/at_accounting19.git
# point Odoo's addons_path at the clone, then:
odoo -d <db> -i at_account_accountant
```

## Testing status

**Nothing here has been run against a live Odoo 19 instance.** No Odoo runtime
was available where it was written. Treat first install as the real test.

What *has* been verified:

```bash
python3 tools/validate_module.py
```

Checks that the manifest parses, every declared data file exists, all Python
compiles, all XML is well-formed, and every internal xmlid, `report_name`,
report `AbstractModel`, `report_type` and `model_id` reference resolves to
something real. The depreciation board arithmetic was additionally replayed
outside Odoo across six cases (even splits, rounding remainders, declining
balance, single period) — every board totals its depreciable value to the cent.

What has **not** been verified, in rough order of risk:

1. **External references.** `account.menu_finance`,
   `account.menu_finance_reports`, `account.menu_finance_configuration`,
   `account.group_account_readonly` / `_user` / `_manager`,
   `base.view_partner_form`, `base.group_multi_company`. If any moved in 19.0,
   install fails loudly and the fix is a line each.
2. **API surface.** `_read_group` aggregate tuples, `compute_fiscalyear_dates`,
   `account_type` values, `<chatter/>`, and `list`-vs-`tree` view tags are all
   used as of the 17→19 conventions.
3. **The test suite itself** has never executed. Run it with:
   `odoo -d <db> -i at_account_accountant --test-enable --stop-after-init`

## Not built

- **Bank reconciliation widget.** This is a substantial OWL frontend
  component, not a model-and-view feature, and was out of reach here.
- **Asset disposal and revaluation.** The board handles the normal life of an
  asset; selling or revaluing one mid-life is not implemented.
- `static/description/icon.png` (128×128) and `banner.png`, required by Odoo
  Apps before publishing. Re-add the manifest's `images` key once they exist.
