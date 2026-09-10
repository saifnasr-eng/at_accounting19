# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AtAssetRevaluationWizard(models.TransientModel):
    _name = "at.asset.revaluation.wizard"
    _description = "Revalue an Asset"

    asset_id = fields.Many2one(
        "at.account.asset",
        string="Asset",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="asset_id.company_id", readonly=True)
    currency_id = fields.Many2one(related="asset_id.currency_id", readonly=True)

    date = fields.Date(
        string="Revaluation Date",
        required=True,
        default=fields.Date.context_today,
    )
    current_value = fields.Monetary(
        string="Current Book Value",
        compute="_compute_values",
    )
    new_value = fields.Monetary(
        string="New Book Value",
        required=True,
        help="What the asset is worth after revaluation. The remaining "
             "periods are rebuilt around this figure.",
    )
    difference = fields.Monetary(
        string="Adjustment",
        compute="_compute_values",
    )
    revaluation_account_id = fields.Many2one(
        "account.account",
        string="Revaluation Account",
        required=True,
        help="Counterpart of the adjustment, typically a revaluation reserve "
             "in equity or an impairment expense account.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', '=', 'general')]",
        default=lambda self: self._default_journal(),
    )

    @api.model
    def _default_journal(self):
        asset_id = self.env.context.get("active_id")
        if asset_id:
            return self.env["at.account.asset"].browse(asset_id).journal_id
        return False

    @api.depends("asset_id", "new_value")
    def _compute_values(self):
        for wizard in self:
            wizard.current_value = wizard.asset_id.value_residual
            wizard.difference = wizard.new_value - wizard.current_value

    def action_revalue(self):
        self.ensure_one()
        asset = self.asset_id

        if asset.state != "running":
            raise UserError(_("Only a running asset can be revalued."))
        if self.new_value < 0:
            raise UserError(_("The new book value cannot be negative."))

        difference = self.difference
        if self.currency_id.is_zero(difference):
            raise UserError(
                _("The new value matches the current book value; there is "
                  "nothing to adjust.")
            )

        label = _("Revaluation of %s", asset.name)
        # An increase debits the asset account; an impairment credits it, with
        # the revaluation account taking the other side either way.
        lines = [
            (0, 0, {
                "name": label,
                "account_id": asset.account_asset_id.id,
                "debit": difference if difference > 0 else 0.0,
                "credit": -difference if difference < 0 else 0.0,
            }),
            (0, 0, {
                "name": label,
                "account_id": self.revaluation_account_id.id,
                "debit": -difference if difference < 0 else 0.0,
                "credit": difference if difference > 0 else 0.0,
            }),
        ]

        move = self.env["account.move"].create({
            "journal_id": self.journal_id.id,
            "date": self.date,
            "ref": label,
            "company_id": asset.company_id.id,
            "line_ids": lines,
        })
        move.action_post()

        # Raise the gross value, then rebuild the unposted periods so the
        # remaining board depreciates the revalued figure.
        asset.original_value += difference
        asset.compute_depreciation_board()
        asset.message_post(body=_(
            "Revalued on %(date)s from %(old)s to %(new)s.",
            date=self.date,
            old=self.current_value,
            new=self.new_value,
        ))

        return {
            "type": "ir.actions.act_window",
            "name": _("Revaluation Entry"),
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
        }
