# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AtAssetDisposalWizard(models.TransientModel):
    _name = "at.asset.disposal.wizard"
    _description = "Dispose of an Asset"

    asset_id = fields.Many2one(
        "at.account.asset",
        string="Asset",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="asset_id.company_id", readonly=True)
    currency_id = fields.Many2one(related="asset_id.currency_id", readonly=True)

    disposal_type = fields.Selection(
        [
            ("sale", "Sold"),
            ("scrap", "Scrapped"),
        ],
        required=True,
        default="sale",
    )
    date = fields.Date(
        string="Disposal Date",
        required=True,
        default=fields.Date.context_today,
    )
    proceeds = fields.Monetary(
        string="Sale Proceeds",
        default=0.0,
        help="Amount received. Zero for a scrapped asset.",
    )
    proceeds_account_id = fields.Many2one(
        "account.account",
        string="Proceeds Account",
        help="Where the money received lands, typically a receivable or bank "
             "account. Required when there are proceeds.",
    )
    gain_loss_account_id = fields.Many2one(
        "account.account",
        string="Gain / Loss Account",
        required=True,
        help="Takes the difference between the proceeds and the asset's "
             "remaining book value.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', '=', 'general')]",
        default=lambda self: self._default_journal(),
    )

    book_value = fields.Monetary(
        string="Book Value at Disposal",
        compute="_compute_book_value",
    )
    gain_loss = fields.Monetary(
        string="Gain / (Loss)",
        compute="_compute_book_value",
    )

    @api.model
    def _default_journal(self):
        asset_id = self.env.context.get("active_id")
        if asset_id:
            return self.env["at.account.asset"].browse(asset_id).journal_id
        return False

    @api.depends("asset_id", "proceeds")
    def _compute_book_value(self):
        for wizard in self:
            wizard.book_value = wizard.asset_id.value_residual
            wizard.gain_loss = wizard.proceeds - wizard.book_value

    @api.constrains("proceeds", "proceeds_account_id")
    def _check_proceeds_account(self):
        for wizard in self:
            if wizard.proceeds and not wizard.proceeds_account_id:
                raise UserError(
                    _("Set a proceeds account, or leave the proceeds at zero.")
                )

    def _prepare_disposal_lines(self):
        """Build the entry that takes the asset off the books.

        Gross cost is credited off the asset account and the depreciation
        booked so far is debited back off its counterpart, which together
        remove the asset. The proceeds are debited, and whatever is left over
        lands in the gain/loss account.
        """
        self.ensure_one()
        asset = self.asset_id
        label = _("Disposal of %s", asset.name)

        lines = [
            (0, 0, {
                "name": label,
                "account_id": asset.account_asset_id.id,
                "debit": 0.0,
                "credit": asset.original_value,
            }),
        ]

        if asset.value_depreciated:
            lines.append((0, 0, {
                "name": label,
                "account_id": asset.account_depreciation_id.id,
                "debit": asset.value_depreciated,
                "credit": 0.0,
            }))

        if self.proceeds:
            lines.append((0, 0, {
                "name": label,
                "account_id": self.proceeds_account_id.id,
                "debit": self.proceeds,
                "credit": 0.0,
            }))

        # Whatever the two sides do not already cover is the gain or loss.
        gain_loss = self.gain_loss
        if not self.currency_id.is_zero(gain_loss):
            lines.append((0, 0, {
                "name": label,
                "account_id": self.gain_loss_account_id.id,
                "debit": -gain_loss if gain_loss < 0 else 0.0,
                "credit": gain_loss if gain_loss > 0 else 0.0,
            }))

        return lines

    def action_dispose(self):
        self.ensure_one()
        asset = self.asset_id

        if asset.state not in ("running", "closed"):
            raise UserError(
                _("Only a running or closed asset can be disposed of.")
            )

        move = self.env["account.move"].create({
            "journal_id": self.journal_id.id,
            "date": self.date,
            "ref": _("Disposal of %s", asset.name),
            "company_id": asset.company_id.id,
            "line_ids": self._prepare_disposal_lines(),
        })
        move.action_post()

        # Future periods are void once the asset is gone.
        asset.depreciation_line_ids.filtered(
            lambda line: not line.move_posted
        ).unlink()
        asset.write({
            "state": "disposed",
            "disposal_move_id": move.id,
            "disposal_date": self.date,
            "disposal_type": self.disposal_type,
        })
        asset.message_post(body=_(
            "Disposed on %(date)s. Book value %(book)s, proceeds %(proceeds)s.",
            date=self.date,
            book=self.book_value,
            proceeds=self.proceeds,
        ))

        return {
            "type": "ir.actions.act_window",
            "name": _("Disposal Entry"),
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
        }
