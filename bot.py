import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("\ud83d\udcf1 \u041f\u043e\u0434\u0456\u043b\u0438\u0442\u0438\u0441\u044f \u043d\u043e\u043c\u0435\u0440\u043e\u043c", request_contact=True))
    kb.add(KeyboardButton("\ud83d\udcc4 \u0423\u043c\u043e\u0432\u0438 \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043d\u044f Temp"))
    return kb

def contact_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("\ud83d\udcac \u0417\u0432\u2019\u044f\u0437\u0430\u0442\u0438\u0441\u044f \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("\ud83d\udd19 \u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0438 \u0440\u043e\u0437\u043c\u043e\u0432\u0443"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    await message.answer("\ud83d\udc4b \u0412\u0456\u0442\u0430\u0454\u043c\u043e! \u041f\u043e\u0434\u0456\u043b\u0456\u0442\u044c\u0441\u044f \u043d\u043e\u043c\u0435\u0440\u043e\u043c \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0443 \u0430\u0431\u043e \u043f\u0435\u0440\u0435\u0433\u043b\u044f\u043d\u044c\u0442\u0435 \u0443\u043c\u043e\u0432\u0438.", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("\u270f\ufe0f \u0412\u0432\u0435\u0434\u0456\u0442\u044c \u0432\u0430\u0448\u0435 \u0456\u043c'\u044f:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("\u2705 \u0414\u044f\u043a\u0443\u0454\u043c\u043e! \u041d\u0430\u0442\u0438\u0441\u043d\u0456\u0442\u044c \u043d\u0438\u0436\u0447\u0435, \u0449\u043e\u0431 \u0437\u0432'\u044f\u0437\u0430\u0442\u0438\u0441\u044f \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c.", reply_markup=contact_keyboard())

@dp.message_handler(lambda msg: msg.text == "\ud83d\udcc4 \u0423\u043c\u043e\u0432\u0438 \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043d\u044f Temp")
async def send_terms(message: types.Message):
    try:
        doc = InputFile("full_temp_terms.pdf")
        await bot.send_document(message.chat.id, doc, caption="\ud83d\udccc \u041e\u0437\u043d\u0430\u0439\u043e\u043c\u0442\u0435\u0441\u044c \u0437 \u0443\u043c\u043e\u0432\u0430\u043c\u0438 \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043d\u044f")
    except Exception as e:
        await message.answer("\u26a0\ufe0f \u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f \u0437\u043d\u0430\u0439\u0442\u0438 \u0444\u0430\u0439\u043b \u0443\u043c\u043e\u0432.")

@dp.message_handler(lambda msg: msg.text == "\ud83d\udcac \u0417\u0432\u2019\u044f\u0437\u0430\u0442\u0438\u0441\u044f \u0437 \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u043e\u043c")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user = user_state.get(user_id)
    if not user:
        return await message.answer("\u26a0\ufe0f \u041f\u043e\u0447\u043d\u0456\u0442\u044c \u0437 /start \u0456 \u043f\u043e\u0434\u0456\u043b\u0456\u0442\u044c\u0441\u044f \u043d\u043e\u043c\u0435\u0440\u043e\u043c.")
    user_state[user_id]['chat_active'] = True
    active_chats[user_id] = True
    await message.answer("\ud83d\udcdd \u041e\u043f\u0438\u0448\u0456\u0442\u044c \u0432\u0430\u0448\u0443 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0443.", reply_markup=back_keyboard())
    for op in OPERATORS:
        await bot.send_message(op, f"\ud83d\udce8 \u041d\u043e\u0432\u0435 \u0437\u0432\u0435\u0440\u043d\u0435\u043d\u043d\u044f: {user['name']} {user['phone']}")

@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id))
async def relay_to_operator(message: types.Message):
    user = user_state.get(message.from_user.id)
    if not user:
        return
    for op in OPERATORS:
        await bot.send_message(op, f"\u2709\ufe0f {user['name']}: {message.text}")

@dp.message_handler(lambda msg: msg.text == "\ud83d\udd19 \u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0438 \u0440\u043e\u0437\u043c\u043e\u0432\u0443")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    user_state.get(user_id, {}).pop('chat_active', None)
    await message.answer("\ud83d\udd1a \u0420\u043e\u0437\u043c\u043e\u0432\u0443 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e. \u041d\u0430\u0442\u0438\u0441\u043d\u0456\u0442\u044c /start, \u0449\u043e\u0431 \u043f\u043e\u0447\u0430\u0442\u0438 \u0437\u043d\u043e\u0432\u0443.", reply_markup=types.ReplyKeyboardRemove())
    for op in OPERATORS:
        await bot.send_message(op, f"\ud83d\udd14 {user_state.get(user_id, {}).get('name', 'Користувач')} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
