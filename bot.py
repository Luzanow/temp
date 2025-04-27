import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

# Завантаження API-ключа з .env файлу
API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    print("API Token not found. Please ensure the .env file is configured correctly.")
    exit()

# Налаштування логування
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером телефону", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання"))
    return kb

# Обробка команди /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state[message.from_user.id] = {}
    await message.answer(
        "👋 Вітаємо! Поділіться номером телефону або перегляньте умови.",
        reply_markup=start_keyboard()
    )

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id]['phone'] = message.contact.phone_number
    await message.answer("✏️ Введіть ваше ім’я:")

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Натисніть, щоб зв’язатися з оператором.")

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання")
async def send_terms(message: types.Message):
    try:
        with open('full_temp_terms.pdf', 'rb') as doc:
            await bot.send_document(message.chat.id, doc, caption="📎 Ознайомтесь з умовами використання")
    except FileNotFoundError:
        await message.answer("⚠️ Файл умов не знайдено.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
