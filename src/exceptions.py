class AccountFrozenError(Exception): pass

class AccountClosedError(Exception): pass

class InvalidOperationError(Exception): pass

class InsufficientFundsError(Exception): pass

class MinBalanceViolationError(Exception): pass

class OverdraftLimitExceededError(Exception): pass

class BankException(Exception): pass

class AuthenticationError(BankException): pass

class SecurityBlockError(BankException): pass

class MaintenanceTimeError(BankException): pass