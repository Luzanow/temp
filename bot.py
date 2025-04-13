import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # ID операторів

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}  # user_id: {'phone': '', 'name': '', 'chat_active': True}
active_chats = {}  # user_id: operator_id
operator_chats = {}  # operator_id: user_id
TERMS_FILE_ID = "<your_telegram_file_id_for_pdf>"  # Замінити на дійсний file_id

# Клавіатури
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("📱 Поділитися номером", request_contact=True),
    KeyboardButton("📄 Умови використання Temp")
)

def chat_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("💬 Зв’язатися з оператором"))

def back_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("🔙 Повернутись назад"))

def end_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("🔚 Завершити розмову"))

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=main_keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=chat_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    try:
        await bot.send_document(message.chat.id, TERMS_FILE_ID)
    except:
        await message.answer("⚠️ Не вдалося завантажити файл.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['chat_active'] = True
    active_chats[uid] = None
    await message.answer("✍️ Опишіть свою проблему. Оператор відповість вам тут.", reply_markup=end_keyboard())
    asyncio.create_task(auto_end_chat(uid))

async def auto_end_chat(uid):
    await asyncio.sleep(600)  # 10 хвилин
    if uid in active_chats and active_chats[uid] is None:
        await bot.send_message(uid, "⌛ Розмову завершено через неактивність.", reply_markup=chat_keyboard())
        user_state[uid]['chat_active'] = False
        active_chats.pop(uid, None)

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    operator_id = active_chats.get(uid)
    if operator_id:
        await bot.send_message(operator_id, f"🔴 Користувач {uid} завершив розмову.")
        operator_chats.pop(operator_id, None)
    active_chats.pop(uid, None)
    user_state[uid]['chat_active'] = False
    await message.answer("✅ Розмову завершено.", reply_markup=chat_keyboard())

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('chat_active'))
async def user_to_operator(message: types.Message):
    uid = message.from_user.id
    name = user_state[uid].get('name', 'Невідомо')
    phone = user_state[uid].get('phone', '-')
    text = message.text
    for op in OPERATORS:
        await bot.send_message(op, f"📩 Повідомлення від {name} ({phone}, id:{uid}):\n{text}\n\nЩоб відповісти — просто натисни reply")
    await message.answer("✅ Повідомлення надіслано. Очікуйте відповідь.")

@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id in OPERATORS)
async def operator_reply(message: types.Message):
    original = message.reply_to_message.text
    uid = None
    for line in original.splitlines():
        if "id:" in line:
            uid = int(line.split("id:")[-1].replace(")", "").strip())
            break
    if uid:
        await bot.send_message(uid, f"👨‍💻 Відповідь оператора: {message.text}", reply_markup=end_keyboard())
        active_chats[uid] = message.from_user.id
        operator_chats[message.from_user.id] = uid

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
