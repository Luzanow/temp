import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("7862608221:AAFANx6YmUG2IPRiQp9l_ejOHTc12PEABCY"
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Подiлитися номером", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання Temp"))
    return kb

def contact_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Зв’язатися з оператором"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Обробка /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Вiтаємо! Подiлiться номером телефону або перегляньте умови.", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введiть ваше iм’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Натиснiть, щоб зв’язатися з оператором.", reply_markup=contact_keyboard())

# Умови використання
@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    try:
        doc = InputFile("full_temp_terms.pdf")
        await bot.send_document(message.chat.id, doc, caption="📎 Ознайомтесь з умовами використання")
    except:
        await message.answer("⚠️ Не вдалося знайти файл умов.")

# Зв'язок з оператором
@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user = user_state.get(user_id, {})
    if not user:
        return await message.answer("⚠️ Помилка. Спочатку подiлiться номером телефону.")
    user_state[user_id]['chat_active'] = True
    active_chats[user_id] = True
    await message.answer("📝 Опишiть вашу проблему нижче.", reply_markup=back_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"📨 Нове звернення вiд <b>{user['name']}</b> <code>{user['phone']}</code>.\nЩоб вiдповiсти, просто свайпнiть на повiдомлення.", parse_mode='HTML')

# Переписка
@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id))
async def relay_to_operator(message: types.Message):
    user = user_state.get(message.from_user.id)
    if not user:
        return
    for op in OPERATORS:
        await bot.send_message(op, f"✉️ <b>{user['name']}</b>: {message.text}", parse_mode='HTML')

@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id in OPERATORS)
async def operator_reply(message: types.Message):
    reply_text = message.reply_to_message.text
    try:
        user_id_line = [line for line in reply_text.split('\n') if '>' not in line][-1]
        name = user_id_line.split(':')[0].replace('✉️', '').strip()
        user_id = next((uid for uid, data in user_state.items() if data.get('name') == name), None)
        if not user_id:
            return await message.reply("⚠️ Не вдалося визначити користувача")
        await bot.send_message(user_id, f"💬 Вiдповiдь оператора: {message.text}")
    except Exception as e:
        await message.reply("❌ Помилка вiдповiдi користувачу")

# Завершення
@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    user_state[user_id]['chat_active'] = False
    await message.answer("🔚 Розмову завершено. Натиснiть /start, щоб почати знову.", reply_markup=types.ReplyKeyboardRemove())
    for op in OPERATORS:
        await bot.send_message(op, f"🔔 Користувач {user_state[user_id]['name']} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
