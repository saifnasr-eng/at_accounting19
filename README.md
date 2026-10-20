# at_accounting19

**AT Full Accounting** — Enterprise accounting features for Odoo 17 Community.

Technical name: `scalebox_accounting` · Version: `17.0.1.0.0` · License: OPL-1 · Price: $150 USD

> This branch targets **Odoo 17.0 Community**. The 19.0 series lives on `main`.

## What this is

Adds the accounting capabilities that ship with the Enterprise edition of Odoo
to a Community installation, on top of the standard `account` module.

The technical name mirrors Odoo Enterprise's own `account_accountant` module so
its purpose is obvious to any Odoo developer. The original name `at_accounting`
is already taken on Odoo Apps.

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

**Disposal** (sale or scrap) removes the gross cost and the depreciation booked
so far, records any proceeds, and sends the difference to a gain/loss account.
**Revaluation** posts the adjustment against a reserve or impairment account,
raises the gross value, and rebuilds the periods not yet posted. Both void the
board's remaining periods where appropriate.

> The module never books the *purchase* itself — that comes from a vendor bill
> or a manual entry. It books depreciation, revaluation and disposal.

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
scalebox_accounting/
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
odoo -d <db> -i scalebox_accounting
```

## Testing status

Verified on a real **Odoo 17.0 FINAL** install (PostgreSQL 16, wkhtmltopdf
0.12.6):

| Check | Result |
|---|---|
| Install with a chart of accounts and demo data | clean, exits 0 |
| Install on an empty database (no demo) | clean, exits 0 |
| Unit tests | **30/30 pass**, on both databases |
| All 7 reports render to HTML | pass, 25–123 KB each |
| All 7 reports render to **PDF** | pass, 16–38 KB each |
| `ir_module_module` records | `scalebox_accounting \| 17.0.1.0.0 \| OPL-1 \| installed` |

On a 47-account, 68-entry ledger the statements reconcile:

| Check | Result |
|---|---|
| Balance sheet: assets vs. liabilities + equity | 2,500.00 vs. 2,500.00 — difference **0.00** |
| Trial balance: debits vs. credits | 302,673.57 vs. 302,673.57 — difference **0.00** |
| Cash flow: classified movements vs. change in cash | reconciles, **0.00** unclassified |

Static checks, no Odoo runtime needed:

```bash
python3 tools/validate_module.py
```

Reproducing the live run:

```bash
odoo -d <db> --addons-path=<odoo17>/addons,<clone-parent> \
     -i scalebox_accounting --stop-after-init
odoo -d <db> --addons-path=... -u scalebox_accounting \
     --test-enable --test-tags /scalebox_accounting --stop-after-init
```

## What the 19 → 17 downgrade changed

Five API differences, each confirmed against the Odoo 17 source rather than
assumed:

| Area | 19.0 | 17.0 |
|---|---|---|
| List view tag | `<list>` | `<tree>` — and `view_mode` reads `tree,form` |
| Chatter | `<chatter/>` | an explicit `<div class="oe_chatter">` with the follower, activity and message fields |
| Translation in a comprehension | `self.env._()` | `env._` does not exist; `_()` is called in a plain loop so the frame still carries `self` |
| `account.account` company | `company_ids` (many2many) | `company_id` (many2one) — affects the test fixtures |
| `ir.cron.numbercall` | removed | present, and its default of **1** would run the job once and stop, so it is set to `-1` |

Everything else carried over unchanged: `_read_group`'s aggregate signature,
`compute_fiscalyear_dates`, the `account_type` values, `parent_state`,
`column_invisible`, `web_ribbon`, and the `invisible="<expr>"` view syntax all
behave the same in 17.0.

## Not built

- **Bank reconciliation widget.** This is a substantial OWL frontend
  component rather than a model-and-view feature, and is the one part of the
  original scope deliberately left out. Community installs keep Odoo's own
  statement reconciliation.

## Licensing

Published under **OPL-1** (Odoo Proprietary License v1.0), not LGPL-3. LGPL
permits anyone to redistribute the module for free, which is incompatible with
selling it. The manifest carries `price` and `currency` so Odoo Apps lists it
at $150 USD.

The `LICENSE` file must contain the official OPL-1 text from
<https://www.odoo.com/documentation/17.0/legal/licenses.html> — it could not be
fetched from the build environment, so add it before publishing.

## Before publishing to Odoo Apps

- Add the `LICENSE` file with the official OPL-1 text
- Confirm `scalebox_accounting` is free at
  `https://apps.odoo.com/apps/modules/17.0/scalebox_accounting/` (404 means
  available). This could not be checked from the build environment.
- The icon (`static/description/icon.png`, 128×128) and banner
  (`static/description/banner.png`, 1200×400) are in place and the manifest's
  `images` key points at the banner.
