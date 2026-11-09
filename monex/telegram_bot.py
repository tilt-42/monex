"""The Telegram front end. Each chat has its own Group, kept in memory until the bot restarts."""

import os

from telegram.ext import Application, CommandHandler

from monex.expenses import Group, format_amount, parse_amount

HELP_TEXT = (
  'I split small shared expenses.\n\n'
  '/new Alice Bob Carol - start a new group (replaces the current one)\n'
  '/pay Alice 12.50 - record that Alice paid 12.50 for everyone\n'
  '/status - show what everyone paid and their balance\n'
  '/settle - show who should pay whom\n'
  '/help - show this message\n\n'
  'Names are one word each.'
)
NO_GROUP_TEXT = 'There is no group in this chat yet. Start one with /new Alice Bob'


async def reply(update, text):
  await update.effective_message.reply_text(text)


async def show_help(update, context):
  await reply(update, HELP_TEXT)


async def new_group(update, context):
  group = Group(context.args)
  if len(group.participants) < 2:
    await reply(update, 'Please give at least two names, like this: /new Alice Bob')
    return

  context.chat_data['group'] = group
  await reply(update, f'New group: {", ".join(group.participants)}\nAdd expenses like this: /pay {group.participants[0]} 12.50')


async def add_payment(update, context):
  group = context.chat_data.get('group')
  if group is None:
    await reply(update, NO_GROUP_TEXT)
    return
  if len(context.args) != 2:
    await reply(update, 'Please use this format: /pay Alice 12.50')
    return

  payer, amount_text = context.args
  if payer not in group.participants:
    await reply(update, f'{payer} is not in this group. The names are: {", ".join(group.participants)}')
    return
  try:
    amount = parse_amount(amount_text)
  except ValueError:
    await reply(update, 'Please enter an amount like 12.50')
    return

  group.add_expense(payer, amount)
  await reply(update, f'{payer} paid {format_amount(amount)}. Total so far: {format_amount(group.total_expenses())}')


async def show_status(update, context):
  group = context.chat_data.get('group')
  if group is None:
    await reply(update, NO_GROUP_TEXT)
    return

  paid = group.total_paid_by_participant()
  balance = group.balance_per_participant()
  lines = [
    f'Total: {format_amount(group.total_expenses())}',
    f'Share per person: {format_amount(group.expense_per_participant())}',
    '',
  ]
  lines += [f'{name}: paid {format_amount(paid[name])}, balance {format_amount(balance[name])}' for name in group.participants]
  await reply(update, '\n'.join(lines))


async def show_settlements(update, context):
  group = context.chat_data.get('group')
  if group is None:
    await reply(update, NO_GROUP_TEXT)
    return

  settlements = group.settle_balances()
  if not settlements:
    await reply(update, 'Nobody owes anything.')
    return
  await reply(update, '\n'.join(f'{debtor} pays {creditor} {format_amount(amount)}' for debtor, creditor, amount in settlements))


def add_handlers(application):
  application.add_handler(CommandHandler(['start', 'help'], show_help))
  application.add_handler(CommandHandler('new', new_group))
  application.add_handler(CommandHandler('pay', add_payment))
  application.add_handler(CommandHandler('status', show_status))
  application.add_handler(CommandHandler('settle', show_settlements))


def main():
  token = os.environ.get('TELEGRAM_BOT_TOKEN')
  if not token:
    raise SystemExit('Please set the TELEGRAM_BOT_TOKEN environment variable first.')

  application = Application.builder().token(token).build()
  add_handlers(application)
  application.run_polling()


if __name__ == '__main__':
  main()
