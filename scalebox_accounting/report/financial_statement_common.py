# -*- coding: utf-8 -*-
"""Shared building blocks for the Balance Sheet and Profit & Loss reports.

Both statements group ``account.move.line`` by the account's ``account_type``
rather than by individual account, so the section layout below is the single
place where Odoo's account types are mapped onto statement lines.
"""
from odoo import models
from odoo.tools import float_is_zero

# Profit & loss account types, needed by the balance sheet too: retained
# earnings are derived from them rather than stored on an account.
INCOME_TYPES = ("income", "income_other")
EXPENSE_TYPES = ("expense", "expense_depreciation", "expense_direct_cost")
PL_TYPES = INCOME_TYPES + EXPENSE_TYPES


class AtFinancialStatementCommon(models.AbstractModel):
    _name = "at.financial.statement.common"
    _description = "Shared helpers for financial statements"

    def _sum_by_account_type(self, domain):
        """Return {account_type: signed balance} for a domain.

        Balance is debit - credit, so asset and expense totals come out
        positive while liability, equity and income totals come out negative.
        """
        groups = self.env["account.move.line"]._read_group(
            domain,
            groupby=["account_id"],
            aggregates=["balance:sum"],
        )
        totals = {}
        for account, balance in groups:
            account_type = account.account_type
            totals[account_type] = totals.get(account_type, 0.0) + balance
        return totals

    def _sum_for_types(self, totals, account_types):
        return sum(totals.get(account_type, 0.0) for account_type in account_types)

    def _build_section(self, label, rows, currency, hide_zero):
        """Assemble one statement section from (label, amount) rows.

        The section total sums every row, including any hidden at zero, so
        hiding empty lines can never change the reported total.
        """
        precision = currency.rounding
        visible = [
            {"label": row_label, "amount": amount}
            for row_label, amount in rows
            if not (hide_zero and float_is_zero(amount, precision_rounding=precision))
        ]
        return {
            "label": label,
            "rows": visible,
            "total": sum(amount for _row_label, amount in rows),
            # A section with nothing left to show is dropped by the template
            # rather than printing a heading above a lone zero total.
            "visible": bool(visible),
        }
