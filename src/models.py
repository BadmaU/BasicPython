import math
import uuid
from abc import ABC, abstractmethod
from enum import Enum

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

class AccountFrozenError(Exception): pass

class AccountClosedError(Exception): pass

class InvalidOperationError(Exception): pass

class InsufficientFundsError(Exception): pass

class MinBalanceViolationError(Exception): pass

class OverdraftLimitExceededError(Exception): pass


class AbstractAccount(ABC):
    def __init__(self, owner: str, account_id: str = None, status: AccountStatus = AccountStatus.ACTIVE):
        if not isinstance(status, AccountStatus):
            raise InvalidOperationError("Неверный формат статуса. Используйте класс AccountStatus.")
        self.account_id: str = account_id if account_id else str(uuid.uuid4())[:8]
        self.owner: str = owner
        self._balance: float = 0.0
        self.status: AccountStatus = status

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
