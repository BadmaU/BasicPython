import os
import sys
import unittest
import contextlib
import io
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import models
from models import (
    Bank,
    BankAccount,
    Client,
    Currency,
    AccountStatus,
    ClientStatus,
)
from exceptions import (
    AccountFrozenError,
    AuthenticationError,
    InvalidOperationError,
    MaintenanceTimeError,
    SecurityBlockError,
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


def fake_clock(hour: int):
    fake = mock.MagicMock()
    fake.now.return_value.hour = hour
    return fake


class ClientTest(unittest.TestCase):
    def test_create_client(self):
        client = Client("Иван Иванов", 30, "+7-900-000-00-00", "1234")
        self.assertTrue(client.id.startswith("CLI-"))
        self.assertEqual(client.full_name, "Иван Иванов")
        self.assertEqual(client.age, 30)
        self.assertEqual(client.status, ClientStatus.ACTIVE)
        self.assertEqual(client.account_numbers, [])
        self.assertEqual(client.failed_login_attempts, 0)

    def test_minor_registration_raises(self):
        with self.assertRaises(InvalidOperationError):
            Client("Петя Малолетний", 17, "+7-900", "0000")

    def test_eighteen_years_old_allowed(self):
        client = Client("Свежесовершеннолетний", 18, "+7-900", "0000")
        self.assertEqual(client.age, 18)


class BankAuthTest(QuietOutput, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.bank = Bank("ТестБанк")
        self.client = self.bank.add_client("Иван Иванов", 30, "+7-900", "1234")

    def test_add_client_registers_client(self):
        self.assertIn(self.client.id, self.bank.clients)
        self.assertIs(self.bank.clients[self.client.id], self.client)

    def test_authenticate_with_correct_pin(self):
        self.assertTrue(self.bank.authenticate_client(self.client.id, "1234"))

    def test_authenticate_unknown_client_raises(self):
        with self.assertRaises(AuthenticationError):
            self.bank.authenticate_client("CLI-NOPE", "1234")

    def test_wrong_pin_raises_and_counts_attempts(self):
        with self.assertRaises(AuthenticationError) as ctx:
            self.bank.authenticate_client(self.client.id, "9999")
        self.assertIn("Осталось попыток: 2", str(ctx.exception))
        self.assertEqual(self.client.failed_login_attempts, 1)

    def test_correct_pin_resets_attempt_counter(self):
        with self.assertRaises(AuthenticationError):
            self.bank.authenticate_client(self.client.id, "9999")
        self.assertTrue(self.bank.authenticate_client(self.client.id, "1234"))
        self.assertEqual(self.client.failed_login_attempts, 0)

    def test_three_wrong_pins_blocks_client(self):
        with self.assertRaises(AuthenticationError):
            self.bank.authenticate_client(self.client.id, "9999")
        with self.assertRaises(AuthenticationError):
            self.bank.authenticate_client(self.client.id, "9999")
        with self.assertRaises(SecurityBlockError):
            self.bank.authenticate_client(self.client.id, "9999")

        self.assertEqual(self.client.status, ClientStatus.BLOCKED)
        self.assertEqual(len(self.bank.suspicious_log), 1)
        self.assertIn("ЗАБЛОКИРОВАН", self.bank.suspicious_log[0])

    def test_blocked_client_rejected_even_with_correct_pin(self):
        self.client.status = ClientStatus.BLOCKED
        with self.assertRaises(SecurityBlockError):
            self.bank.authenticate_client(self.client.id, "1234")


class BankAccountsTest(QuietOutput, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Фиксируем "дневное" время (12:00), чтобы тесты не зависели
        # от реального времени запуска (ночью операции запрещены).
        clock = mock.patch.object(models, "datetime", fake_clock(12))
        clock.start()
        self.addCleanup(clock.stop)

        self.bank = Bank("ТестБанк")
        self.client = self.bank.add_client("Иван Иванов", 30, "+7-900", "1234")
        self.other = self.bank.add_client("Мария Петрова", 25, "+7-911", "4321")

    def test_open_account_links_to_client(self):
        acc = self.bank.open_account(self.client.id, Currency.USD)
        self.assertIsInstance(acc, BankAccount)
        self.assertEqual(acc.currency, Currency.USD)
        self.assertEqual(acc.balance, 0.0)
        self.assertIn(acc.account_id, self.bank.accounts)
        self.assertIn(acc.account_id, self.client.account_numbers)

    def test_open_account_for_unknown_client_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.bank.open_account("CLI-NOPE")

    def test_open_account_for_blocked_client_raises(self):
        self.client.status = ClientStatus.BLOCKED
        with self.assertRaises(SecurityBlockError):
            self.bank.open_account(self.client.id)

    def test_operations_during_maintenance_time_raise(self):
        acc = self.bank.open_account(self.client.id)
        with mock.patch.object(models, "datetime", fake_clock(2)):
            with self.assertRaises(MaintenanceTimeError):
                self.bank.open_account(self.client.id)
            with self.assertRaises(MaintenanceTimeError):
                self.bank.close_account(acc.account_id)
            with self.assertRaises(MaintenanceTimeError):
                self.bank.freeze_account(acc.account_id)
            with self.assertRaises(MaintenanceTimeError):
                self.bank.unfreeze_account(acc.account_id)

    def test_maintenance_time_ends_at_five_am(self):
        acc = self.bank.open_account(self.client.id)
        with mock.patch.object(models, "datetime", fake_clock(5)):
            self.bank.freeze_account(acc.account_id)

    def test_close_account_with_zero_balance(self):
        acc = self.bank.open_account(self.client.id)
        self.bank.close_account(acc.account_id)
        self.assertEqual(acc.status, AccountStatus.CLOSED)

    def test_cannot_close_account_with_money(self):
        acc = self.bank.open_account(self.client.id)
        acc.deposit(500.0)
        with self.assertRaises(InvalidOperationError):
            self.bank.close_account(acc.account_id)
        self.assertEqual(acc.status, AccountStatus.ACTIVE)
        self.assertEqual(len(self.bank.suspicious_log), 1)
        self.assertIn(acc.account_id, self.bank.suspicious_log[0])

    def test_close_unknown_account_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.bank.close_account("NO-SUCH-ID")

    def test_freeze_and_unfreeze_account(self):
        acc = self.bank.open_account(self.client.id)
        self.bank.freeze_account(acc.account_id)
        self.assertEqual(acc.status, AccountStatus.FROZEN)
        self.bank.unfreeze_account(acc.account_id)
        self.assertEqual(acc.status, AccountStatus.ACTIVE)

    def test_freeze_unknown_account_raises(self):
        with self.assertRaises(InvalidOperationError):
            self.bank.freeze_account("NO-SUCH-ID")

    def test_search_accounts_returns_only_own_accounts(self):
        acc1 = self.bank.open_account(self.client.id)
        acc2 = self.bank.open_account(self.client.id, Currency.EUR)
        foreign = self.bank.open_account(self.other.id)

        found = self.bank.search_accounts(self.client.id)
        self.assertCountEqual(found, [acc1, acc2])
        self.assertNotIn(foreign, found)

    def test_search_accounts_unknown_client_returns_empty(self):
        self.assertEqual(self.bank.search_accounts("CLI-NOPE"), [])

    def test_total_balance_filters_by_currency_and_closed(self):
        rub1 = self.bank.open_account(self.client.id, Currency.RUB)
        rub2 = self.bank.open_account(self.other.id, Currency.RUB)
        usd = self.bank.open_account(self.client.id, Currency.USD)

        rub1.deposit(1000.0)
        rub2.deposit(250.5)
        usd.deposit(999.0)

        closed = self.bank.open_account(self.other.id, Currency.RUB)
        closed.deposit(777.0)
        closed.status = AccountStatus.CLOSED

        self.assertAlmostEqual(self.bank.get_total_balance(Currency.RUB), 1250.5)
        self.assertAlmostEqual(self.bank.get_total_balance(Currency.USD), 999.0)
        self.assertAlmostEqual(self.bank.get_total_balance(Currency.EUR), 0.0)

    def test_clients_ranking_sorted_by_total_desc(self):
        poor = self.bank.open_account(self.client.id)
        poor.deposit(100.0)

        rich_rub = self.bank.open_account(self.other.id, Currency.RUB)
        rich_usd = self.bank.open_account(self.other.id, Currency.USD)
        rich_rub.deposit(5000.0)
        rich_usd.deposit(3000.0)

        ranking = self.bank.get_clients_ranking()
        self.assertEqual([r["name"] for r in ranking], ["Мария Петрова", "Иван Иванов"])
        self.assertAlmostEqual(ranking[0]["total_balance"], 8000.0)
        self.assertAlmostEqual(ranking[1]["total_balance"], 100.0)
        self.assertEqual(ranking[0]["id"], self.other.id)


class Day3ScenarioTest(QuietOutput, unittest.TestCase):
    """Сквозной сценарий из задания День 3: клиенты -> счета -> вход -> заморозка."""

    def setUp(self):
        super().setUp()
        clock = mock.patch.object(models, "datetime", fake_clock(12))
        clock.start()
        self.addCleanup(clock.stop)
        self.bank = Bank("СценарныйБанк")

    def test_full_day3_scenario(self):
        # 1. Создание нескольких клиентов
        alice = self.bank.add_client("Алиса Смирнова", 30, "+7-901", "1111")
        bob = self.bank.add_client("Боб Кузнецов", 45, "+7-902", "2222")

        # 2. Открытие счетов для каждого клиента
        acc_a = self.bank.open_account(alice.id, Currency.RUB)
        acc_b = self.bank.open_account(bob.id, Currency.EUR)
        self.assertIn(acc_a.account_id, alice.account_numbers)
        self.assertIn(acc_b.account_id, bob.account_numbers)
        self.assertEqual(self.bank.search_accounts(bob.id), [acc_b])

        # 3. Попытки входа: две неверные, затем верная (счетчик сбрасывается)
        with self.assertRaises(AuthenticationError):
            self.bank.authenticate_client(alice.id, "0000")
        with self.assertRaises(AuthenticationError):
            self.bank.authenticate_client(alice.id, "9999")
        self.assertTrue(self.bank.authenticate_client(alice.id, "1111"))
        self.assertEqual(alice.failed_login_attempts, 0)

        # 4. Заморозка счета блокирует операции, разморозка возвращает доступ
        acc_a.deposit(300.0)
        self.bank.freeze_account(acc_a.account_id)
        with self.assertRaises(AccountFrozenError):
            acc_a.deposit(500.0)
        self.bank.unfreeze_account(acc_a.account_id)
        acc_a.deposit(500.0)

        # 5. Аналитика: суммарный баланс и рейтинг клиентов
        self.assertAlmostEqual(self.bank.get_total_balance(Currency.RUB), 800.0)
        self.assertAlmostEqual(self.bank.get_total_balance(Currency.EUR), 0.0)
        ranking = self.bank.get_clients_ranking()
        self.assertEqual(ranking[0]["name"], "Алиса Смирнова")
        self.assertAlmostEqual(ranking[0]["total_balance"], 800.0)


if __name__ == "__main__":
    unittest.main()
