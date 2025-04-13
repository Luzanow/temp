import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o") or "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_ID = 5498505652  # ID оператора
PDF_PATH = "temp_terms_fixed.pdf"  # ваш PDF

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# Стани та таймери
user_data = defaultdict(dict)
active_chats = {}
timers = {}

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add("📄 Умови використання Temp")
    return kb

def get_chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💬 Зв’язатися з оператором")
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 Завершити розмову")
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    await message.answer("👋 Привіт! Щоб почати, поділіться номером або перегляньте умови.", reply_markup=get_main_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_contact(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]['phone'] = message.contact.phone_number
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda m: m.text and 'phone' in user_data.get(m.from_user.id, {}) and 'name' not in user_data[m.from_user.id])
async def get_name(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]['name'] = message.text
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=get_chat_keyboard())

@dp.message_handler(lambda m: m.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    if os.path.exists(PDF_PATH):
        await message.answer_document(InputFile(PDF_PATH))
    else:
        await message.answer("❌ Файл умов не знайдено.")

@dp.message_handler(lambda m: m.text == "💬 Зв’язатися з оператором")
async def connect_operator(message: types.Message):
    user_id = message.from_user.id
    active_chats[user_id] = ADMIN_ID
    await message.answer("📝 Опишіть вашу проблему. Ми вам відповімо.", reply_markup=back_keyboard())
    # Запуск таймера на 10 хв
    if user_id in timers:
        timers[user_id].cancel()
    timers[user_id] = asyncio.create_task(timeout_checker(user_id))

async def timeout_checker(user_id):
    await asyncio.sleep(600)
    if user_id in active_chats:
        await bot.send_message(user_id, "⌛ Розмову завершено через неактивність.", reply_markup=get_chat_keyboard())
        await bot.send_message(ADMIN_ID, f"❌ Розмова з користувачем {user_data[user_id].get('name')} завершена через неактивність.")
        active_chats.pop(user_id, None)

@dp.message_handler(lambda m: m.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        await message.answer("✅ Ви завершили розмову.", reply_markup=get_chat_keyboard())
        await bot.send_message(ADMIN_ID, f"❌ Користувач {user_data[user_id].get('name')} завершив розмову.")
        active_chats.pop(user_id, None)
        if user_id in timers:
            timers[user_id].cancel()

@dp.message_handler(lambda message: message.reply_to_message and message.from_user.id == ADMIN_ID and '/reply' not in message.text)
async def reply_from_operator(message: types.Message):
    try:
        user_id = int(message.reply_to_message.text.split()[2])
        await bot.send_message(user_id, f"💬 Відповідь від оператора:\n{message.text}", reply_markup=back_keyboard())
    except Exception:
        await message.reply("❗ Не вдалося відповісти.")

@dp.message_handler()
async def relay_message(message: types.Message):
    user_id = message.from_user.id
