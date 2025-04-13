import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # оператори

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

TERMS_FILE_ID = "BQACAgIAAxkBAAIBQ2Yh7X9kS9Kov3DCeW8iSmo3AAH0TAACMwEAAmMRSEsRNUJ6iGkX7TQE"  # реальний File_ID

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
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    active_chats[user_id] = {'operator': None, 'last_activity': asyncio.get_event_loop().time()}
    user_state[user_id]['chatting'] = True
    await message.answer("📝 Опишіть вашу проблему. Оператор відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    await bot.send_document(message.chat.id, TERMS_FILE_ID)

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    if active_chats.get(user_id):
        op_id = active_chats[user_id]['operator']
        await message.answer("🔕 Розмову завершено.", reply_markup=start_keyboard())
        if op_id:
            await bot.send_message(op_id, f"❌ Користувач {user_id} завершив розмову")
        del active_chats[user_id]
        user_state[user_id]['chatting'] = False

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('chatting'))
async def forward_to_operator(message: types.Message):
    user_id = message.from_user.id
    for op_id in OPERATORS:
        await bot.forward_message(op_id, from_chat_id=user_id, message_id=message.message_id)
        await bot.send_message(op_id, f"👆 Повідомлення від користувача {user_id}. Щоб відповісти, напишіть команду /reply у відповідь на це повідомлення.")

@dp.message_handler(commands=['reply'])
async def operator_reply(message: types.Message):
    if not message.reply_to_message or not message.reply_to_message.forward_from:
        return await message.reply("❗ Скористайтесь командою /reply у відповідь на переслане повідомлення.")

    user_id = message.reply_to_message.forward_from.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("❗ Введіть текст повідомлення після команди /reply")
    reply_text = args[1]
    try:
        await bot.send_message(user_id, f"💬 Відповідь оператора:
{reply_text}", reply_markup=end_chat_keyboard())
        await message.reply("✅ Відповідь надіслано")
    except:
        await message.reply("❌ Не вдалося надіслати повідомлення користувачу")

def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💬 Зв’язатися з оператором")
    return kb

def end_chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 Завершити розмову")
    return kb

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
