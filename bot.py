import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
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
TERMS_FILE_PATH = "full_temp_terms.pdf"

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете натиснути, щоб зв’язатись з оператором.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['awaiting_response'] = True
    active_chats[uid] = True
    await message.answer("📝 Опишіть вашу проблему. Оператор отримає ваше повідомлення та відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await message.answer_document(InputFile(TERMS_FILE_PATH))
    else:
        await message.answer("❌ Файл умов використання не знайдено.")

@dp.message_handler(lambda message: message.from_user.id in user_state and user_state[message.from_user.id].get('awaiting_response'))
async def handle_user_message(message: types.Message):
    uid = message.from_user.id
    user = user_state[uid]
    user['awaiting_response'] = False
    active_chats[uid] = True

    text = f"📩 Запит від <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{message.text}\n\n👨‍💻 Для відповіді: /reply {uid} <текст>"
    for operator_id in OPERATORS:
        try:
            await bot.send_message(operator_id, text, parse_mode='HTML')
        except BotBlocked:
            continue

    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора. 🙌")

@dp.message_handler(commands=['reply'])
async def operator_reply(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <повідомлення>")

    user_id = int(args[1])
    text = args[2]
    try:
        await bot.send_message(user_id, f"💬 Відповідь оператора: {text}")
        await message.reply("✅ Відповідь надіслано")
    except:
        await message.reply("❌ Не вдалося надіслати повідомлення користувачу")

@dp.message_handler(lambda msg: msg.text == "🔙 Повернутись назад")
async def back_to_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("🔄 Ви повернулись у головне меню.", reply_markup=keyboard)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
