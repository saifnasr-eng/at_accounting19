# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import AtAccountingCase


@tagged("post_install", "-at_install")
class TestReportsRender(AtAccountingCase):
    """Every report must actually render, not just compute its values.

    A template can reference a key the engine does not return, or call a
    method that no longer exists, and no amount of testing _get_report_values
    will notice.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        move = cls.env["account.move"].create({
            "journal_id": cls.journal.id,
            "company_id": cls.company.id,
            "date": "2026-03-01",
            "line_ids": [
                (0, 0, {"name": "sale", "account_id": cls.account_cash.id,
                        "debit": 5000.0, "credit": 0.0}),
                (0, 0, {"name": "sale", "account_id": cls.account_income.id,
                        "debit": 0.0, "credit": 5000.0}),
            ],
        })
        move.action_post()

    def test_every_report_renders_html(self):
        wizard_model = self.env["at.financial.report.wizard"]
        report_model = self.env["ir.actions.report"]
        selection = dict(
            wizard_model._fields["report_type"]._description_selection(self.env)
        )

        for report_type in selection:
            with self.subTest(report_type=report_type):
                wizard = wizard_model.create({
                    "report_type": report_type,
                    "date_from": "2026-01-01",
                    "date_to": "2026-12-31",
                    "company_id": self.company.id,
                })
                action = wizard.with_context(
                    discard_logo_check=True
                ).print_report()
                html, _kind = report_model._render_qweb_html(
                    action["report_name"], wizard.ids
                )
                self.assertGreater(len(html), 500)
                self.assertIn(b"<table", html)
