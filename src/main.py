import logging
from models import (
    BankAccount,
    Currency,
    AccountStatus,
    AccountFrozenError,
    AccountClosedError,
    InvalidOperationError,
    InsufficientFundsError
)

# Настройка логирования: выводим уровень, время и сообщение
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("BankDemo")


def run_demonstration():
    logger.info("Запуск демонстрации базовой модели банковских счетов (День 1)")
    print("=" * 70)

    # -----------------------------------------------------------------
    # 1. Создание активного и замороженного счёта
    # -----------------------------------------------------------------
    print("\nЭТАП 1: Создание счетов с различными статусами")

    active_acc = BankAccount(owner="Иван Иванов", currency=Currency.RUB)
    frozen_acc = BankAccount(owner="Петр Petrov", currency=Currency.USD, status=AccountStatus.FROZEN)
    closed_acc = BankAccount(owner="Анна Сидорова", currency=Currency.EUR, status=AccountStatus.CLOSED)

    print(f"Создан счет: {active_acc}")
    print(f"Создан счет: {frozen_acc}")
    print("-" * 70)

    # -----------------------------------------------------------------
    # 2. Валидное пополнение и снятие
    # -----------------------------------------------------------------
    print("\nЭТАП 2: Выполнение валидных операций над активным счетом")

    logger.info("Попытка внесения 10000.00 RUB")
    active_acc.deposit(10000.0)

    logger.info("Попытка снятия 3500.50 RUB")
    active_acc.withdraw(3500.50)

    print(f"Текущее состояние счета: {active_acc.get_account_info()}")
    print("-" * 70)

    # -----------------------------------------------------------------
    # 3. Попытка операций над замороженным и закрытым счётом
    # -----------------------------------------------------------------
    print("\nЭТАП 3: Проверка блокировки операций по статусу счета")

    print("Попытка пополнить замороженный счет Петра...")
    try:
        frozen_acc.deposit(500)
    except AccountFrozenError as e:
        logger.warning(f"Ошибка операции: {e}")

    print("\nПопытка снять деньги с закрытого счета Анны...")
    try:
        closed_acc.withdraw(100)
    except AccountClosedError as e:
        logger.warning(f"Ошибка операции: {e}")
    print("-" * 70)

    # -----------------------------------------------------------------
    # 4. Проверка базовых операций и защиты
    # -----------------------------------------------------------------
    print("\nЭТАП 4: Валидация входящих данных и защита баланса")

    print("Тест А: Превышение доступного лимита баланса...")
    try:
        active_acc.withdraw(15000.0)
    except InsufficientFundsError as e:
        logger.warning(f"Ошибка операции: {e}")

    print("\nТест Б: Передача отрицательного значения суммы...")
    try:
        active_acc.deposit(-500)
    except InvalidOperationError as e:
        logger.warning(f"Ошибка операции: {e}")

    print("\nТест В: Некорректный тип данных суммы (строка)...")
    try:
        active_acc.withdraw("сто рублей")
    except InvalidOperationError as e:
        logger.warning(f"Ошибка операции: {e}")

    print("\nТест Г: Передача некорректного типа валюты при инициализации...")
    try:
        BankAccount(owner="Неизвестный", currency="BITCOIN")
    except InvalidOperationError as e:
        logger.warning(f"Ошибка инициализации: {e}")

    print("=" * 70)
    logger.info("Демонстрация завершена. Все бизнес-правила отработали корректно.")


if __name__ == "__main__":
    run_demonstration()
