import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # заміни на реальні ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
operator_reply_mode = {}

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
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['chat_active'] = True
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор побачить повідомлення та відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())
    await asyncio.sleep(600)
    if user_state.get(message.from_user.id, {}).get('chat_active'):
        await message.answer("⌛ Усі оператори зараз зайняті. Очікуйте, будь ласка. 🙏", reply_markup=end_chat_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms_file(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await message.answer_document(open(TERMS_FILE_PATH, "rb"))
    else:
        await message.answer("❌ Не вдалося знайти файл із умовами використання.")

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_state[message.from_user.id]['chat_active'] = False
    await message.answer("🔒 Розмову завершено. Дякуємо за звернення!", reply_markup=start_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"❌ Користувач @{message.from_user.username or 'анонім'} завершив розмову.")

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('chat_active'))
async def handle_user_message(message: types.Message):
    user = user_state[message.from_user.id]
    for op in OPERATORS:
        try:
            await bot.send_message(op, f"📨 Повідомлення від @{message.from_user.username or 'анонім'}:
{message.text}\n\nНатисніть Reply, щоб відповісти.", reply_to_message_id=message.message_id)
        except BotBlocked:
            logging.warning(f"Оператор {op} заблокував бота")
    await message.answer("✅ Повідомлення надіслано. Очікуйте відповідь.", reply_markup=end_chat_keyboard())

@dp.message_handler(lambda msg: msg.chat.id in OPERATORS and msg.reply_to_message)
async def handle_operator_reply(message: types.Message):
    try:
        reply_text = message.reply_to_message.text
        user_id = int(reply_text.split("@")[1].split()[0])
        await bot.send_message(user_id, f"💬 Відповідь оператора:
{message.text}")
    except Exception as e:
        logging.error(f"Не вдалося визначити користувача: {e}")
        await message.answer("❌ Не вдалося надіслати повідомлення користувачу")

def start_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    return keyboard

def end_chat_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔚 Завершити розмову")
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
