import logging
from datetime import datetime
import models
from models import (
    BankAccount,
    SavingsAccount,
    PremiumAccount,
    InvestmentAccount,
    Bank,
    Currency,
    AccountStatus,
    AccountFrozenError,
    AccountClosedError,
    InvalidOperationError,
    InsufficientFundsError,
    MinBalanceViolationError,
    OverdraftLimitExceededError
)
from exceptions import (
    AuthenticationError,
    SecurityBlockError,
    MaintenanceTimeError,
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


class DemoClock(datetime):
    """Часы с управляемым временем: позволяют показать ночной технический
    перерыв банка (00:00-05:00) в любой момент запуска демонстрации."""
    current_hour = 12

    @classmethod
    def now(cls) -> datetime:
        return datetime(2026, 1, 15, cls.current_hour, 0, 0)


def run_demonstration_day_three():
    logger.info("Запуск демонстрации системы Bank и Client (День 3)")
    print("=" * 80)

    # Подменяем часы банка фиксированными, чтобы демо работало круглосуточно
    # (иначе ночью все операции заблокированы до 05:00). В конце вернем обратно.
    real_clock = models.datetime
    models.datetime = DemoClock

    bank = Bank("ДемоБанк")

    # -----------------------------------------------------------------
    print("\nЭТАП 1: Регистрация клиентов")
    ivan = bank.add_client("Иван Иванов", 30, "+7-900-111-22-33", pin="1234")
    maria = bank.add_client("Мария Петрова", 25, "+7-901-555-66-77", pin="4321")
    print(f"Клиент {ivan.full_name}: ID {ivan.id}, статус: {ivan.status.value}")
    print(f"Клиент {maria.full_name}: ID {maria.id}, статус: {maria.status.value}")

    print("\nПопытка зарегистрировать несовершеннолетнего (16 лет)...")
    try:
        bank.add_client("Петя Школьников", 16, "+7-902-000-00-00", pin="0000")
    except InvalidOperationError as e:
        logger.warning(f"Ошибка регистрации: {e}")
    print("-" * 80)

    # -----------------------------------------------------------------
    print("\nЭТАП 2: Открытие счетов")
    rub_acc = bank.open_account(ivan.id, Currency.RUB)
    eur_acc = bank.open_account(maria.id, Currency.EUR)
    print(f"Счёт Ивана: {rub_acc.get_account_info()}")
    print(f"Счёт Марии: {eur_acc.get_account_info()}")

    print("\nПопытка открыть счёт для незарегистрированного клиента...")
    try:
        bank.open_account("CLI-NOPE")
    except InvalidOperationError as e:
        logger.warning(f"Ошибка операции: {e}")
    print("-" * 80)

    # -----------------------------------------------------------------
    print("\nЭТАП 3: Пополнение счетов и аналитика банка")
    rub_acc.deposit(50000.0)
    eur_acc.deposit(3000.0)
    print(f"Суммарный баланс в рублях: {bank.get_total_balance(Currency.RUB):.2f}")
    print("-" * 80)

    # -----------------------------------------------------------------
    print("\nЭТАП 4: Аутентификация и защита от подбора ПИН-кода")

    print("Попытка входа с неверным ПИН-кодом...")
    try:
        bank.authenticate_client(ivan.id, "9999")
    except AuthenticationError as e:
        logger.warning(f"Отказ входа: {e}")

    bank.authenticate_client(ivan.id, "1234")  # Верный ПИН сбрасывает счетчик
    print(f"Верный ПИН принят, счетчик попыток сброшен ({ivan.failed_login_attempts}).")

    print("\nТри неверных ПИН-кода подряд -> блокировка кабинета...")
    for _ in range(2):
        try:
            bank.authenticate_client(ivan.id, "9999")
        except AuthenticationError as e:
            logger.warning(f"Отказ входа: {e}")
    try:
        bank.authenticate_client(ivan.id, "9999")
    except SecurityBlockError as e:
        logger.warning(f"Блокировка: {e}")

    print("\nДаже верный ПИН не пустит заблокированного клиента...")
    try:
        bank.authenticate_client(ivan.id, "1234")
    except SecurityBlockError as e:
        logger.warning(f"Блокировка: {e}")

    print("\nЗаблокированный клиент не может открыть новый счёт...")
    try:
        bank.open_account(ivan.id)
    except SecurityBlockError as e:
        logger.warning(f"Ошибка операции: {e}")
    print("-" * 80)

    # -----------------------------------------------------------------
    print("\nЭТАП 5: Технический перерыв (запрет операций с 00:00 до 05:00)")
    print("Переводим часы банка на ночь (02:00)...")
    DemoClock.current_hour = 2
    try:
        bank.open_account(maria.id)
    except MaintenanceTimeError as e:
        logger.warning(f"Отказ операции: {e}")
    DemoClock.current_hour = 12
    print("Время возвращено на дневное (12:00), банк снова работает.")
    print("-" * 80)

    # -----------------------------------------------------------------
    print("\nЭТАП 6: Заморозка и закрытие счетов")

    print("Заморозка счёта Ивана...")
    bank.freeze_account(rub_acc.account_id)
    print("Попытка пополнить замороженный счет...")
    try:
        rub_acc.deposit(1000.0)
    except AccountFrozenError as e:
        logger.warning(f"Ошибка операции: {e}")

    print("\nРазморозка счета и повторное пополнение...")
    bank.unfreeze_account(rub_acc.account_id)
    rub_acc.deposit(1000.0)
    print(f"Информация: {rub_acc.get_account_info()}")

    print("\nЗакрытие пустого счета Марии...")
    empty_eur = bank.open_account(maria.id, Currency.EUR)
    bank.close_account(empty_eur.account_id)
    print(f"Пустой счет *{empty_eur.account_id[-4:]} успешно закрыт.")

    print("\nПопытка закрыть счет с ненулевым балансом (попадет в журнал безопасности)...")
    try:
        bank.close_account(rub_acc.account_id)
    except InvalidOperationError as e:
        logger.warning(f"Ошибка операции: {e}")
    print("=" * 80)

    # -----------------------------------------------------------------
    print("\nИТОГИ ДНЯ 3:")
    print(f"Суммарный баланс RUB: {bank.get_total_balance(Currency.RUB):.2f}")
    print("\nРейтинг клиентов по объему средств:")
    for place, row in enumerate(bank.get_clients_ranking(), start=1):
        print(f"  {place}. {row['name']} ({row['id']}): {row['total_balance']:.2f}")

    print("\nЖурнал подозрительных действий:")
    for entry in bank.suspicious_log:
        print(f"  {entry}")

    # Возвращаем банку настоящие системные часы
    models.datetime = real_clock
    logger.info("Демонстрация Дня 3 завершена.")


if __name__ == "__main__":
    run_demonstration_day_one()
    run_demonstration_day_two()
    run_demonstration_day_three()
