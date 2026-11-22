"""In-memory account ledger. Amounts are positive integer cents."""

from __future__ import annotations


class Ledger:
    def __init__(self) -> None:
        self._balances: dict[str, int] = {}

    def balance(self, account: str) -> int:
        return self._balances.get(account, 0)

    def deposit(self, account: str, amount: int) -> None:
        self._require_account(account)
        self._require_amount(amount)
        self._balances[account] = self.balance(account) + amount

    def withdraw(self, account: str, amount: int) -> None:
        self._require_account(account)
        self._require_amount(amount)
        if self.balance(account) < amount:
            raise ValueError("insufficient funds")
        self._balances[account] = self.balance(account) - amount

    def transfer(self, source: str, target: str, amount: int) -> None:
        self._require_account(source)
        self._require_account(target)
        self._require_amount(amount)
        if source == target:
            raise ValueError("cannot transfer to the same account")
        if self.balance(source) < amount:
            raise ValueError("insufficient funds")
        self._balances[source] = self.balance(source) - amount
        self._balances[target] = self.balance(target) + amount

    def _require_account(self, account: str) -> None:
        if not account:
            raise ValueError("account name is required")

    def _require_amount(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be greater than 0")
