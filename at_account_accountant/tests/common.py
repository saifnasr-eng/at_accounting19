# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class AtAccountingCase(TransactionCase):
    """Shared fixtures: a journal and one account per type the tests need."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
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
            "journal_id": self.journal.id,
            "account_asset_id": self.account_asset.id,
            "account_depreciation_id": self.account_depreciation.id,
            "account_expense_id": self.account_expense.id,
        }
        values.update(overrides)
        return self.env["at.account.asset"].create(values)
