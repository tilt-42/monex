"""The console front end: asks the questions and shows the results."""

from monex.expenses import Group

YES_LIST = ('Y', 'y', 'yes', 'Yes', 'YES')


def ask_yes_no(question):
  return input(question + '\n') in YES_LIST


def ask_number(question):
  while True:
    try:
      return int(input(question + '\n'))
    except ValueError:
      print('Please enter a number')


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
    participants.append(input('enter the name of a participant\n'))
    add_participant = ask_yes_no('add another participant? (y/n)')
  return participants


def run():
  group = Group(ask_participants())

  add_payment = True
  while add_payment:
    payer = ask_participant('Please enter the name of the payer', group.participants)
    amount = ask_number('Please enter the amount')
    group.add_expense(payer, amount)
    print('Expense added')
    add_payment = ask_yes_no('add another expense?')

  print("Total paid: " + str(group.total_paid_by_participant()))
  print("Expenses per participant: " + str(group.expense_per_participant()))
  print("Balances per participant: " + str(group.balance_per_participant()))
  print("Settlements needed: " + str(group.settle_balances()))
