from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

active_chats = {}

# Стартова клавіатура
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитись номером", request_contact=True))
    return kb

# Оператор може прийняти чат
def operator_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("👥 Прийняти чат"))
    return kb

# Кнопка завершення розмови
def end_chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Завершити чат"))
    return kb

# Підключення користувача
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("👋 Вітаємо у службі підтримки TEMP! Надішліть свій номер телефону, натиснувши кнопку нижче.", reply_markup=start_keyboard())

# Обробка контактів користувача
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    # Зберігаємо дані користувача
    active_chats[user_id] = {"phone": phone_number}
    await message.answer("📝 Введіть ваше ім'я:")

# Обробка імені користувача
@dp.message_handler(lambda message: message.from_user.id in active_chats and "name" not in active_chats[message.from_user.id])
async def name_handler(message: types.Message):
    user_id = message.from_user.id
    active_chats[user_id]["name"] = message.text
    await message.answer("📝 Опишіть вашу проблему або запитання:")

# Обробка запитання користувача
@dp.message_handler(lambda message: message.from_user.id in active_chats and "question" not in active_chats[message.from_user.id])
async def question_handler(message: types.Message):
    user_id = message.from_user.id
    active_chats[user_id]["question"] = message.text
    await message.answer("⏳ Очікуйте, ми передаємо ваше звернення оператору.", reply_markup=operator_keyboard())

# Прийом чату оператором
@dp.message_handler(lambda message: message.text == "👥 Прийняти чат" and message.from_user.id in OPERATORS)
async def accept_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        operator_id = message.from_user.id
        # Повідомлення користувачу
        await bot.send_message(user_id, "👨‍💻 Оператор приєднався до чату, можете почати спілкування!")
        # Повідомлення оператору
        await bot.send_message(operator_id, "✅ Ви підключилися до чату. Почніть спілкування з користувачем.")
        # Додаємо чат до активних
        active_chats[user_id]['operator_id'] = operator_id

# Завершення чату
@dp.message_handler(lambda message: message.text == "❌ Завершити чат" and message.from_user.id in active_chats)
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        operator_id = active_chats[user_id]["operator_id"]
        await bot.send_message(operator_id, "🔔 Користувач завершив чат.")
        await bot.send_message(user_id, "✅ Розмову завершено. Дякуємо за використання нашої підтримки!")
        active_chats.pop(user_id, None)

# Повідомлення від користувача після прийняття чату
@dp.message_handler(lambda message: message.from_user.id in active_chats)
async def user_message(message: types.Message):
    operator_id = active_chats[message.from_user.id]["operator_id"]
    await bot.send_message(operator_id, f"👤 {active_chats[message.from_user.id]['name']} пише:\n{message.text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
