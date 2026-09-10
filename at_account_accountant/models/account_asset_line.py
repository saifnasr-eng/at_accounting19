# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AtAccountAssetLine(models.Model):
    _name = "at.account.asset.line"
    _description = "Depreciation Board Line"
    _order = "asset_id, sequence, date"

    asset_id = fields.Many2one(
        "at.account.asset",
        string="Asset",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(required=True, default=1)
    company_id = fields.Many2one(
        related="asset_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="asset_id.currency_id",
        readonly=True,
    )

    date = fields.Date(string="Depreciation Date", required=True)
    amount = fields.Monetary(string="Depreciation", required=True)
    depreciated_value = fields.Monetary(string="Cumulative Depreciation")
    remaining_value = fields.Monetary(string="Remaining Value")

    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    move_posted = fields.Boolean(
        string="Posted",
        compute="_compute_move_posted",
        store=True,
    )

    @api.depends("move_id", "move_id.state")
    def _compute_move_posted(self):
        for line in self:
            line.move_posted = bool(line.move_id) and line.move_id.state == "posted"

    def _prepare_move_lines(self):
        """Build the two balanced lines for one period.

        A fixed asset credits accumulated depreciation and debits the expense.
        Deferred revenue runs the other way: it debits the deferral account
        held as a liability and credits the revenue account. Same two accounts
        in both cases, opposite signs.
        """
        self.ensure_one()
        asset = self.asset_id
        label = _("%(asset)s - %(date)s", asset=asset.name, date=self.date)

        if asset.asset_type == "sale":
            debit_account = asset.account_depreciation_id
            credit_account = asset.account_expense_id
        else:
            debit_account = asset.account_expense_id
            credit_account = asset.account_depreciation_id

        return [
            (0, 0, {
                "name": label,
                "account_id": debit_account.id,
                "debit": self.amount,
                "credit": 0.0,
            }),
            (0, 0, {
                "name": label,
                "account_id": credit_account.id,
                "debit": 0.0,
                "credit": self.amount,
            }),
        ]

    def create_move(self, post=True):
        """Create (and by default post) the journal entry for these lines."""
        moves = self.env["account.move"]
        for line in self:
            if line.move_id:
                raise UserError(
                    _("A journal entry already exists for %s.", line.display_name)
                )
            if line.asset_id.state != "running":
                raise UserError(
                    _("%s is not running, so its board cannot be posted.",
                      line.asset_id.display_name)
                )

            move = self.env["account.move"].create({
                "journal_id": line.asset_id.journal_id.id,
                "date": line.date,
                "ref": line.asset_id.name,
                "company_id": line.asset_id.company_id.id,
                "line_ids": line._prepare_move_lines(),
            })
            line.move_id = move
            moves |= move

        if post:
            moves.action_post()

        # An asset whose board is fully posted has nothing left to do.
        for asset in self.asset_id:
            if len(asset.depreciation_line_ids.filtered("move_posted")) >= (
                asset.method_number
            ):
                asset.state = "closed"

        return moves

    def action_create_move(self):
        return self.create_move()

    def unlink(self):
        if self.filtered("move_id"):
            raise UserError(
                _("A board line with a journal entry cannot be deleted. "
                  "Reverse or delete the entry first.")
            )
        return super().unlink()
