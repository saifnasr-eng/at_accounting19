# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AtAccountAsset(models.Model):
    _name = "at.account.asset"
    _description = "Asset / Deferred Entry"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(required=True, tracking=True)
    asset_type = fields.Selection(
        [
            ("purchase", "Fixed Asset"),
            ("sale", "Deferred Revenue"),
            ("expense", "Deferred Expense"),
        ],
        required=True,
        default="purchase",
        tracking=True,
        help="Fixed assets depreciate. Deferred revenue and deferred expense "
             "spread an already-recorded amount over future periods; the "
             "mechanics are identical, only the accounts differ.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
    )

    original_value = fields.Monetary(
        string="Original Value",
        required=True,
        tracking=True,
    )
    salvage_value = fields.Monetary(
        string="Salvage Value",
        default=0.0,
        help="Amount never depreciated, kept as the residual book value.",
    )
    depreciable_value = fields.Monetary(
        string="Depreciable Value",
        compute="_compute_depreciable_value",
        store=True,
    )
    value_depreciated = fields.Monetary(
        string="Depreciated",
        compute="_compute_amounts",
        store=True,
    )
    value_residual = fields.Monetary(
        string="Book Value",
        compute="_compute_amounts",
        store=True,
    )

    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Date of the first depreciation entry.",
    )
    method_number = fields.Integer(
        string="Number of Entries",
        required=True,
        default=12,
        tracking=True,
    )
    method_period = fields.Selection(
        [
            ("1", "Monthly"),
            ("3", "Quarterly"),
            ("12", "Yearly"),
        ],
        string="Period Length",
        required=True,
        default="1",
    )
    method = fields.Selection(
        [
            ("linear", "Straight Line"),
            ("degressive", "Declining Balance"),
        ],
        string="Method",
        required=True,
        default="linear",
        tracking=True,
    )
    method_progress_factor = fields.Float(
        string="Declining Factor",
        default=0.3,
        help="Share of the remaining book value written off each period.",
    )

    account_asset_id = fields.Many2one(
        "account.account",
        string="Fixed Asset Account",
        required=True,
        help="Account holding the asset's gross value. Credited as it "
             "depreciates.",
    )
    account_depreciation_id = fields.Many2one(
        "account.account",
        string="Depreciation Account",
        required=True,
        help="Counterpart of the asset account. Usually accumulated "
             "depreciation, or the revenue account for deferred revenue.",
    )
    account_expense_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        required=True,
        help="Where the periodic charge lands: depreciation expense, or the "
             "recognised revenue account.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', '=', 'general')]",
    )

    depreciation_line_ids = fields.One2many(
        "at.account.asset.line",
        "asset_id",
        string="Depreciation Board",
        copy=False,
    )
    entry_count = fields.Integer(compute="_compute_entry_count")

    @api.depends("original_value", "salvage_value")
    def _compute_depreciable_value(self):
        for asset in self:
            asset.depreciable_value = asset.original_value - asset.salvage_value

    @api.depends(
        "depreciation_line_ids.amount",
        "depreciation_line_ids.move_posted",
        "original_value",
    )
    def _compute_amounts(self):
        for asset in self:
            posted = asset.depreciation_line_ids.filtered("move_posted")
            asset.value_depreciated = sum(posted.mapped("amount"))
            asset.value_residual = asset.original_value - asset.value_depreciated

    @api.depends("depreciation_line_ids.move_id")
    def _compute_entry_count(self):
        for asset in self:
            asset.entry_count = len(
                asset.depreciation_line_ids.filtered("move_id")
            )

    @api.constrains("original_value", "salvage_value", "method_number")
    def _check_values(self):
        for asset in self:
            if asset.original_value <= 0:
                raise ValidationError(_("The original value must be positive."))
            if asset.salvage_value < 0:
                raise ValidationError(_("The salvage value cannot be negative."))
            if asset.salvage_value >= asset.original_value:
                raise ValidationError(
                    _("The salvage value must be below the original value.")
                )
            if asset.method_number <= 0:
                raise ValidationError(
                    _("The number of entries must be at least one.")
                )

    @api.constrains("method_progress_factor", "method")
    def _check_progress_factor(self):
        for asset in self:
            if asset.method == "degressive" and not (
                0 < asset.method_progress_factor < 1
            ):
                raise ValidationError(
                    _("The declining factor must be between 0 and 1.")
                )

    def _compute_board_amounts(self):
        """Return the amount for each period, as a list.

        Straight line splits the depreciable value evenly. Declining balance
        takes a fixed share of the remaining book value, but switches to the
        straight-line amount once that becomes larger, which is what stops a
        declining asset from never reaching its salvage value. The last period
        absorbs any rounding difference so the board always totals exactly.
        """
        self.ensure_one()
        currency = self.currency_id
        total = self.depreciable_value
        periods = self.method_number

        amounts = []
        remaining = total
        for index in range(periods):
            periods_left = periods - index
            linear_amount = currency.round(remaining / periods_left)

            if self.method == "degressive":
                degressive_amount = currency.round(
                    remaining * self.method_progress_factor
                )
                amount = max(linear_amount, degressive_amount)
            else:
                amount = linear_amount

            if index == periods - 1:
                amount = remaining
            amount = min(amount, remaining)

            amounts.append(amount)
            remaining = currency.round(remaining - amount)

        return amounts

    def _board_dates(self):
        self.ensure_one()
        months = int(self.method_period)
        return [
            self.date_start + relativedelta(months=months * index)
            for index in range(self.method_number)
        ]

    def compute_depreciation_board(self):
        """(Re)build the board, keeping any period already posted."""
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered("move_posted")
            if len(posted_lines) >= asset.method_number:
                raise UserError(
                    _("Every period of %s is already posted.", asset.display_name)
                )

            asset.depreciation_line_ids.filtered(
                lambda line: not line.move_posted
            ).unlink()

            amounts = asset._compute_board_amounts()
            dates = asset._board_dates()
            cumulative = sum(posted_lines.mapped("amount"))

            values = []
            for index, (amount, date) in enumerate(zip(amounts, dates), start=1):
                if index <= len(posted_lines):
                    continue
                cumulative += amount
                values.append({
                    "asset_id": asset.id,
                    "sequence": index,
                    "date": date,
                    "amount": amount,
                    "depreciated_value": cumulative,
                    "remaining_value": asset.original_value - cumulative,
                })
            self.env["at.account.asset.line"].create(values)
        return True

    def action_confirm(self):
        for asset in self:
            if asset.state != "draft":
                raise UserError(
                    _("Only a draft asset can be confirmed.")
                )
            if not asset.depreciation_line_ids:
                asset.compute_depreciation_board()
            asset.state = "running"
        return True

    def action_set_to_draft(self):
        for asset in self:
            if asset.depreciation_line_ids.filtered("move_posted"):
                raise UserError(
                    _("%s already has posted entries and cannot go back to "
                      "draft. Cancel it instead.", asset.display_name)
                )
            asset.state = "draft"
        return True

    def action_cancel(self):
        for asset in self:
            asset.depreciation_line_ids.filtered(
                lambda line: not line.move_posted
            ).unlink()
            asset.state = "cancelled"
        return True

    def action_view_entries(self):
        self.ensure_one()
        moves = self.depreciation_line_ids.mapped("move_id")
        return {
            "type": "ir.actions.act_window",
            "name": _("Depreciation Entries"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", moves.ids)],
        }

    @api.model
    def _cron_post_depreciation(self, date=None):
        """Post every depreciation line that has come due."""
        date = date or fields.Date.context_today(self)
        lines = self.env["at.account.asset.line"].search([
            ("move_id", "=", False),
            ("date", "<=", date),
            ("asset_id.state", "=", "running"),
        ])
        lines.create_move()
        return True
