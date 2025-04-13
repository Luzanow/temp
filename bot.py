import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o")
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
operator_reply_mode = {}
active_chats = {}
timeouts = {}

TERMS_FILE_PATH = "terms.pdf"

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Натисніть нижче, щоб почати розмову з оператором.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await message.answer_document(InputFile(TERMS_FILE_PATH))
    else:
        await message.answer("❌ Файл з умовами не знайдено.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    uid = message.from_user.id
    active_chats[uid] = True
    timeouts[uid] = asyncio.create_task(auto_end(uid))
    await message.answer("📝 Напишіть ваше питання. Оператор відповість найближчим часом.", reply_markup=cancel_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"📞 Новий запит від {user_state[uid]['name']} ({user_state[uid]['phone']}), ID: {uid}")

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    active_chats.pop(uid, None)
    if timeouts.get(uid):
        timeouts[uid].cancel()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Розмову завершено.", reply_markup=keyboard)
    for op in OPERATORS:
        await bot.send_message(op, f"❌ Користувач {user_state[uid]['name']} завершив розмову.")

@dp.message_handler(lambda msg: msg.from_user.id in active_chats)
async def relay_message(message: types.Message):
    uid = message.from_user.id
    for op in OPERATORS:
        await bot.send_message(op, f"✉️ {user_state[uid]['name']} ({uid}): {message.text}")

@dp.message_handler(commands=['reply'])
async def operator_reply(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <повідомлення>")
    try:
        uid = int(args[1])
        await bot.send_message(uid, f"💬 Відповідь оператора: {args[2]}", reply_markup=cancel_keyboard())
        await message.reply("✅ Відповідь надіслано")
    except:
        await message.reply("❌ Не вдалося надіслати повідомлення.")

async def auto_end(uid):
    await asyncio.sleep(600)
    if uid in active_chats:
        active_chats.pop(uid)
        await bot.send_message(uid, "⌛ Час очікування завершився. Розмову завершено.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("💬 Зв’язатися з оператором"))
        for op in OPERATORS:
            await bot.send_message(op, f"⏱️ Розмова з {user_state[uid]['name']} завершена автоматично через неактивність.")

def cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔚 Завершити розмову")
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
