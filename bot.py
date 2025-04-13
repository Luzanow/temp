import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_CHAT_ID = 5498505652

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
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['active'] = True
    active_chats[message.from_user.id] = {'operator': ADMIN_CHAT_ID}
    text = (
        f"📩 Запит від {user_state[message.from_user.id]['name']} (user_id={message.from_user.id}):\n"
        f"Телефон: {user_state[message.from_user.id]['phone']}\n"
        f"🔁 Відповідайте на це повідомлення через Reply, щоб надіслати відповідь."
    )
    await bot.send_message(ADMIN_CHAT_ID, text)
    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову"))

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    try:
        with open(TERMS_FILE_PATH, "rb") as f:
            await message.answer_document(f)
    except:
        await message.answer("❌ Не вдалося відкрити файл умов користування.")

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_state[message.from_user.id]['active'] = False
    await message.answer("✅ Розмову завершено. Дякуємо!", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("💬 Зв’язатися з оператором"))
    await bot.send_message(ADMIN_CHAT_ID, f"🔔 Користувач {message.from_user.id} завершив розмову.")

@dp.message_handler(lambda msg: msg.reply_to_message and "user_id=" in msg.reply_to_message.text)
async def operator_reply(message: types.Message):
    try:
        lines = message.reply_to_message.text.split('\n')
        for line in lines:
            if "user_id=" in line:
                user_id = int(line.split("user_id=")[-1].split(")")[0])
                break
        else:
            return await message.reply("❗ Не вдалося визначити користувача для відповіді.")

        if user_state.get(user_id, {}).get('active'):
            await bot.send_message(user_id, f"💬 Відповідь оператора: {message.text}")
            await message.reply("✅ Відповідь надіслано.")
        else:
            await message.reply("⚠️ Користувач завершив розмову або недоступний.")

    except Exception as e:
        await message.reply(f"❌ Помилка: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
