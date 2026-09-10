# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AtFinancialReportWizard(models.TransientModel):
    _name = "at.financial.report.wizard"
    _description = "Financial Report Options"

    report_type = fields.Selection(
        [
            ("trial_balance", "Trial Balance"),
            ("general_ledger", "General Ledger"),
            ("balance_sheet", "Balance Sheet"),
            ("profit_loss", "Profit & Loss"),
            ("cash_flow", "Cash Flow Statement"),
            ("aged_partner", "Aged Partner Balance"),
            ("tax_report", "Tax Report"),
        ],
        string="Report",
        required=True,
        default="trial_balance",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: self._default_fiscalyear_dates()["date_from"],
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        default=lambda self: self._default_fiscalyear_dates()["date_to"],
    )
    target_move = fields.Selection(
        [
            ("posted", "Posted Entries Only"),
            ("all", "All Entries"),
        ],
        string="Target Moves",
        required=True,
        default="posted",
    )
    journal_ids = fields.Many2many(
        "account.journal",
        string="Journals",
        help="Leave empty to include every journal.",
    )
    account_ids = fields.Many2many(
        "account.account",
        string="Accounts",
        help="Leave empty to include every account.",
    )
    aged_result_type = fields.Selection(
        [
            ("receivable", "Receivable"),
            ("payable", "Payable"),
        ],
        string="Aged Balance For",
        required=True,
        default="receivable",
    )
    hide_zero_balance = fields.Boolean(
        string="Hide Accounts at Zero",
        default=True,
        help="Skip accounts with no initial balance, no movement and no "
             "closing balance over the period.",
    )

    @api.model
    def _default_fiscalyear_dates(self):
        """Current fiscal year of the active company, not the calendar year."""
        today = fields.Date.context_today(self)
        return self.env.company.compute_fiscalyear_dates(today)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(
                    _("The start date must not be after the end date.")
                )

    def _base_domain(self):
        """Domain shared by the initial-balance and period queries."""
        self.ensure_one()
        domain = [("company_id", "=", self.company_id.id)]
        if self.target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "in", ("draft", "posted")))
        if self.journal_ids:
            domain.append(("journal_id", "in", self.journal_ids.ids))
        if self.account_ids:
            domain.append(("account_id", "in", self.account_ids.ids))
        return domain

    def _period_domain(self):
        return self._base_domain() + [
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]

    def _initial_domain(self):
        return self._base_domain() + [("date", "<", self.date_from)]

    def _as_of_domain(self):
        """Everything up to and including the end date.

        A balance sheet is a snapshot, not a period, so it ignores date_from
        and accumulates from the very first entry.
        """
        return self._base_domain() + [("date", "<=", self.date_to)]

    def _fiscalyear_start(self):
        """First day of the fiscal year containing the end date."""
        self.ensure_one()
        return self.company_id.compute_fiscalyear_dates(self.date_to)["date_from"]

    REPORT_ACTIONS = {
        "trial_balance": "scalebox_accounting.action_report_trial_balance",
        "general_ledger": "scalebox_accounting.action_report_general_ledger",
        "balance_sheet": "scalebox_accounting.action_report_balance_sheet",
        "profit_loss": "scalebox_accounting.action_report_profit_loss",
        "cash_flow": "scalebox_accounting.action_report_cash_flow",
        "aged_partner": "scalebox_accounting.action_report_aged_partner",
        "tax_report": "scalebox_accounting.action_report_tax",
    }

    def print_report(self):
        self.ensure_one()
        return self.env.ref(self.REPORT_ACTIONS[self.report_type]).report_action(self)
