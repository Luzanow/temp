import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
TERMS_FILE_PATH = "full_temp_terms.pdf"

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    user_state[message.from_user.id]['active'] = False
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await message.answer_document(types.InputFile(TERMS_FILE_PATH))
    else:
        await message.answer("❌ Умови використання наразі недоступні.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_operator(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['active'] = True
    active_chats[uid] = {'operator': None, 'last_msg': None}
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔚 Завершити розмову"))
    await message.answer("📝 Напишіть ваше запитання. Оператор відповість найближчим часом.", reply_markup=keyboard)
    asyncio.create_task(timeout_check(uid))

async def timeout_check(uid):
    await asyncio.sleep(600)
    if uid in active_chats:
        await bot.send_message(uid, "⏳ Розмова завершена через неактивність.", reply_markup=start_keyboard())
        for op in OPERATORS:
            await bot.send_message(op, f"⚠️ Користувач {uid} не відповів 10 хв. Розмову завершено.")
        active_chats.pop(uid, None)
        user_state[uid]['active'] = False

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['active'] = False
    active_chats.pop(uid, None)
    await message.answer("✅ Розмову завершено. Ви можете звернутися ще раз у будь-який час.", reply_markup=start_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"❌ Користувач {uid} завершив розмову.")

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('active'))
async def user_message(message: types.Message):
    uid = message.from_user.id
    user = user_state[uid]
    text = f"📩 Від <b>{user['name']}</b> (<code>{user['phone']}</code>):\n{message.text}"
    active_chats[uid]['last_msg'] = message.text
    for op in OPERATORS:
        sent = await bot.send_message(op, text)
        await sent.reply("✉️ Для відповіді просто відповідайте на це повідомлення.")

@dp.message_handler(content_types=types.ContentType.TEXT)
async def operator_reply(message: types.Message):
    if message.reply_to_message:
        for uid, data in active_chats.items():
            if data['last_msg'] and data['last_msg'] in message.reply_to_message.text:
                try:
                    await bot.send_message(uid, f"💬 Відповідь оператора: {message.text}", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову"))
                    break
                except:
                    await message.answer("❌ Не вдалося надіслати користувачу.")


def start_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
