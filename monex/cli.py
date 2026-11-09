"""The console front end: asks the questions and shows the results."""

from monex.expenses import Group, format_amount, parse_amount, parse_name

YES_LIST = ('Y', 'y', 'yes', 'Yes', 'YES')


def format_amounts(amounts):
  return ', '.join(f'{name}: {format_amount(amount)}' for name, amount in amounts.items())


def ask_yes_no(question):
  return input(question + '\n') in YES_LIST


def ask_amount(question):
  while True:
    try:
      return parse_amount(input(question + '\n'))
    except ValueError:
      print('Please enter an amount like 12.50')


def ask_name(question):
  while True:
    try:
      return parse_name(input(question + '\n'))
    except ValueError:
      print("Names can only contain letters, numbers, - and '")


def ask_participant(question, participants):
  print('Enter one of these:')
  print('\n'.join(participants))
  result = input(question + '\n')
  while result not in participants:
    print('Please enter one of the names in this list:')
    print('\n'.join(participants))
    result = input(question + '\n')
  return result


def ask_participants():
  participants = []
  add_participant = True
  while add_participant:
    participants.append(ask_name('enter the name of a participant'))
    add_participant = ask_yes_no('add another participant? (y/n)')
  return participants


def run():
  group = Group(ask_participants())

  add_payment = True
  while add_payment:
    payer = ask_participant('Please enter the name of the payer', group.participants)
    amount = ask_amount('Please enter the amount')
    group.add_expense(payer, amount)
    print('Expense added')
    add_payment = ask_yes_no('add another expense?')

  settlements = [f'{debtor} pays {creditor} {format_amount(amount)}' for debtor, creditor, amount in group.settle_balances()]
  print("Total paid: " + format_amounts(group.total_paid_by_participant()))
  print("Expenses per participant: " + format_amounts(group.share_per_participant()))
  print("Balances per participant: " + format_amounts(group.balance_per_participant()))
  print("Settlements needed: " + ', '.join(settlements))
