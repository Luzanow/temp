# telegram_support_bot.py

import os
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import MessageNotModified
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS = [5498505652]  # замість ADMIN_ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

# Стани
class ChatState(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    active_chat = State()

# Сесії користувачів
user_sessions = {}  # user_id: {"accepted": False, "operator_id": None, "last_active": datetime}

# Кнопка поділитись номером
phone_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_keyboard.add(types.KeyboardButton("📞 Поділитись номером", request_contact=True))

# Головне меню (у користувача)
def start_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💬 Зв’язатись з оператором", callback_data="contact_operator"))
    return kb

# Старт бота
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_sessions.pop(message.from_user.id, None)
    await message.answer("🙋️ Вітаємо! Натисніть кнопку нижче, щоб почати.", reply_markup=start_keyboard())

# Користувач хоче зв'язатися
@dp.callback_query_handler(lambda c: c.data == "contact_operator")
async def contact_operator(callback_query: types.CallbackQuery, state: FSMContext):
    await ChatState.waiting_name.set()
    await callback_query.message.answer("👤 Як вас звати?", reply_markup=ReplyKeyboardRemove())
    await callback_query.answer()

@dp.message_handler(state=ChatState.waiting_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await ChatState.waiting_phone.set()
    await message.answer("📞 Поділіться номером або введіть вручну:", reply_markup=phone_keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT, state=ChatState.waiting_phone)
@dp.message_handler(lambda m: True, state=ChatState.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)

    data = await state.get_data()
    name = data['name']
    user_id = message.from_user.id
    user_sessions[user_id] = {"accepted": False, "operator_id": None, "last_active": datetime.now()}

    for op_id in OPERATORS:
        try:
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Прийняти", callback_data=f"accept_{user_id}")
            )
            await bot.send_message(op_id, f"🔔 Нове звернення:

• Ім’я: {name}
• Телефон: {phone}", reply_markup=kb)
        except Exception as e:
            logging.error(f"Помилка надсилання оператору: {e}")

    await state.finish()
    await message.answer("⏳ Очікуйте, оператор з’єднається з вами...", reply_markup=ReplyKeyboardRemove())

# Оператор приймає
@dp.callback_query_handler(lambda c: c.data.startswith("accept_"))
async def accept_chat(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    if user_id in user_sessions:
        user_sessions[user_id]["accepted"] = True
        user_sessions[user_id]["operator_id"] = callback_query.from_user.id
        user_sessions[user_id]["last_active"] = datetime.now()

        await bot.send_message(user_id, "👨‍💻 Оператор підключився. Можете писати.")
        await bot.send_message(callback_query.from_user.id, "✅ Ви прийняли звернення. Напишіть відповідь або натисніть Завершити:",
                               reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Завершити", callback_data=f"end_{user_id}")))
    await callback_query.answer()

# Користувач надсилає повідомлення
@dp.message_handler(lambda m: m.from_user.id in user_sessions)
async def handle_user_message(message: types.Message):
    session = user_sessions.get(message.from_user.id)
    if not session or not session.get("accepted"):
        await message.answer("⛔ Очікуйте, оператор ще не підключився.")
        return

    operator_id = session["operator_id"]
    user_sessions[message.from_user.id]["last_active"] = datetime.now()
    await bot.send_message(operator_id, f"👤 Користувач:
{message.text}")

# Оператор надсилає відповідь
@dp.message_handler(lambda m: m.from_user.id in OPERATORS)
async def handle_operator_message(message: types.Message):
    for user_id, session in user_sessions.items():
        if session.get("operator_id") == message.from_user.id and session.get("accepted"):
            await bot.send_message(user_id, f"👨‍💻 Оператор:
{message.text}")
            user_sessions[user_id]["last_active"] = datetime.now()
            break

# Завершення чату
@dp.callback_query_handler(lambda c: c.data.startswith("end_"))
async def end_chat(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    if user_id in user_sessions:
        await bot.send_message(user_id, "❌ Чат завершено. Дякуємо за звернення!")
        await bot.send_message(callback_query.from_user.id, "✅ Ви завершили чат.")
        user_sessions.pop(user_id)
    await callback_query.answer()

# Перевірка неактивності (10 хв)
async def monitor_timeouts():
    while True:
        now = datetime.now()
        to_remove = []
        for user_id, session in user_sessions.items():
            if session.get("accepted") and now - session["last_active"] > timedelta(minutes=10):
                await bot.send_message(user_id, "❌ Чат завершено через неактивність.")
                await bot.send_message(session["operator_id"], f"⚠️ Чат з користувачем {user_id} завершено через неактивність.")
                to_remove.append(user_id)
        for uid in to_remove:
            user_sessions.pop(uid)
        await asyncio.sleep(60)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_timeouts())
    executor.start_polling(dp, skip_updates=True)
