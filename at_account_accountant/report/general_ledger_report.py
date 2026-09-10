# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import float_is_zero


class ReportGeneralLedger(models.AbstractModel):
    _name = "report.at_account_accountant.report_general_ledger"
    _description = "General Ledger Report"

    def _opening_by_account(self, wizard):
        groups = self.env["account.move.line"]._read_group(
            wizard._initial_domain(),
            groupby=["account_id"],
            aggregates=["balance:sum"],
        )
        return {account.id: balance for account, balance in groups}

    def _build_lines(self, wizard):
        opening_by_account = self._opening_by_account(wizard)

        move_lines = self.env["account.move.line"].search(
            wizard._period_domain(),
            order="account_id, date, move_id, id",
        )

        currency = wizard.company_id.currency_id
        precision = currency.rounding

        accounts = self.env["account.account"].browse(
            sorted(set(move_lines.account_id.ids) | set(opening_by_account))
        )

        report = []
        for account in accounts.sorted(lambda a: (a.code or "", a.name or "")):
            opening = opening_by_account.get(account.id, 0.0)
            account_lines = move_lines.filtered(
                lambda line, account=account: line.account_id == account
            )

            if wizard.hide_zero_balance and not account_lines and float_is_zero(
                opening, precision_rounding=precision
            ):
                continue

            running = opening
            entries = []
            for line in account_lines:
                running += line.balance
                entries.append({
                    "date": line.date,
                    "move_name": line.move_id.name,
                    "journal": line.journal_id.code,
                    "partner": line.partner_id.display_name or "",
                    "label": line.name or "",
                    "debit": line.debit,
                    "credit": line.credit,
                    "running_balance": running,
                })

            report.append({
                "account": account,
                "code": account.code,
                "name": account.name,
                "opening": opening,
                "entries": entries,
                "debit": sum(entry["debit"] for entry in entries),
                "credit": sum(entry["credit"] for entry in entries),
                "closing": running,
            })
        return report

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()
        accounts = self._build_lines(wizard)
        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "accounts": accounts,
            "currency": wizard.company_id.currency_id,
        }
