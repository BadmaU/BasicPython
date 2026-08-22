import math
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

from exceptions import (
    AccountClosedError,
    AccountFrozenError,
    AuthenticationError,
    InsufficientFundsError,
    InvalidOperationError,
    MaintenanceTimeError,
    MinBalanceViolationError,
    OverdraftLimitExceededError,
    SecurityBlockError,
)

class Currency(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    CNY = "CNY"

class AccountStatus(Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"

class ClientStatus(Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"  # Для блокировки после 3 неверных попыток


class AbstractAccount(ABC):
    def __init__(self, owner: str, account_id: str = None, status: AccountStatus = AccountStatus.ACTIVE):
        if not isinstance(status, AccountStatus):
            raise InvalidOperationError("Неверный формат статуса. Используйте класс AccountStatus.")
        self.account_id: str = account_id if account_id else str(uuid.uuid4())[:8]
        self.owner: str = owner
        self._balance: float = 0.0
        self.status: AccountStatus = status

    @property
    def balance(self) -> float:
        return self._balance

    @abstractmethod
    def deposit(self, amount: float) -> None:
        """Пополнить счет."""
        pass

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        """Снять деньги со счета."""
        pass

    @abstractmethod
    def get_account_info(self) -> str:
        """Получить информацию о счете."""
        pass

    def __str__(self) -> str:
        short_id = self.account_id[-4:]
        return (
            f"Тип счета: {self.__class__.__name__} | "
            f"Клиент: {self.owner} | "
            f"Номер: *{short_id} | "
            f"Статус: {self.status.value.upper()} | "
            f"Баланс: {self._balance:.2f} {self.currency.value}"
        )


class BankAccount(AbstractAccount):
    def __init__(self, owner: str, currency: Currency = Currency.RUB, account_id: str = None,
                 status: AccountStatus = AccountStatus.ACTIVE):
        super().__init__(owner, account_id, status)

        if not isinstance(currency, Currency):
            raise InvalidOperationError("Неверный формат валюты. Используйте класс Currency.")
        self.currency: Currency = currency

    def _validate_operation(self, amount: float) -> None:
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError(f"Операция невозможна. Счёт {self.account_id} заморожен.")
        if self.status == AccountStatus.CLOSED:
            raise AccountClosedError(f"Операция невозможна. Счёт {self.account_id} закрыт.")

        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("Сумма должна быть числом.")

        if not math.isfinite(amount):
            raise InvalidOperationError("Сумма операции должна быть конечным числом.")

        if amount <= 0:
            raise InvalidOperationError("Сумма операции должна быть строго больше нуля.")

    def deposit(self, amount: float) -> None:
        self._validate_operation(amount)
        self._balance += float(amount)
        print(f"[Пополнение] На счёт *{self.account_id[-4:]} зачислено {amount} {self.currency.value}")

    def withdraw(self, amount: float) -> bool:
        self._validate_operation(amount)

        if self._balance < amount:
            raise InsufficientFundsError(
                f"Недостаточно средств. Баланс: {self._balance}, Запрос: {amount}"
            )

        self._balance -= float(amount)
        print(f" [Снятие] Со счёта *{self.account_id[-4:]} снято {amount} {self.currency.value}")
        return True

    def get_account_info(self) -> str:
        return f"Счёт {self.account_id} ({self.owner}): {self._balance:.2f} {self.currency.value} [{self.status.value}]"

class SavingsAccount(BankAccount):
    def __init__(self, owner: str, currency: Currency = Currency.RUB,
                 account_id: str = None, status: AccountStatus = AccountStatus.ACTIVE,
                 min_balance: float = 1000.0, interest_rate: float = 0.05):
        super().__init__(owner, currency, account_id, status)

        # 🔒 Минимальный остаток и ставка доходности (например, 0.05 = 5% в месяц)
        self.min_balance: float = float(min_balance)
        self.interest_rate: float = float(interest_rate)

        # Сберегательный счет не может быть открыт с балансом меньше минимального
        self._balance = self.min_balance

    def withdraw(self, amount: float) -> bool:
        self._validate_operation(amount)

        # Проверяем, не нарушит ли снятие лимит минимального остатка
        if self._balance - amount < self.min_balance:
            raise MinBalanceViolationError(
                f"Невозможно снять {amount}. На счете должен оставаться неснижаемый остаток: {self.min_balance}"
            )

        self._balance -= float(amount)
        print(f"[Снятие (Savings)] Со счёта *{self.account_id[-4:]} снято {amount} {self.currency.value}")
        return True

    def apply_monthly_interest(self) -> None:
        """💰 Начисление процентов на текущий баланс."""
        if self.status != AccountStatus.ACTIVE:
            raise InvalidOperationError("Нельзя начислить проценты на неактивный счет.")

        interest = self._balance * self.interest_rate
        self._balance += interest
        print(
            f"[Проценты] На счёт *{self.account_id[-4:]} начислено {interest:.2f} {self.currency.value} ({self.interest_rate * 100}%)")

    def get_account_info(self) -> str:
        base_info = super().get_account_info()
        return f"{base_info} | Мин. остаток: {self.min_balance:.2f} | Ставка: {self.interest_rate * 100}%"


class PremiumAccount(BankAccount):
    def __init__(self, owner: str, currency: Currency = Currency.RUB,
                 account_id: str = None, status: AccountStatus = AccountStatus.ACTIVE,
                 overdraft_limit: float = 50000.0, monthly_fee: float = 1500.0):
        super().__init__(owner, currency, account_id, status)

        # Кредитный лимит (овердрафт) и фиксированная комиссия
        self.overdraft_limit: float = float(overdraft_limit)
        self.monthly_fee: float = float(monthly_fee)

    def withdraw(self, amount: float) -> bool:
        self._validate_operation(amount)

        # Допустимый предел: текущий баланс + лимит овердрафта
        available_funds = self._balance + self.overdraft_limit
        if amount > available_funds:
            raise OverdraftLimitExceededError(
                f"Превышен лимит овердрафта. Доступно с учетом кредита: {available_funds}"
            )

        self._balance -= float(amount)
        print(
            f"[Снятие (Premium)] Со счёта *{self.account_id[-4:]} снято {amount} {self.currency.value} (Баланс: {self._balance:.2f})")
        return True

    def charge_monthly_fee(self) -> None:
        """Списание фиксированной комиссии (может уводить баланс в овердрафт)."""
        if self.status != AccountStatus.ACTIVE:
            raise InvalidOperationError("Нельзя списать комиссию с неактивного счета.")

        self._balance -= self.monthly_fee
        print(f"[Комиссия] Со счёта *{self.account_id[-4:]} списано {self.monthly_fee} {self.currency.value}")

    def get_account_info(self) -> str:
        base_info = super().get_account_info()
        return f"{base_info} | Лимит овердрафта: {self.overdraft_limit:.2f} | Комиссия: {self.monthly_fee:.2f}"


class InvestmentAccount(BankAccount):
    def __init__(self, owner: str, currency: Currency = Currency.RUB,
                 account_id: str = None, status: AccountStatus = AccountStatus.ACTIVE):
        super().__init__(owner, currency, account_id, status)

        # Виртуальные активы внутри портфеля {название: количество}
        self.portfolio: dict[str, float] = {
            "stocks": 0.0,
            "bonds": 0.0,
            "etf": 0.0
        }

    def buy_asset(self, asset_type: str, amount_money: float, asset_price: float) -> None:
        """Покупка виртуального актива на сумму со счета."""
        self._validate_operation(amount_money)
        if asset_type not in self.portfolio:
            raise InvalidOperationError(f"Неизвестный тип актива: {asset_type}. Доступны: stocks, bonds, etf")
        if self._balance < amount_money:
            raise InsufficientFundsError("Недостаточно средств для покупки активов.")

        quantity = amount_money / asset_price
        self._balance -= amount_money
        self.portfolio[asset_type] += quantity
        print(f"[Инвестиция] Куплено {quantity:.4f} ед. '{asset_type}' на сумму {amount_money} {self.currency.value}")

    def project_yearly_growth(self, years: int = 5, estimated_rate: float = 0.12) -> float:
        """Расчет прогнозируемого роста баланса по формуле сложного процента."""
        # Формула: A = P * (1 + r)^t
        projected_balance = self._balance * ((1 + estimated_rate) ** years)
        print(
            f"[Прогноз] За {years} лет при ставке {estimated_rate * 100}% баланс вырастет до {projected_balance:.2f} {self.currency.value}")
        return projected_balance

    def get_account_info(self) -> str:
        base_info = super().get_account_info()
        portfolio_str = ", ".join([f"{k}: {v:.2f}" for k, v in self.portfolio.items()])
        return f"{base_info} | Портфель -> [{portfolio_str}]"


class Client:
    """1. Класс Client"""
    def __init__(self, full_name: str, age: int, phone: str, pin: str):
        if age < 18:
            raise InvalidOperationError("Регистрация клиентов младше 18 лет запрещена.")

        self.id = f"CLI-{uuid.uuid4().hex[:6].upper()}"
        self.full_name = full_name
        self.age = age
        self.phone = phone
        self._pin = pin  # Приватный ПИН-код для аутентификации

        self.status = ClientStatus.ACTIVE
        self.account_numbers = []  # Список номеров счетов клиента
        self.failed_login_attempts = 0


class Bank:
    """2. Класс Bank с функциями защиты и аналитики"""
    def __init__(self, name: str):
        self.name = name
        self.clients = {}  # id -> Client
        self.accounts = {}  # account_id -> BankAccount
        self.suspicious_log = []  # Лог подозрительных действий


    def _check_maintenance_time(self):
        """Запрет операций с 00:00 до 05:00"""
        current_hour = datetime.now().hour
        if 0 <= current_hour < 5:
            raise MaintenanceTimeError("Технический перерыв. Операции запрещены с 00:00 до 05:00.")

    def _log_suspicious(self, message: str):
        """Пометка подозрительных действий"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] ⚠️ ВНИМАНИЕ: {message}"
        self.suspicious_log.append(log_entry)
        print(log_entry)

    def add_client(self, full_name: str, age: int, phone: str, pin: str) -> Client:
        """Регистрация нового клиента"""
        client = Client(full_name, age, phone, pin)
        self.clients[client.id] = client
        return client

    def authenticate_client(self, client_id: str, pin: str) -> bool:
        """Аутентификация клиента с защитой от брутфорса"""
        if client_id not in self.clients:
            raise AuthenticationError("Клиент не найден.")

        client = self.clients[client_id]

        if client.status == ClientStatus.BLOCKED:
            raise SecurityBlockError("Личный кабинет заблокирован из-за превышения попыток ввода ПИН-кода.")

        if client._pin == pin:
            client.failed_login_attempts = 0  # Сбрасываем счетчик при успехе
            return True
        else:
            client.failed_login_attempts += 1
            if client.failed_login_attempts >= 3:
                client.status = ClientStatus.BLOCKED
                self._log_suspicious(f"Клиент {client.id} ({client.full_name}) ЗАБЛОКИРОВАН. 3 неверных ввода ПИН.")
                raise SecurityBlockError("Превышено число попыток! Личный кабинет заблокирован.")

            raise AuthenticationError(f"Неверный ПИН-код. Осталось попыток: {3 - client.failed_login_attempts}")

    def open_account(self, client_id: str, currency: Currency = Currency.RUB) -> BankAccount:
        """Открытие счета для клиента"""
        self._check_maintenance_time()
        if client_id not in self.clients:
            raise InvalidOperationError("Клиент не зарегистрирован в банке.")

        client = self.clients[client_id]
        if client.status == ClientStatus.BLOCKED:
            raise SecurityBlockError("Невозможно открыть счет. Клиент заблокирован.")

        account = BankAccount(owner=client_id, currency=currency)
        self.accounts[account.account_id] = account
        client.account_numbers.append(account.account_id)
        return account

    def close_account(self, account_id: str):
        """Закрытие счета"""
        self._check_maintenance_time()
        if account_id not in self.accounts:
            raise InvalidOperationError("Счет не найден.")

        account = self.accounts[account_id]
        if account.balance > 0:
            self._log_suspicious(f"Попытка закрыть счет {account_id} с ненулевым балансом ({account.balance}).")
            raise InvalidOperationError("Нельзя закрыть счет, пока на нем есть средства.")

        account.status = AccountStatus.CLOSED

    def freeze_account(self, account_id: str):
        """Заморозка счета"""
        if account_id not in self.accounts:
            raise InvalidOperationError("Счет не найден.")
        self.accounts[account_id].status = AccountStatus.FROZEN

    def unfreeze_account(self, account_id: str):
        """Разморозка счета"""
        if account_id not in self.accounts:
            raise InvalidOperationError("Счет не найден.")
        self.accounts[account_id].status = AccountStatus.ACTIVE

    def search_accounts(self, client_id: str) -> list[BankAccount]:
        """Поиск всех счетов конкретного клиента"""
        if client_id not in self.clients:
            return []
        return [self.accounts[acc_id] for acc_id in self.clients[client_id].account_numbers]

    def get_total_balance(self, currency: Currency = Currency.RUB) -> float:
        """Получить суммарный баланс всех активных счетов (в рамках одной валюты)"""
        # Для простоты считаем сумму без конвертации, только по выбранной валюте
        return sum(acc.balance for acc in self.accounts.values() if
                   acc.currency == currency and acc.status != AccountStatus.CLOSED)

    def get_clients_ranking(self) -> list[dict]:
        """Рейтинг клиентов по общему объему средств на счетах (балансы суммируются независимо от валюты)"""
        ranking = []
        for client in self.clients.values():
            client_accounts = self.search_accounts(client.id)
            total_money = sum(acc.balance for acc in client_accounts)
            ranking.append({
                "id": client.id,
                "name": client.full_name,
                "total_balance": total_money
            })
        # Сортировка от большего к меньшему
        return sorted(ranking, key=lambda x: x["total_balance"], reverse=True)


