import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN") or "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # Telegram ID оператора

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
operator_sessions = {}

TERMS_FILE = "terms_temp.pdf"

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Вітаємо у Temp! Щоб почати, поділіться номером телефону або перегляньте умови використання.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_contact(message: types.Message):
    user_state[message.from_user.id] = {
        'phone': message.contact.phone_number,
        'name': None,
        'chatting': False
    }
    await message.answer("✏️ Введіть своє ім'я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and user_state[msg.from_user.id]['name'] is None)
async def set_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Ви зареєстровані. Щоб почати чат із оператором — натисніть кнопку нижче.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    if os.path.exists(TERMS_FILE):
        await message.answer_document(open(TERMS_FILE, 'rb'))
    else:
        await message.answer("❌ Файл умов не знайдено.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['chatting'] = True
    operator_sessions[message.from_user.id] = {'last_message_time': asyncio.get_event_loop().time()}
    await message.answer("📝 Напишіть повідомлення. Оператор відповість вам у цьому чаті. Щоб завершити розмову — натисніть кнопку нижче.", reply_markup=cancel_keyboard())

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_state[message.from_user.id]['chatting'] = False
    await message.answer("✅ Розмову завершено. Натисніть /start, щоб повернутись до меню.", reply_markup=types.ReplyKeyboardRemove())
    for op in OPERATORS:
        await bot.send_message(op, f"❗ Користувач {user_state[message.from_user.id]['name']} завершив розмову.")

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('chatting'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    operator_sessions[uid]['last_message_time'] = asyncio.get_event_loop().time()
    data = user_state[uid]
    text = f"📩 <b>{data['name']}</b> (<code>{data['phone']}</code>):\n{message.text}\n\nВідповісти: /reply {uid} <текст>"
    for op in OPERATORS:
        await bot.send_message(op, text, parse_mode="HTML")
    await message.answer("📨 Ваше повідомлення надіслано оператору.")

@dp.message_handler(commands=['reply'])
async def reply_to_user(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <текст>")
    uid = int(args[1])
    text = args[2]
    try:
        await bot.send_message(uid, f"💬 Відповідь оператора:\n{text}", reply_markup=cancel_keyboard())
        await message.reply("✅ Відповідь надіслана.")
    except BotBlocked:
        await message.reply("❌ Користувач заблокував бота або його недоступно.")

async def auto_end_chat():
    while True:
        now = asyncio.get_event_loop().time()
        for uid, session in list(operator_sessions.items()):
            if user_state.get(uid, {}).get('chatting') and now - session['last_message_time'] > 600:
                user_state[uid]['chatting'] = False
                await bot.send_message(uid, "⌛ Час очікування вичерпано. Розмова завершена.", reply_markup=types.ReplyKeyboardRemove())
                for op in OPERATORS:
                    await bot.send_message(op, f"⚠️ Розмова з користувачем {user_state[uid]['name']} завершилась через таймаут.")
                del operator_sessions[uid]
        await asyncio.sleep(30)

def cancel_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 Завершити розмову")
    return kb

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(auto_end_chat())
    executor.start_polling(dp, skip_updates=True)
