import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
OPERATORS = [5498505652]  # Список ID операторів

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
waiting_operators = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    return kb

def finish_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

def accept_chat_keyboard(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Взяти в роботу", callback_data=f"accept_{user_id}"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    await message.answer("👋 Привіт! Поділіться номером телефону, щоб розпочати спілкування.", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def name_handler(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("❓ Опишіть ваше питання або проблему:")

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'problem' not in user_state[msg.from_user.id] and 'name' in user_state[msg.from_user.id])
async def problem_handler(message: types.Message):
    user_state[message.from_user.id]['problem'] = message.text
    for operator_id in OPERATORS:
        try:
            await bot.send_message(
                operator_id,
                f"📩 Нова заявка!
<b>Ім'я:</b> {user_state[message.from_user.id]['name']}
<b>Телефон:</b> {user_state[message.from_user.id]['phone']}
<b>Проблема:</b> {user_state[message.from_user.id]['problem']}",
                reply_markup=accept_chat_keyboard(message.from_user.id)
            )
        except BotBlocked:
            continue
    await message.answer("🛎️ Вас вітає служба підтримки TEMP! Очікуйте відповіді оператора.")

    # Запуск таймера очікування 5 хвилин
    asyncio.create_task(check_operator_response(message.from_user.id))

async def check_operator_response(user_id):
    await asyncio.sleep(300)  # 5 хвилин
    if user_id not in active_chats:
        await bot.send_message(user_id, "⏳ Вибачте, всі оператори зараз зайняті. Ми швидко знайдемо для вас спеціаліста, будь ласка, очікуйте.")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('accept_'))
async def accept_chat(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    operator_id = callback_query.from_user.id
    active_chats[user_id] = operator_id
    active_chats[operator_id] = user_id

    await bot.send_message(operator_id, f"✅ Ви взяли користувача {user_state[user_id]['name']} у роботу. Тепер ви можете спілкуватись. Натисніть 'Завершити розмову' для завершення.", reply_markup=finish_keyboard())
    await bot.send_message(user_id, "🧑‍💻 Оператор TEMP приєднався до чату. Ви можете ставити питання.", reply_markup=finish_keyboard())

    await callback_query.answer()

@dp.message_handler(lambda message: message.from_user.id in active_chats)
async def chat_handler(message: types.Message):
    partner_id = active_chats.get(message.from_user.id)
    if not partner_id:
        return
    prefix = "💬 Ваша відповідь:"
    if message.from_user.id in OPERATORS:
        prefix = f"💬 Відповідь оператора TEMP:"
    try:
        await bot.send_message(partner_id, f"{prefix}\n{message.text}")
    except BotBlocked:
        pass

@dp.message_handler(lambda message: message.text == "🔙 Завершити розмову")
async def finish_chat(message: types.Message):
    partner_id = active_chats.get(message.from_user.id)
    if partner_id:
        await bot.send_message(partner_id, "🔚 Розмову завершено. Натисніть /start, щоб почати нову сесію.", reply_markup=types.ReplyKeyboardRemove())
        active_chats.pop(partner_id, None)
    active_chats.pop(message.from_user.id, None)
    await message.answer("🔚 Розмову завершено. Натисніть /start для нової сесії.", reply_markup=types.ReplyKeyboardRemove())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
