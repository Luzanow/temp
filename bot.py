import logging
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
OPERATORS = [5498505652]  # заміни на актуальні ID операторів

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
chat_timers = {}

TERMS_FILE = "full_temp_terms.pdf"
WELCOME_IMAGE = "welcome.jpg"

# Кнопки
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.add(KeyboardButton("\ud83d\udcf1 \u041f\u043e\u0434\u0456\u043b\u0438\u0442\u0438\u0441\u044f \u043d\u043e\u043c\u0435\u0440\u043e\u043c", request_contact=True))
start_keyboard.add(KeyboardButton("\ud83d\udcc4 \u0423\u043c\u043e\u0432\u0438 \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043d\u044f TEMP"))

def back_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("\ud83d\udd19 \u041f\u043e\u0432\u0435\u0440\u043d\u0443\u0442\u0438\u0441\u044c \u043d\u0430\u0437\u0430\u0434"))

def operator_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("\ud83d\udcac \u0417\u0432'\u044f\u0437\u0430\u0442\u0438\u0441\u044f \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c"))

def end_chat_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("\u274c \u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0438 \u0440\u043e\u0437\u043c\u043e\u0432\u0443 \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c"))

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    photo = InputFile(WELCOME_IMAGE)
    await message.answer_photo(photo=photo, caption="\ud83d\udc4b \u0412\u0456\u0442\u0430\u0454\u043c\u043e \u0443 TEMP!", reply_markup=start_keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {
        'phone': message.contact.phone_number
    }
    await message.answer("\u270f\ufe0f \u0412\u0432\u0435\u0434\u0456\u0442\u044c \u0441\u0432\u043e\u0454 \u0456\u043c'\u044f:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("\u2705 \u0414\u044f\u043a\u0443\u0454\u043c\u043e! \u0422\u0435\u043f\u0435\u0440 \u0432\u0438 \u043c\u043e\u0436\u0435\u0442\u0435 \u0437\u0432'\u044f\u0437\u0430\u0442\u0438\u0441\u044f \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c.", reply_markup=operator_keyboard())

@dp.message_handler(lambda msg: msg.text == "\ud83d\udcac \u0417\u0432'\u044f\u0437\u0430\u0442\u0438\u0441\u044f \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]['chatting'] = True
    user_state[user_id]['last_message'] = datetime.now()
    active_chats[user_id] = None
    await message.answer("\ud83d\udcdd \u041d\u0430\u043f\u0438\u0448\u0456\u0442\u044c \u0441\u0432\u043e\u0454 \u043f\u0438\u0442\u0430\u043d\u043d\u044f \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u0443.", reply_markup=end_chat_keyboard())
    asyncio.create_task(chat_timeout_checker(user_id))

async def chat_timeout_checker(user_id):
    await asyncio.sleep(600)
    if user_state.get(user_id, {}).get('chatting'):
        await end_chat(user_id, timeout=True)

@dp.message_handler(lambda msg: msg.text == "\u274c \u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0438 \u0440\u043e\u0437\u043c\u043e\u0432\u0443 \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c")
async def manual_end_chat(message: types.Message):
    await end_chat(message.from_user.id)

async def end_chat(user_id, timeout=False):
    user = user_state.get(user_id, {})
    if not user.get('chatting'):
        return
    user['chatting'] = False
    text = "\ud83d\udd19 \u0420\u043e\u0437\u043c\u043e\u0432\u0443 \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e."
    await bot.send_message(user_id, text, reply_markup=operator_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"\u274c \u041a\u043e\u0440\u0438\u0441\u0442\u0443\u0432\u0430\u0447 <b>{user.get('name')}</b> \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u0432 \u0440\u043e\u0437\u043c\u043e\u0432\u0443." + (" (\u0430\u0432\u0442\u043e\u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043d\u044f)" if timeout else ""), parse_mode='HTML')

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('chatting'))
async def forward_message(msg: types.Message):
    user = user_state[msg.from_user.id]
    user['last_message'] = datetime.now()
    for op in OPERATORS:
        await bot.send_message(op, f"\ud83d\udce2 <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{msg.text}", parse_mode='HTML')

@dp.message_handler(lambda msg: msg.from_user.id in OPERATORS and msg.reply_to_message)
async def operator_reply(msg: types.Message):
    text = msg.text
    if not text:
        return
    if "<code>" in msg.reply_to_message.html_text:
        user_id = int(msg.reply_to_message.html_text.split("<code>")[1].split("</code>")[0])
        await bot.send_message(user_id, f"\ud83d\udca1 \u0412\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u044c \u0432\u0456\u0434 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u0430:\n{text}")

@dp.message_handler(lambda msg: msg.text == "\ud83d\udcc4 \u0423\u043c\u043e\u0432\u0438 \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043d\u044f TEMP")
async def send_terms(msg: types.Message):
    try:
        doc = InputFile(TERMS_FILE)
        await msg.answer_document(doc, caption="\ud83d\udcc4 \u0423\u043c\u043e\u0432\u0438 \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043d\u044f \u0434\u043e\u0434\u0430\u0442\u043a\u0430 TEMP")
    except:
        await msg.answer("\u26a0\ufe0f \u0424\u0430\u0439\u043b \u0443\u043c\u043e\u0432 \u043d\u0435 \u0437\u043d\u0430\u0439\u0434\u0435\u043d.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
