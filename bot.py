import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")  # Обов'язково додай токен у змінні середовища
OPERATORS = [5498505652]  # ID операторів

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Надіслати номер телефону", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання TEMP"))
    return kb

def chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Старт бота
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    await message.answer(
        "👋 Привіт! Поділіться своїм номером телефону, щоб почати спілкування.",
        reply_markup=start_keyboard()
    )

# Приймаємо контакт
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Як до вас звертатися? Введіть ваше ім'я:", reply_markup=types.ReplyKeyboardRemove())

# Приймаємо ім'я
@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("📝 Коротко опишіть вашу проблему або запитання:")

# Приймаємо питання
@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'problem' not in user_state[msg.from_user.id] and 'name' in user_state[msg.from_user.id])
async def handle_problem(message: types.Message):
    user_state[message.from_user.id]['problem'] = message.text
    user_state[message.from_user.id]['chat_active'] = True
    active_chats[message.from_user.id] = True

    await message.answer(
        "🫰 Дякуємо! Вас вітає служба підтримки TEMP. Очікуйте під'єднання оператора.",
        reply_markup=chat_keyboard()
    )

    for op_id in OPERATORS:
        await bot.send_message(
            op_id,
            f"📢 Нова заявка!
<b>Ім'я:</b> {user_state[message.from_user.id]['name']}
<b>Телефон:</b> {user_state[message.from_user.id]['phone']}
<b>Питання:</b> {user_state[message.from_user.id]['problem']}\n\nНатисніть "/accept_{message.from_user.id}" щоб прийняти."
        )

# Оператор приймає чат
@dp.message_handler(lambda msg: msg.text.startswith("/accept_"))
async def accept_chat(message: types.Message):
    try:
        user_id = int(message.text.split("_", 1)[1])
        if user_id in user_state:
            user_state[user_id]['operator_id'] = message.from_user.id
            await bot.send_message(user_id, f"✅ Оператор {message.from_user.first_name} приєднався до чату! Ви можете писати.")
            await bot.send_message(message.from_user.id, "🧑‍💻 Ви приєдналися до користувача. Спілкуйтеся вільно!")
    except Exception as e:
        await message.reply("⚠️ Помилка прийняття чату")

# Спілкування
@dp.message_handler()
async def relay_messages(message: types.Message):
    if message.from_user.id in user_state and user_state[message.from_user.id].get('chat_active'):
        # Відправка повідомлення користувача оператору
        operator_id = user_state[message.from_user.id].get('operator_id')
        if operator_id:
            await bot.send_message(operator_id, f"💬 {user_state[message.from_user.id]['name']}: {message.text}")
    elif message.from_user.id in [op for op in OPERATORS]:
        # Відповідь оператора
        for uid, info in user_state.items():
            if info.get('operator_id') == message.from_user.id and info.get('chat_active'):
                await bot.send_message(uid, f"💬 Відповідь оператора TEMP {message.from_user.first_name}: {message.text}")

# Завершення розмови
@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_state:
        operator_id = user_state[user_id].get('operator_id')
        user_state[user_id]['chat_active'] = False
        active_chats.pop(user_id, None)

        await message.answer("🔚 Розмову завершено. Натисніть /start щоб почати знову.", reply_markup=types.ReplyKeyboardRemove())
        if operator_id:
            await bot.send_message(operator_id, f"🔔 Користувач {user_state[user_id]['name']} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
