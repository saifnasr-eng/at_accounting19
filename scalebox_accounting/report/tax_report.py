# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.tools import float_is_zero


class ReportTax(models.AbstractModel):
    _name = "report.scalebox_accounting.report_tax"
    _description = "Tax Report"

    def _tax_lines(self, wizard, type_tax_use):
        """Return one row per tax: its base amount and its tax amount.

        Two different link fields are involved. A line carries ``tax_ids`` for
        the taxes applied *to* it (that is the base), while a line generated
        *by* a tax carries ``tax_line_id`` (that is the tax amount).
        """
        AccountMoveLine = self.env["account.move.line"]
        domain = wizard._period_domain()

        taxes = self.env["account.tax"].search([
            ("type_tax_use", "=", type_tax_use),
            ("company_id", "=", wizard.company_id.id),
        ])

        base_groups = dict(AccountMoveLine._read_group(
            domain + [("tax_ids", "in", taxes.ids)],
            groupby=["tax_ids"],
            aggregates=["balance:sum"],
        ))
        tax_groups = dict(AccountMoveLine._read_group(
            domain + [("tax_line_id", "in", taxes.ids)],
            groupby=["tax_line_id"],
            aggregates=["balance:sum"],
        ))

        # Sales taxes sit on credit-natured lines; flip so both sections read
        # as positive amounts.
        sign = -1.0 if type_tax_use == "sale" else 1.0

        rows = []
        for tax in taxes:
            base = base_groups.get(tax, 0.0) * sign
            amount = tax_groups.get(tax, 0.0) * sign
            rows.append({
                "name": tax.name,
                "base": base,
                "amount": amount,
            })

        if wizard.hide_zero_balance:
            precision = wizard.company_id.currency_id.rounding
            rows = [
                row for row in rows
                if not (
                    float_is_zero(row["base"], precision_rounding=precision)
                    and float_is_zero(row["amount"], precision_rounding=precision)
                )
            ]
        return sorted(rows, key=lambda row: row["name"])

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()

        sales = self._tax_lines(wizard, "sale")
        purchases = self._tax_lines(wizard, "purchase")

        sales_total = sum(row["amount"] for row in sales)
        purchases_total = sum(row["amount"] for row in purchases)

        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "currency": wizard.company_id.currency_id,
            "sections": [
                {"label": _("Sales Taxes"), "rows": sales, "total": sales_total},
                {"label": _("Purchase Taxes"), "rows": purchases,
                 "total": purchases_total},
            ],
            "net_tax": sales_total - purchases_total,
        }
