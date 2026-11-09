"""The Telegram front end. Each chat has its own Group, kept in memory until the bot restarts."""

import os

from telegram.ext import Application, CommandHandler

from monex.expenses import Group, format_amount, parse_amount

HELP_TEXT = (
  'Pour quand vous avez la flemme de faire un tricount mais la flemme de faire les calculs.\n\n'
  '/new Alice Bob Carol Dave: crée un nouveau groupe avec ces prénoms (remplace un groupe existant)\n'
  '/pay Alice 12.50: indique qu\'Alice a payé 12.50 pour tout le monde\n'
  '/pay Alice 12.50 Bob Carol: indique qu\'Alice a payé 12.50 pour Bob et Carol seulement\n'
  '/status: montre ce que chaque personne a payé et l\'état actuel des comptes\n'
  '/settle: liste qui doit combien à qui\n'
  '/help: montre ce message\n\n'
  'Les prénoms doivent encore être des mots tous seuls.'
)
NO_GROUP_TEXT = 'Y\'a pas de groupe encore ! Commences-en un avec /new Alice Bob'


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
  if len(context.args) < 2:
    await reply(update, 'Please use this format: /pay Alice 12.50 or /pay Alice 12.50 Bob Carol')
    return

  payer, amount_text, *beneficiaries = context.args
  unknown = [name for name in (payer, *beneficiaries) if name not in group.participants]
  if unknown:
    await reply(update, f'Not in this group: {", ".join(unknown)}. The names are: {", ".join(group.participants)}')
    return
  try:
    amount = parse_amount(amount_text)
  except ValueError:
    await reply(update, 'Please enter an amount like 12.50')
    return

  group.add_expense(payer, amount, beneficiaries)
  paid_for = ', '.join(dict.fromkeys(beneficiaries)) or 'everyone'
  await reply(update, f'{payer} paid {format_amount(amount)} for {paid_for}. Total so far: {format_amount(group.total_expenses())}')


async def show_status(update, context):
  group = context.chat_data.get('group')
  if group is None:
    await reply(update, NO_GROUP_TEXT)
    return

  paid = group.total_paid_by_participant()
  shares = group.share_per_participant()
  balance = group.balance_per_participant()
  lines = [f'Total: {format_amount(group.total_expenses())}', '']
  lines += [f'{name}: paid {format_amount(paid[name])}, share {format_amount(shares[name])}, balance {format_amount(balance[name])}' for name in group.participants]
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
