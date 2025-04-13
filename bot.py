import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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

TERMS_PATH = "full_temp_terms.pdf"

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number, 'chatting': False}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]['chatting'] = True
    active_chats[user_id] = {'operator': OPERATORS[0], 'timeout': asyncio.create_task(chat_timeout(user_id))}
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔚 Завершити розмову")
    await message.answer("📝 Опишіть свою проблему. Ви можете спілкуватися з оператором у реальному часі.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        operator_id = active_chats[uid]['operator']
        del active_chats[uid]
        user_state[uid]['chatting'] = False
        await message.answer("❎ Розмову завершено.", reply_markup=start_keyboard())
        await bot.send_message(operator_id, f"🔕 Користувач {user_state[uid]['name']} завершив розмову.")

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_PATH):
        await message.answer_document(types.InputFile(TERMS_PATH))
    else:
        await message.answer("❌ Файл умов використання не знайдено.")

@dp.message_handler()
async def relay_messages(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats and user_state.get(uid, {}).get('chatting'):
        operator_id = active_chats[uid]['operator']
        await bot.send_message(operator_id, f"📩 <b>{user_state[uid]['name']}</b>: {message.text}", parse_mode="HTML")
    elif message.chat.id in OPERATORS:
        parts = message.text.split(" ", 1)
        if len(parts) > 1 and parts[0].isdigit():
            target_id = int(parts[0])
            text = parts[1]
            if target_id in user_state:
                await bot.send_message(target_id, f"💬 Оператор: {text}")
                await message.reply("✅ Повідомлення надіслано користувачу")
            else:
                await message.reply("❌ Користувача не знайдено")

async def chat_timeout(user_id):
    await asyncio.sleep(600)  # 10 хв
    if user_state.get(user_id, {}).get('chatting'):
        user_state[user_id]['chatting'] = False
        await bot.send_message(user_id, "⏰ Розмова завершена через відсутність активності.", reply_markup=start_keyboard())
        operator_id = active_chats[user_id]['operator']
        await bot.send_message(operator_id, f"🔕 Розмова з користувачем {user_state[user_id]['name']} завершена через неактивність.")
        del active_chats[user_id]

def start_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
