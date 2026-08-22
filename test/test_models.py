import math
import os
import sys
import unittest
import contextlib
import io

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from models import (
    AbstractAccount,
    BankAccount,
    SavingsAccount,
    PremiumAccount,
    InvestmentAccount,
    Currency,
    AccountStatus,
)
from exceptions import (
    AccountClosedError,
    AccountFrozenError,
    InsufficientFundsError,
    InvalidOperationError,
    MinBalanceViolationError,
    OverdraftLimitExceededError,
)


class QuietOutput:
    """Глушит print из моделей, чтобы отчет тестов был читаемым."""

    def setUp(self):
        self._buffer = io.StringIO()
        self._redirect = contextlib.redirect_stdout(self._buffer)
        self._redirect.__enter__()
        super().setUp()

    def tearDown(self):
        self._redirect.__exit__(None, None, None)
        super().tearDown()


class HierarchyTest(unittest.TestCase):
    """Проверки правильной иерархии классов счетов."""

    def test_abstract_account_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            AbstractAccount("Иван")

    def test_subclass_without_abstract_methods_cannot_be_instantiated(self):
        class BrokenAccount(AbstractAccount):
            pass

        with self.assertRaises(TypeError):
            BrokenAccount("Иван")

    def test_all_accounts_are_abstract_account_instances(self):
        accounts = [
            BankAccount("A"),
            SavingsAccount("B"),
            PremiumAccount("C"),
            InvestmentAccount("D"),
        ]
        for acc in accounts:
            self.assertIsInstance(acc, AbstractAccount)
            self.assertIsInstance(acc, BankAccount)

    def test_bank_account_is_direct_child_of_abstract_account(self):
        self.assertIs(BankAccount.__mro__[1], AbstractAccount)

    def test_specific_accounts_are_direct_children_of_bank_account(self):
        for cls in (SavingsAccount, PremiumAccount, InvestmentAccount):
            self.assertIs(cls.__mro__[1], BankAccount)


class BankAccountCreationTest(QuietOutput, unittest.TestCase):
    def test_default_creation(self):
        acc = BankAccount("Иван Иванов")
        self.assertEqual(acc.owner, "Иван Иванов")
        self.assertEqual(acc.currency, Currency.RUB)
        self.assertEqual(acc.status, AccountStatus.ACTIVE)
        self.assertEqual(acc.balance, 0.0)
        self.assertTrue(acc.account_id)

    def test_custom_account_id_and_status(self):
        acc = BankAccount("Иван", Currency.USD, account_id="TEST1234",
                          status=AccountStatus.FROZEN)
        self.assertEqual(acc.account_id, "TEST1234")
        self.assertEqual(acc.status, AccountStatus.FROZEN)

    def test_invalid_currency_type_raises(self):
        with self.assertRaises(InvalidOperationError):
            BankAccount("Иван", currency="BITCOIN")

    def test_invalid_status_type_raises(self):
        with self.assertRaises(InvalidOperationError):
            BankAccount("Иван", status="active")

    def test_all_subclasses_are_bank_accounts(self):
        accounts = [
            BankAccount("A"),
            SavingsAccount("B"),
            PremiumAccount("C"),
            InvestmentAccount("D"),
        ]
        for acc in accounts:
            self.assertIsInstance(acc, BankAccount)

class BankAccountOperationsTest(QuietOutput, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.acc = BankAccount("Иван Иванов")

    def test_deposit_increases_balance(self):
        self.acc.deposit(10000.0)
        self.acc.deposit(0.5)
        self.assertAlmostEqual(self.acc.balance, 10000.5)

    def test_withdraw_returns_true_and_decreases_balance(self):
        self.acc.deposit(1000.0)
        self.assertTrue(self.acc.withdraw(500.0))
        self.assertAlmostEqual(self.acc.balance, 500.0)

    def test_withdraw_insufficient_funds_raises_and_balance_unchanged(self):
        self.acc.deposit(100.0)
        with self.assertRaises(InsufficientFundsError):
            self.acc.withdraw(15000.0)
        self.assertAlmostEqual(self.acc.balance, 100.0)

    def test_frozen_account_blocks_operations(self):
        self.acc.status = AccountStatus.FROZEN
        with self.assertRaises(AccountFrozenError):
            self.acc.deposit(500)
        with self.assertRaises(AccountFrozenError):
            self.acc.withdraw(500)

    def test_closed_account_blocks_operations(self):
        self.acc.status = AccountStatus.CLOSED
        with self.assertRaises(AccountClosedError):
            self.acc.deposit(100)
        with self.assertRaises(AccountClosedError):
            self.acc.withdraw(100)

    def test_negative_amount_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.acc.deposit(-500)

    def test_zero_amount_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.acc.withdraw(0)

    def test_non_numeric_amount_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.acc.withdraw("сто рублей")
        with self.assertRaises(InvalidOperationError):
            self.acc.deposit(None)

    def test_non_finite_amount_raises(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(InvalidOperationError):
                self.acc.deposit(bad)

    def test_get_account_info_format(self):
        acc = BankAccount("Иван", account_id="ABCD1234")
        info = acc.get_account_info()
        self.assertIn("ABCD1234", info)
        self.assertIn("Иван", info)
        self.assertIn("0.00 RUB", info)
        self.assertIn("active", info)

    def test_str_contains_key_fields(self):
        acc = BankAccount("Иван", Currency.EUR, account_id="ABCD1234")
        text = str(acc)
        self.assertIn("BankAccount", text)
        self.assertIn("*1234", text)
        self.assertIn("ACTIVE", text)
        self.assertIn("EUR", text)


class SavingsAccountTest(QuietOutput, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.acc = SavingsAccount("Игорь", min_balance=2000.0, interest_rate=0.08)

    def test_starts_with_min_balance(self):
        self.assertAlmostEqual(self.acc.balance, 2000.0)

    def test_withdraw_below_min_balance_raises(self):
        self.acc.deposit(5000.0)
        with self.assertRaises(MinBalanceViolationError):
            self.acc.withdraw(6000.0)
        self.assertAlmostEqual(self.acc.balance, 7000.0)

    def test_withdraw_to_exact_min_balance_succeeds(self):
        self.acc.deposit(5000.0)
        self.assertTrue(self.acc.withdraw(5000.0))
        self.assertAlmostEqual(self.acc.balance, 2000.0)

    def test_apply_monthly_interest(self):
        interest = self.acc.balance * 0.08
        self.acc.apply_monthly_interest()
        self.assertAlmostEqual(self.acc.balance, 2000.0 + interest)

    def test_interest_on_inactive_account_raises(self):
        self.acc.status = AccountStatus.CLOSED
        with self.assertRaises(InvalidOperationError):
            self.acc.apply_monthly_interest()

    def test_info_contains_settings(self):
        info = self.acc.get_account_info()
        self.assertIn("Мин. остаток: 2000.00", info)
        self.assertIn("Ставка: 8.0%", info)


class PremiumAccountTest(QuietOutput, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.acc = PremiumAccount("Ольга", Currency.USD,
                                  overdraft_limit=10000.0, monthly_fee=500.0)

    def test_overdraft_withdraw_allowed_into_negative(self):
        self.assertTrue(self.acc.withdraw(4000.0))
        self.assertAlmostEqual(self.acc.balance, -4000.0)

    def test_exceeding_overdraft_limit_raises(self):
        self.acc.withdraw(4000.0)
        with self.assertRaises(OverdraftLimitExceededError):
            self.acc.withdraw(10000.0)
        self.assertAlmostEqual(self.acc.balance, -4000.0)

    def test_withdraw_up_to_full_limit_succeeds(self):
        self.assertTrue(self.acc.withdraw(10000.0))
        self.assertAlmostEqual(self.acc.balance, -10000.0)

    def test_charge_monthly_fee_decreases_balance(self):
        self.acc.deposit(2000.0)
        self.acc.charge_monthly_fee()
        self.assertAlmostEqual(self.acc.balance, 1500.0)

    def test_fee_can_deepen_overdraft(self):
        self.acc.withdraw(9800.0)
        self.acc.charge_monthly_fee()
        self.assertAlmostEqual(self.acc.balance, -10300.0)

    def test_fee_on_inactive_account_raises(self):
        self.acc.status = AccountStatus.FROZEN
        with self.assertRaises(InvalidOperationError):
            self.acc.charge_monthly_fee()

    def test_info_contains_overdraft_settings(self):
        info = self.acc.get_account_info()
        self.assertIn("Лимит овердрафта: 10000.00", info)
        self.assertIn("Комиссия: 500.00", info)


class InvestmentAccountTest(QuietOutput, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.acc = InvestmentAccount("Дмитрий", Currency.RUB)
        self.acc.deposit(20000.0)

    def test_portfolio_starts_empty(self):
        self.assertEqual(self.acc.portfolio, {"stocks": 0.0, "bonds": 0.0, "etf": 0.0})

    def test_buy_asset_reduces_balance_and_adds_quantity(self):
        self.acc.buy_asset("stocks", 5000.0, asset_price=150.0)
        self.assertAlmostEqual(self.acc.portfolio["stocks"], 5000.0 / 150.0)
        self.assertAlmostEqual(self.acc.balance, 15000.0)

    def test_buy_unknown_asset_type_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.acc.buy_asset("crypto", 1000.0, asset_price=10.0)

    def test_buy_without_funds_raises(self):
        with self.assertRaises(InsufficientFundsError):
            self.acc.buy_asset("bonds", 999999.0, asset_price=1.0)

    def test_buy_invalid_amount_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.acc.buy_asset("etf", -100.0, asset_price=10.0)

    def test_project_yearly_growth_compound(self):
        expected = self.acc.balance * (1.15 ** 3)
        result = self.acc.project_yearly_growth(years=3, estimated_rate=0.15)
        self.assertAlmostEqual(result, expected)
        self.assertAlmostEqual(result, 30417.50, places=2)

    def test_info_contains_portfolio(self):
        self.acc.buy_asset("etf", 3000.0, asset_price=300.0)
        info = self.acc.get_account_info()
        self.assertIn("stocks: 0.00", info)
        self.assertIn("etf: 10.00", info)


if __name__ == "__main__":
    unittest.main()
