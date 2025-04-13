import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o")  # Встанови цей токен у .env файлі
OPERATORS = [5498505652]  # Замінити на реальні ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
operator_reply_mode = {}
user_operator_mapping = {}

TERMS_FILE_PATH = "terms.pdf"  # Переконайся, що файл знаходиться поруч

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {
        'phone': message.contact.phone_number,
        'chat_active': False
    }
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['chat_active'] = True
    user_operator_mapping[message.from_user.id] = OPERATORS[0]  # Просте призначення
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор побачить повідомлення та відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())
    await asyncio.sleep(600)
    if user_state.get(message.from_user.id, {}).get('chat_active'):
        await message.answer("⌛ Розмова завершена через неактивність. Щоб почати знову — натисніть старт.")
        operator_id = user_operator_mapping.get(message.from_user.id)
        if operator_id:
            await bot.send_message(operator_id, f"⚠️ Користувач {message.from_user.id} не відповідав 10 хв. Розмова завершена.")
        user_state[message.from_user.id]['chat_active'] = False

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('chat_active'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    user = user_state[uid]
    operator_reply_mode[uid] = True
    text = f"📩 <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{message.text}"
    operator_id = user_operator_mapping[uid]
    await bot.send_message(operator_id, text, parse_mode='HTML')
    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора.")

@dp.message_handler(commands=['reply'])
async def operator_reply(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <повідомлення>")
    user_id = int(parts[1])
    reply_text = parts[2]
    await bot.send_message(user_id, f"💬 Відповідь оператора: {reply_text}")
    await message.reply("✅ Надіслано.")

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    try:
        await message.answer_document(open(TERMS_FILE_PATH, "rb"))
    except:
        await message.answer("❌ Не вдалося знайти файл умов використання.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
