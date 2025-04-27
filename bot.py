import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання Temp"))
    return kb

def contact_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Зв'язатися з оператором"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    await message.answer("👋 Вітаємо! Поділіться номером телефону або перегляньте умови використання.", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Натисніть нижче, щоб зв'язатися з оператором.", reply_markup=contact_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    try:
        doc = InputFile("full_temp_terms.pdf")
        await bot.send_document(message.chat.id, doc, caption="📎 Ознайомтесь з умовами використання")
    except:
        await message.answer("⚠️ Не вдалося знайти файл умов.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв'язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user = user_state.get(user_id)
    if not user:
        return await message.answer("⚠️ Почніть із /start та поділіться номером.")
    user_state[user_id]['chat_active'] = True
    active_chats[user_id] = True
    await message.answer("📝 Опишіть вашу проблему.", reply_markup=back_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"📨 Нове звернення від <b>{user['name']}</b> <code>{user['phone']}</code>.", parse_mode='HTML')

@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id))
async def relay_to_operator(message: types.Message):
    user = user_state.get(message.from_user.id)
    if not user:
        return
    for op in OPERATORS:
        await bot.send_message(op, f"✉️ <b>{user['name']}</b>: {message.text}", parse_mode='HTML')

@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    user_state.get(user_id, {}).pop('chat_active', None)
    await message.answer("🔚 Розмову завершено. Натисніть /start, щоб почати знову.", reply_markup=types.ReplyKeyboardRemove())
    for op in OPERATORS:
        await bot.send_message(op, f"🔔 {user_state.get(user_id, {}).get('name', 'Користувач')} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
