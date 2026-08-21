import logging
from models import (
    BankAccount,
    SavingsAccount,
    PremiumAccount,
    InvestmentAccount,
    Currency,
    AccountStatus,
    AccountFrozenError,
    AccountClosedError,
    InvalidOperationError,
    InsufficientFundsError,
    MinBalanceViolationError,
    OverdraftLimitExceededError
)

# Настройка логирования: выводим уровень, время и сообщение
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("BankDemo")


def run_demonstration_day_one():
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


def run_demonstration_day_two():
    logger.info("Запуск демонстрации продвинутых типов счетов (День 2)")
    print("=" * 80)

    # 1. Тестирование SavingsAccount
    print("\nЭТАП 1: Тестирование Сберегательного счета (SavingsAccount)")
    savings = SavingsAccount("Игорь Николаев", Currency.RUB, min_balance=2000.0, interest_rate=0.08)
    print(savings)  # Проверка __str__

    savings.deposit(5000.0)

    print("Попытка нарушить минимальный остаток (снять 6000 при балансе 7000 и лимите 2000)...")
    try:
        savings.withdraw(6000.0)
    except MinBalanceViolationError as e:
        logger.warning(f"Блокировка: {e}")

    # Валидное снятие
    savings.withdraw(3000.0)
    # Начисление процентов
    savings.apply_monthly_interest()
    print(f"Информация: {savings.get_account_info()}")
    print("-" * 80)

    # 2. Тестирование PremiumAccount
    print("\nЭТАП 2: Тестирование Премиум счета (PremiumAccount)")
    premium = PremiumAccount("Ольга Бузова", Currency.USD, overdraft_limit=10000.0, monthly_fee=500.0)
    print(premium)

    # Уводим баланс в минус за счет овердрафта
    logger.info("Снятие суммы, превышающей баланс, с использованием овердрафта")
    premium.withdraw(4000.0)  # Баланс станет -4000.00

    print("Попытка превысить лимит овердрафта (снять еще 10000)...")
    try:
        premium.withdraw(10000.0)
    except OverdraftLimitExceededError as e:
        logger.warning(f"Блокировка: {e}")

    premium.charge_monthly_fee()  # Списание комиссии
    print(f"Информация: {premium.get_account_info()}")
    print("-" * 80)

    # 3. Тестирование InvestmentAccount
    print("\nЭТАП 3: Тестирование Инвестиционного счета (InvestmentAccount)")
    invest = InvestmentAccount("Дмитрий Нагиев", Currency.CNY)
    print(invest)

    invest.deposit(20000.0)
    # Покупка акций и ETF
    invest.buy_asset("stocks", 5000.0, asset_price=150.0)
    invest.buy_asset("etf", 3000.0, asset_price=300.0)

    # Прогноз доходности портфеля
    invest.project_yearly_growth(years=3, estimated_rate=0.15)
    print(f"Информация: {invest.get_account_info()}")
    print("=" * 80)

    # 4. Демонстрация Полиморфизма
    print("\nЭТАП 4: Демонстрация Полиморфизма")
    accounts_list = [savings, premium, invest]
    for acc in accounts_list:
        # Вызов одинакового метода __str__ выдаст разный результат в зависимости от реального класса
        print(f"Обработка через цикл полиморфизма -> {acc}")

    logger.info("Демонстрация Дня 2 завершена.")


if __name__ == "__main__":
    run_demonstration_day_one()
    run_demonstration_day_two()
