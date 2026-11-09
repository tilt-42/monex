"""The Telegram front end, driven by buttons. Each chat has its own Group, kept in memory until the bot restarts."""

import os
from dataclasses import dataclass
from decimal import Decimal

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from monex.expenses import Group, format_amount, parse_amount, parse_name

HELP_TEXT = (
  'Pour quand vous avez la flemme de faire un tricount mais la flemme de faire les calculs.\n\n'
  'Tout se passe avec les boutons :\n\n'
  'Nouveau groupe : crée un groupe avec des prénoms (remplace le groupe existant)\n\n'
  'Ajouter une dépense : qui a payé, combien, et pour qui\n\n'
  'État des comptes : ce que chaque personne a payé et son solde\n\n'
  'Qui doit quoi : liste qui doit combien à qui\n\n'
  '/start affiche à nouveau les boutons.\n\n'
  'Les prénoms doivent encore être des mots tous seuls.'
)
NO_GROUP_TEXT = 'Y\'a pas de groupe encore ! Commences-en un avec le bouton Nouveau groupe.'
NAMES_PROMPT = 'Réponds à ce message avec les prénoms, séparés par des espaces (au moins deux).'
INVALID_NAMES_TEXT = 'Les prénoms ne peuvent contenir que des lettres, des chiffres, - et \'.\n\n' + NAMES_PROMPT
AMOUNT_PROMPT = 'Réponds à ce message avec le montant, par exemple 12.50.'
INVALID_AMOUNT_TEXT = 'Montant invalide.\n\n' + AMOUNT_PROMPT
EXPIRED_TEXT = 'Cette saisie n\'est plus active.'


@dataclass
class ExpenseDraft:
  """An expense being entered, tied to the message that shows its buttons."""
  message_id: int
  beneficiaries: list
  payer: str = ''
  amount_prompt_id: int = 0
  amount: Decimal = Decimal(0)


def needs_group(handler):
  async def wrapper(update, context):
    group = context.chat_data.get('group')
    if group is None:
      await update.callback_query.answer(NO_GROUP_TEXT, show_alert=True)
      return
    await handler(update, context, group)
  return wrapper


def needs_draft(handler):
  """Ignore taps on old messages, so a double tap can't record an expense twice."""
  async def wrapper(update, context):
    query = update.callback_query
    draft = context.chat_data.get('draft')
    if draft is None or draft.message_id != query.message.message_id:
      await query.answer(EXPIRED_TEXT, show_alert=True)
      return
    await handler(update, context, draft)
  return wrapper


def button(label, data):
  return InlineKeyboardButton(label, callback_data=data)


def in_rows(buttons, per_row=2):
  return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def menu_text(group):
  if group is None:
    return 'Pas encore de groupe.'
  return f'Groupe : {", ".join(group.participants)}'


def menu_keyboard(group):
  new_group_row = [button('👥 Nouveau groupe', 'menu:new')]
  if group is None:
    return InlineKeyboardMarkup([new_group_row])
  return InlineKeyboardMarkup([
    [button('➕ Ajouter une dépense', 'menu:expense')],
    [button('📊 État des comptes', 'menu:status'), button('💸 Qui doit quoi', 'menu:settle')],
    new_group_row,
  ])


def payer_keyboard(group):
  names = [button(name, f'payer:{i}') for i, name in enumerate(group.participants)]
  return InlineKeyboardMarkup(in_rows(names) + [[button('❌ Annuler', 'cancel')]])


def beneficiaries_keyboard(group, draft):
  names = [
    button(f'{"✅" if name in draft.beneficiaries else "⬜"} {name}', f'for:{i}')
    for i, name in enumerate(group.participants)
  ]
  return InlineKeyboardMarkup(in_rows(names) + [[button('✅ Valider', 'for:done'), button('❌ Annuler', 'cancel')]])


def beneficiaries_text(draft):
  return f'{draft.payer} a payé {format_amount(draft.amount)}.\n\nPour qui ? Touche un prénom pour le cocher ou le décocher.'


async def show_screen(query, text, keyboard=None):
  await query.answer()
  try:
    await query.edit_message_text(text, reply_markup=keyboard)
  except BadRequest as error:
    # Telegram refuses an edit that changes nothing, for example after a double tap.
    if 'not modified' not in str(error).lower():
      raise


async def show_result(update, context, text):
  """Leave the result in the chat history and open a fresh menu below it."""
  query = update.callback_query
  context.chat_data.pop('draft', None)
  await show_screen(query, text)
  group = context.chat_data.get('group')
  await context.bot.send_message(query.message.chat_id, menu_text(group), reply_markup=menu_keyboard(group))


async def show_help(update, context):
  await update.effective_message.reply_text(HELP_TEXT, reply_markup=menu_keyboard(context.chat_data.get('group')))


async def ask_by_reply(chat_id, context, text, placeholder):
  """Ask for typed text. It must come as a reply, because bots don't see other messages in groups."""
  prompt = await context.bot.send_message(chat_id, text, reply_markup=ForceReply(input_field_placeholder=placeholder))
  return prompt.message_id


async def ask_for_names(chat_id, context, text=NAMES_PROMPT):
  context.chat_data['names_prompt_id'] = await ask_by_reply(chat_id, context, text, 'Alice Bob Carol')


async def ask_for_amount(chat_id, context, draft, text=AMOUNT_PROMPT):
  draft.amount_prompt_id = await ask_by_reply(chat_id, context, text, '12.50')


async def receive_reply(update, context):
  replied_to = update.effective_message.reply_to_message.message_id
  draft = context.chat_data.get('draft')
  if replied_to == context.chat_data.get('names_prompt_id'):
    await receive_names(update, context)
  elif draft is not None and replied_to == draft.amount_prompt_id:
    await receive_amount(update, context, draft)


async def start_new_group(update, context):
  query = update.callback_query
  await query.answer()
  await ask_for_names(query.message.chat_id, context)


async def receive_names(update, context):
  message = update.effective_message
  try:
    group = Group(parse_name(name) for name in message.text.replace(',', ' ').split())
  except ValueError:
    await ask_for_names(message.chat_id, context, INVALID_NAMES_TEXT)
    return

  if len(group.participants) < 2:
    await ask_for_names(message.chat_id, context)
    return

  context.chat_data['group'] = group
  context.chat_data.pop('names_prompt_id')
  context.chat_data.pop('draft', None)
  await message.reply_text(menu_text(group), reply_markup=menu_keyboard(group))


@needs_group
async def start_expense(update, context, group):
  query = update.callback_query
  context.chat_data['draft'] = ExpenseDraft(query.message.message_id, list(group.participants))
  await show_screen(query, 'Qui a payé ?', payer_keyboard(group))


@needs_draft
async def choose_payer(update, context, draft):
  query = update.callback_query
  if draft.payer:  # A double tap must not ask for the amount twice.
    await query.answer()
    return

  draft.payer = context.chat_data['group'].participants[int(query.data.split(':')[1])]
  await show_screen(query, f'{draft.payer} a payé combien ?', InlineKeyboardMarkup([[button('❌ Annuler', 'cancel')]]))
  await ask_for_amount(query.message.chat_id, context, draft)


async def receive_amount(update, context, draft):
  message = update.effective_message
  try:
    draft.amount = parse_amount(message.text)
  except ValueError:
    await ask_for_amount(message.chat_id, context, draft, INVALID_AMOUNT_TEXT)
    return

  # From here the buttons live on a new message, below the typed amount.
  previous_message_id = draft.message_id
  sent = await message.reply_text(beneficiaries_text(draft), reply_markup=beneficiaries_keyboard(context.chat_data['group'], draft))
  draft.message_id = sent.message_id
  draft.amount_prompt_id = 0
  await context.bot.edit_message_reply_markup(message.chat_id, previous_message_id, reply_markup=None)


@needs_draft
async def toggle_beneficiary(update, context, draft):
  query = update.callback_query
  group = context.chat_data['group']
  name = group.participants[int(query.data.split(':')[1])]
  if name in draft.beneficiaries:
    draft.beneficiaries.remove(name)
  else:
    draft.beneficiaries.append(name)
  await show_screen(query, beneficiaries_text(draft), beneficiaries_keyboard(group, draft))


@needs_draft
async def confirm_expense(update, context, draft):
  group = context.chat_data['group']
  beneficiaries = [name for name in group.participants if name in draft.beneficiaries]
  if not beneficiaries:
    await update.callback_query.answer('Coche au moins une personne.', show_alert=True)
    return

  group.add_expense(draft.payer, draft.amount, beneficiaries)
  paid_for = 'everyone' if len(beneficiaries) == len(group.participants) else ', '.join(beneficiaries)
  await show_result(update, context, f'{draft.payer} paid {format_amount(draft.amount)} for {paid_for}. Total so far: {format_amount(group.total_expenses())}')


@needs_draft
async def cancel_expense(update, context, draft):
  context.chat_data.pop('draft')
  group = context.chat_data['group']
  await show_screen(update.callback_query, menu_text(group), menu_keyboard(group))


@needs_group
async def show_status(update, context, group):
  paid = group.total_paid_by_participant()
  shares = group.share_per_participant()
  balance = group.balance_per_participant()
  lines = [f'Total: {format_amount(group.total_expenses())}', '']
  lines += [f'{name}: paid {format_amount(paid[name])}, share {format_amount(shares[name])}, balance {format_amount(balance[name])}' for name in group.participants]
  await show_result(update, context, '\n'.join(lines))


@needs_group
async def show_settlements(update, context, group):
  settlements = group.settle_balances()
  if not settlements:
    await show_result(update, context, 'Nobody owes anything.')
    return
  await show_result(update, context, '\n'.join(f'{debtor} pays {creditor} {format_amount(amount)}' for debtor, creditor, amount in settlements))


def add_handlers(application):
  application.add_handler(CommandHandler(['start', 'help'], show_help))
  # Commands are included so that a reply like "/pay Bob" gets refused instead of ignored.
  application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, receive_reply))
  application.add_handler(CallbackQueryHandler(start_new_group, pattern='^menu:new$'))
  application.add_handler(CallbackQueryHandler(start_expense, pattern='^menu:expense$'))
  application.add_handler(CallbackQueryHandler(show_status, pattern='^menu:status$'))
  application.add_handler(CallbackQueryHandler(show_settlements, pattern='^menu:settle$'))
  application.add_handler(CallbackQueryHandler(choose_payer, pattern='^payer:'))
  application.add_handler(CallbackQueryHandler(confirm_expense, pattern='^for:done$'))
  application.add_handler(CallbackQueryHandler(toggle_beneficiary, pattern='^for:'))
  application.add_handler(CallbackQueryHandler(cancel_expense, pattern='^cancel$'))


def main():
  token = os.environ.get('TELEGRAM_BOT_TOKEN')
  if not token:
    raise SystemExit('Please set the TELEGRAM_BOT_TOKEN environment variable first.')

  application = Application.builder().token(token).build()
  add_handlers(application)
  application.run_polling()


if __name__ == '__main__':
  main()
