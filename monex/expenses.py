"""The money logic. Nothing here reads input or prints, so any front end can use it."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Expense:
  payer: str
  amount: int


class Group:
  """The people sharing costs and the expenses they have paid."""

  def __init__(self, participants):
    self.participants = list(participants)
    self.expenses = []

  def add_expense(self, payer, amount):
    if payer not in self.participants:
      raise ValueError(f'Unknown participant: {payer}')
    self.expenses.append(Expense(payer, amount))

  def total_paid_by_participant(self):
    totals = {participant: 0 for participant in self.participants}
    for expense in self.expenses:
      totals[expense.payer] += expense.amount
    return totals

  def total_expenses(self):
    return sum(expense.amount for expense in self.expenses)

  def expense_per_participant(self):
    if not self.participants:
      return 0
    return self.total_expenses() / len(self.participants)

  def balance_per_participant(self):
    balance = {}
    expense_per_participant = self.expense_per_participant()
    for participant in self.participants:
      total_paid = sum(expense.amount for expense in self.expenses if expense.payer == participant)
      balance[participant] = total_paid - expense_per_participant
    return balance

  def settle_balances(self):
    balance = self.balance_per_participant()
    creditors = {p: b for p, b in balance.items() if b > 0}
    debtors = {p: -b for p, b in balance.items() if b < 0}

    settlements = []
    for debtor, debt_amount in debtors.items():
      for creditor, credit_amount in creditors.items():
        if debt_amount <= 0:
          break
        payment = round(100*min(debt_amount, credit_amount))/100
        settlements.append((debtor, creditor, payment))
        debt_amount -= payment
        creditors[creditor] -= payment

    return settlements
