"""The money logic. Nothing here reads input or prints, so any front end can use it."""

import re
from dataclasses import dataclass
from decimal import Decimal

CENT = Decimal('0.01')
AMOUNT_FORMAT = re.compile(r'[0-9]{1,12}([.,][0-9]{1,2})?')


def parse_amount(text):
  """Turn text like '12', '12.5' or '12,50' into a positive Decimal, or raise ValueError."""
  text = text.strip()
  if not AMOUNT_FORMAT.fullmatch(text):
    raise ValueError(f'Not an amount: {text}')
  amount = Decimal(text.replace(',', '.'))
  if amount <= 0:
    raise ValueError('The amount must be more than 0')
  return amount


def round_to_cents(amount):
  return Decimal(amount).quantize(CENT)


def format_amount(amount):
  # Adding 0 turns -0.00 into 0.00.
  return str(round_to_cents(amount) + 0)


@dataclass(frozen=True)
class Expense:
  payer: str
  amount: Decimal


class Group:
  """The people sharing costs and the expenses they have paid."""

  def __init__(self, participants):
    # A repeated name would count twice when splitting the total.
    self.participants = list(dict.fromkeys(participants))
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
        payment = round_to_cents(min(debt_amount, credit_amount))
        if payment <= 0:
          continue
        settlements.append((debtor, creditor, payment))
        debt_amount -= payment
        creditors[creditor] -= payment

    return settlements
