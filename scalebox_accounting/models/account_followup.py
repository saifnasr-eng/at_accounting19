# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AtFollowupLevel(models.Model):
    _name = "at.followup.level"
    _description = "Follow-up Level"
    _order = "delay"

    name = fields.Char(required=True)
    delay = fields.Integer(
        string="Days Overdue",
        required=True,
        help="A partner reaches this level once their oldest overdue invoice "
             "is at least this many days past due.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    subject = fields.Char(default="Payment Reminder")
    body = fields.Html(
        string="Reminder Body",
        translate=True,
        help="Shown above the list of overdue invoices in the reminder.",
    )
    send_email = fields.Boolean(string="Send Email", default=True)

    @api.constrains("delay", "company_id")
    def _check_delay_unique(self):
        """Enforced in Python rather than as a SQL constraint, whose
        declaration style has shifted between Odoo versions."""
        for level in self:
            duplicate = self.search_count([
                ("id", "!=", level.id),
                ("delay", "=", level.delay),
                ("company_id", "=", level.company_id.id),
            ])
            if duplicate:
                raise ValidationError(_(
                    "Another follow-up level already triggers at %s days "
                    "overdue.", level.delay
                ))

    @api.constrains("delay")
    def _check_delay_positive(self):
        for level in self:
            if level.delay < 0:
                raise ValidationError(
                    _("Days overdue cannot be negative.")
                )


class ResPartnerFollowup(models.Model):
    _inherit = "res.partner"

    at_followup_level_id = fields.Many2one(
        "at.followup.level",
        string="Follow-up Level",
        compute="_compute_followup",
        help="Level matching the partner's oldest overdue invoice.",
    )
    at_followup_currency_id = fields.Many2one(
        "res.currency",
        string="Follow-up Currency",
        compute="_compute_at_followup_currency",
        help="Company currency, resolved here rather than relying on a "
             "currency field whose presence on res.partner varies.",
    )
    at_followup_amount_due = fields.Monetary(
        string="Total Overdue",
        compute="_compute_followup",
        currency_field="at_followup_currency_id",
    )
    at_followup_next_date = fields.Date(
        string="Next Reminder",
        copy=False,
        help="Set after a reminder is sent, to hold off the next one.",
    )

    def _overdue_lines(self, date=None):
        """Unpaid receivable lines already past their due date."""
        self.ensure_one()
        date = date or fields.Date.context_today(self)
        return self.env["account.move.line"].search([
            ("partner_id", "=", self.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", "asset_receivable"),
            ("amount_residual", "!=", 0.0),
            ("date_maturity", "<", date),
        ])

    @api.depends_context("company")
    def _compute_at_followup_currency(self):
        for partner in self:
            partner.at_followup_currency_id = self.env.company.currency_id

    @api.depends_context("company")
    def _compute_followup(self):
        levels = self.env["at.followup.level"].search([
            ("company_id", "=", self.env.company.id),
        ])
        today = fields.Date.context_today(self)

        for partner in self:
            lines = partner._overdue_lines(today)
            partner.at_followup_amount_due = sum(lines.mapped("amount_residual"))

            if not lines:
                partner.at_followup_level_id = False
                continue

            oldest = min(lines.mapped("date_maturity"))
            days_overdue = (today - oldest).days
            # The highest level the partner has actually reached.
            matching = levels.filtered(lambda lvl: lvl.delay <= days_overdue)
            partner.at_followup_level_id = matching[-1] if matching else False

    def action_at_send_followup(self):
        """Post the reminder in the partner's chatter, optionally by email."""
        for partner in self:
            level = partner.at_followup_level_id
            if not level:
                continue

            lines = partner._overdue_lines()
            body = level.body or ""
            body += "<ul>"
            for line in lines:
                body += _(
                    "<li>%(move)s — due %(due)s — %(amount)s</li>",
                    move=line.move_id.name,
                    due=line.date_maturity,
                    amount=line.amount_residual,
                )
            body += "</ul>"

            partner.message_post(
                body=body,
                subject=level.subject,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                partner_ids=partner.ids if level.send_email else [],
            )
            partner.at_followup_next_date = fields.Date.add(
                fields.Date.context_today(partner), days=7
            )
        return True
