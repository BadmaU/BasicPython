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


class AbstractAccount(ABC):
    def __init__(self, owner: str, account_id: str = None, status: AccountStatus = AccountStatus.ACTIVE):
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

