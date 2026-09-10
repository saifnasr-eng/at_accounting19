# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import float_is_zero

# Bucket labels, in the order _bucket_index returns. Kept as plain strings:
# translating at import time would bind to whatever language loaded the module.
AGE_BUCKET_LABELS = (
    "Not Due",
    "1 - 30",
    "31 - 60",
    "61 - 90",
    "91 - 120",
    "Older",
)


class ReportAgedPartner(models.AbstractModel):
    _name = "report.at_account_accountant.report_aged_partner"
    _description = "Aged Partner Balance Report"

    def _bucket_index(self, days_overdue):
        """Map days past the due date onto a bucket position."""
        if days_overdue <= 0:
            return 0
        if days_overdue <= 30:
            return 1
        if days_overdue <= 60:
            return 2
        if days_overdue <= 90:
            return 3
        if days_overdue <= 120:
            return 4
        return 5

    def _account_types(self, wizard):
        if wizard.aged_result_type == "payable":
            return ("liability_payable",)
        return ("asset_receivable",)

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()

        currency = wizard.company_id.currency_id
        precision = currency.rounding

        lines = self.env["account.move.line"].search(
            wizard._as_of_domain()
            + [
                ("account_id.account_type", "in", self._account_types(wizard)),
                ("amount_residual", "!=", 0.0),
            ],
            order="partner_id, date_maturity, id",
        )

        # Payables are credit-natured; flip so both statements read positive.
        sign = -1.0 if wizard.aged_result_type == "payable" else 1.0

        partners = {}
        for line in lines:
            due_date = line.date_maturity or line.date
            days_overdue = (wizard.date_to - due_date).days
            index = self._bucket_index(days_overdue)

            partner = line.partner_id
            key = partner.id or 0
            if key not in partners:
                partners[key] = {
                    "partner_name": partner.display_name or _("Unknown Partner"),
                    "buckets": [0.0] * len(AGE_BUCKET_LABELS),
                    "total": 0.0,
                }
            amount = line.amount_residual * sign
            partners[key]["buckets"][index] += amount
            partners[key]["total"] += amount

        rows = sorted(partners.values(), key=lambda row: row["partner_name"])
        if wizard.hide_zero_balance:
            rows = [
                row for row in rows
                if not float_is_zero(row["total"], precision_rounding=precision)
            ]

        totals = [0.0] * len(AGE_BUCKET_LABELS)
        for row in rows:
            for index, amount in enumerate(row["buckets"]):
                totals[index] += amount

        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "currency": currency,
            # env._ rather than _(): a list comprehension gets its own frame,
            # and the bare alias resolves the language by inspecting the caller's.
            "bucket_labels": [self.env._(label) for label in AGE_BUCKET_LABELS],
            "rows": rows,
            "bucket_totals": totals,
            "grand_total": sum(totals),
        }
