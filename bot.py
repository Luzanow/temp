import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
timeout_tasks = {}

TERMS_FILE = "full_temp_terms.pdf"

# Старт
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        del active_chats[user_id]
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

# Надсилання PDF з умовами
@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    try:
        with open(TERMS_FILE, 'rb') as doc:
            await message.answer_document(doc)
    except FileNotFoundError:
        await message.answer("⚠️ Умови використання не знайдено.")

# Отримання номера телефону
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {
        'phone': message.contact.phone_number,
        'step': 'get_name'
    }
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=ReplyKeyboardRemove())

# Введення імені
@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('step') == 'get_name')
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    user_state[message.from_user.id]['step'] = 'waiting_operator'
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

# Запит на зв'язок з оператором
@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def contact_operator(message: types.Message):
    uid = message.from_user.id
    if uid in timeout_tasks:
        timeout_tasks[uid].cancel()
    active_chats[uid] = {'user': uid, 'operator': None, 'active': True}
    user_state[uid]['step'] = 'chatting'
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор відповість вам тут.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову"))
    timeout_tasks[uid] = asyncio.create_task(close_chat_if_idle(uid))

async def close_chat_if_idle(uid):
    await asyncio.sleep(600)
    if active_chats.get(uid, {}).get('active'):
        active_chats[uid]['active'] = False
        await bot.send_message(uid, "⌛ Чат завершено через неактивність. Поверніться в меню /start")
        for op in OPERATORS:
            await bot.send_message(op, f"⚠️ Користувач {uid} завершив розмову через неактивність.")

# Обробка повідомлень від користувача
@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id, {}).get('active'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    user = user_state.get(uid)
    text = f"📩 Повідомлення від <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{message.text}"
    for op in OPERATORS:
        msg_sent = await bot.send_message(op, text, parse_mode='HTML')
        active_chats[uid]['operator'] = msg_sent.chat.id
    timeout_tasks[uid].cancel()
    timeout_tasks[uid] = asyncio.create_task(close_chat_if_idle(uid))

# Відповідь оператора через reply
@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id in OPERATORS)
async def operator_reply(message: types.Message):
    try:
        lines = message.reply_to_message.text.split("\n")
        phone_line = next((line for line in lines if line.startswith("📩 Повідомлення від")), None)
        if not phone_line:
            return await message.answer("❌ Не вдалося визначити користувача.")
        uid = None
        for key, val in user_state.items():
            if val.get("phone") in message.reply_to_message.text:
                uid = key
                break
        if not uid:
            return await message.answer("❌ Не вдалося визначити користувача.")
        await bot.send_message(uid, f"💬 Відповідь оператора: {message.text}")
    except:
        await message.answer("⚠️ Помилка надсилання відповіді користувачу.")

# Завершити розмову
@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        active_chats[uid]['active'] = False
        await message.answer("✅ Розмову завершено. Поверніться в меню /start", reply_markup=ReplyKeyboardRemove())
        for op in OPERATORS:
            await bot.send_message(op, f"✅ Користувач {uid} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
