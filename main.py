YES_LIST = ('Y', 'y', 'yes', 'Yes', 'YES')

def init_participants_list():
  participants = []
  add_participant = True
  while (add_participant):
    participants.append(input('enter the name of a participant\n'))
    add_participant = input('add another participant? (y/n)\n') in YES_LIST
  return participants

def init_payments_list(participants):
  payments = {}
  for participant in participants:
    payments[participant] = 0
  return payments

def add_expense(payments, participant, amount):
  print(payments)
  print(participant)
  print(amount)
  payments[participant] += amount
  print('Expense added')
  return payments

def input_participant(question, participants):
  print('Enter one of these:')
  for p in participants:
    print(p)
  result = input(question + '\n')
  while not result in participants:
    print('Please enter one of the names in this list:')
    print(p for p in participants)
    result = input(question + '\n')
  return result

def input_number(question):
  result = int(input(question + '\n'))
  
  while not isinstance(result, int):
    print('Please enter a number')
    result = input(question + '\n')
  return result

def main():
  participants = init_participants_list()
  print(participants)

  payments = init_payments_list(participants)
  print(payments)

  add_payment = True
  while (add_payment):
    participant = input_participant('Please enter the name of the payer', participants)
    amount = input_number('Please enter the amount')
    payments = add_expense(payments, participant, amount)
    add_payment = input('add another expense?\n') in YES_LIST
  print(payments)
  

# def test2():
#   a = int(input('enter a number\n'))
#   print(isinstance(1, int))
#   print(a)


if __name__ == "__main__":
    main()