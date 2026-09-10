# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class AtAccountingCase(TransactionCase):
    """Shared fixtures for the module's tests.

    Everything runs inside a company created here rather than the database's
    own. The reports aggregate every entry a company has, so running them
    against a database carrying demo data would measure the demo ledger
    instead of the fixtures.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env["res.company"].create({"name": "AT Test Company"})
        cls.env.user.company_ids = [(4, cls.company.id)]
        cls.env.user.company_id = cls.company
        cls.env = cls.env(context=dict(
            cls.env.context, allowed_company_ids=cls.company.ids
        ))
        cls.currency = cls.company.currency_id

        cls.journal = cls.env["account.journal"].create({
            "name": "AT Test Journal",
            "code": "ATT",
            "type": "general",
            "company_id": cls.company.id,
        })

        cls.account_asset = cls._make_account("ATFA", "Fixed Assets", "asset_fixed")
        cls.account_depreciation = cls._make_account(
            "ATAD", "Accumulated Depreciation", "asset_fixed"
        )
        cls.account_expense = cls._make_account(
            "ATDE", "Depreciation Expense", "expense_depreciation"
        )
        cls.account_income = cls._make_account("ATIN", "Test Income", "income")
        cls.account_cash = cls._make_account("ATCA", "Test Cash", "asset_cash")

    @classmethod
    def _make_account(cls, code, name, account_type):
        return cls.env["account.account"].create({
            "code": code,
            "name": name,
            "account_type": account_type,
            "company_ids": [(6, 0, cls.company.ids)],
        })

    def _make_asset(self, **overrides):
        values = {
            "name": "Test Asset",
            "asset_type": "purchase",
            "original_value": 10000.0,
            "method_number": 10,
            "method_period": "1",
            "method": "linear",
            "date_start": "2026-01-01",
            "company_id": self.company.id,
            "journal_id": self.journal.id,
            "account_asset_id": self.account_asset.id,
            "account_depreciation_id": self.account_depreciation.id,
            "account_expense_id": self.account_expense.id,
        }
        values.update(overrides)
        return self.env["at.account.asset"].create(values)
