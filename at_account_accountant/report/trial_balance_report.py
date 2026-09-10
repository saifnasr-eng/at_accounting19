# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import float_is_zero


class ReportTrialBalance(models.AbstractModel):
    _name = "report.at_account_accountant.report_trial_balance"
    _description = "Trial Balance Report"

    def _sum_by_account(self, domain):
        """Return {account_id: (debit, credit, balance)} for a domain."""
        groups = self.env["account.move.line"]._read_group(
            domain,
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum", "balance:sum"],
        )
        return {
            account.id: (debit, credit, balance)
            for account, debit, credit, balance in groups
        }

    def _build_lines(self, wizard):
        initial = self._sum_by_account(wizard._initial_domain())
        period = self._sum_by_account(wizard._period_domain())

        account_ids = set(initial) | set(period)
        if not account_ids:
            return []

        accounts = self.env["account.account"].browse(sorted(account_ids))
        currency = wizard.company_id.currency_id
        precision = currency.rounding

        lines = []
        for account in accounts.sorted(lambda a: (a.code or "", a.name or "")):
            opening = initial.get(account.id, (0.0, 0.0, 0.0))[2]
            debit, credit, movement = period.get(account.id, (0.0, 0.0, 0.0))
            closing = opening + movement

            if wizard.hide_zero_balance and all(
                float_is_zero(value, precision_rounding=precision)
                for value in (opening, debit, credit, closing)
            ):
                continue

            lines.append({
                "account": account,
                "code": account.code,
                "name": account.name,
                "opening": opening,
                "debit": debit,
                "credit": credit,
                "closing": closing,
            })
        return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()
        lines = self._build_lines(wizard)
        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "lines": lines,
            "currency": wizard.company_id.currency_id,
            "totals": {
                "opening": sum(line["opening"] for line in lines),
                "debit": sum(line["debit"] for line in lines),
                "credit": sum(line["credit"] for line in lines),
                "closing": sum(line["closing"] for line in lines),
            },
        }
