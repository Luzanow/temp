import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")  # Ваш токен у .env файлі
OPERATORS = [5498505652]  # ID операторів
OPERATOR_NAME = "TEMP Support"  # Ім'я оператора у відповідях

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}  # Стани користувачів
active_chats = {}  # Активні чати

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання"))
    return kb

def contact_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Зв'язатися з оператором"))
    return kb

def end_chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити розмову"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    await message.answer("👋 Вітаємо в службі підтримки TEMP! Поділіться номером телефону або перегляньте умови використання.", reply_markup=start_keyboard())

# Отримання номера
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=ReplyKeyboardRemove())

# Отримання імені та питання
@dp.message_handler(lambda message: message.from_user.id in user_state and 'name' not in user_state[message.from_user.id])
async def name_handler(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("📝 Опишіть, будь ласка, вашу проблему або питання:")

@dp.message_handler(lambda message: message.from_user.id in user_state and 'issue' not in user_state[message.from_user.id] and 'name' in user_state[message.from_user.id])
async def issue_handler(message: types.Message):
    user_state[message.from_user.id]['issue'] = message.text
    user_state[message.from_user.id]['chat_active'] = True
    active_chats[message.from_user.id] = True

    # Повідомлення операторам про нову заявку
    for operator_id in OPERATORS:
        await bot.send_message(operator_id, 
            f"🚀 Нова заявка!

👤 Користувач: <b>{user_state[message.from_user.id]['name']}</b>
📞 Номер: <b>{user_state[message.from_user.id]['phone']}</b>

💬 Питання:
<code>{user_state[message.from_user.id]['issue']}</code>",
            parse_mode='HTML')

    await message.answer("✅ Дякуємо! Ваше звернення прийняте. Очікуйте відповідь оператора.", reply_markup=end_chat_keyboard())

# Надсилання повідомлень оператору
@dp.message_handler(lambda message: active_chats.get(message.from_user.id))
async def forward_user_message(message: types.Message):
    user = user_state.get(message.from_user.id)
    if not user:
        return
    for operator_id in OPERATORS:
        await bot.send_message(operator_id, 
            f"📨 Повідомлення від <b>{user['name']}</b>:
{message.text}",
            parse_mode='HTML')

# Оператор відповідає свайпом (Reply)
@dp.message_handler(lambda message: message.reply_to_message and message.from_user.id in OPERATORS)
async def operator_reply(message: types.Message):
    try:
        replied_text = message.reply_to_message.text
        name_line = replied_text.split('\n')[0]
        username = name_line.split(':')[1].strip()

        # Знайти ID користувача за ім'ям
        target_user_id = None
        for user_id, data in user_state.items():
            if data.get('name') == username:
                target_user_id = user_id
                break

        if target_user_id:
            await bot.send_message(target_user_id, f"💬 Відповідь оператора {OPERATOR_NAME}:
{message.text}")
    except Exception as e:
        await message.reply("⚠️ Помилка: не вдалося відправити відповідь користувачу.")

# Завершення розмови
@dp.message_handler(lambda message: message.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    user_state.pop(user_id, None)
    await message.answer("🔔 Розмову завершено. Натисніть /start, щоб почати нове звернення.", reply_markup=ReplyKeyboardRemove())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
