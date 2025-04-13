import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # заміни на свій реальний Telegram ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}  # зберігає активні діалоги
operator_reply_mode = {}  # зв'язок оператор-користувач

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number, 'name': None, 'active': False}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda m: m.text and m.from_user.id in user_state and not user_state[m.from_user.id].get('name'))
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Дякуємо! Тепер ви можете натиснути, щоб зв’язатись із оператором.", reply_markup=keyboard)

@dp.message_handler(lambda m: m.text == "💬 Зв’язатися з оператором")
async def connect_operator(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['active'] = True
    user_state[uid]['timeout'] = asyncio.create_task(auto_end(uid))
    await message.answer("📝 Напишіть вашу проблему. Оператор відповість у цьому чаті.", reply_markup=end_keyboard())
    for op in OPERATORS:
        try:
            await bot.send_message(op, f"📥 Нове звернення від {user_state[uid]['name']} ({user_state[uid]['phone']}):\nОчікує повідомлення.")
        except BotBlocked:
            pass

@dp.message_handler(lambda m: m.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    if uid in user_state and user_state[uid]['active']:
        user_state[uid]['active'] = False
        if 'timeout' in user_state[uid]:
            user_state[uid]['timeout'].cancel()
        for op in OPERATORS:
            await bot.send_message(op, f"❌ Користувач {user_state[uid]['name']} завершив розмову.")
        await message.answer("✅ Розмову завершено.", reply_markup=start_keyboard())

@dp.message_handler(lambda m: user_state.get(m.from_user.id, {}).get('active'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    for op in OPERATORS:
        operator_reply_mode[op] = uid
        await bot.send_message(op, f"💬 {user_state[uid]['name']}: {message.text}")
    await message.answer("📨 Повідомлення надіслано. Очікуйте відповідь оператора.")

@dp.message_handler(commands=['reply'])
async def reply_operator(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <повідомлення>")
    uid = int(args[1])
    text = args[2]
    try:
        await bot.send_message(uid, f"👨‍💻 Оператор: {text}", reply_markup=end_keyboard())
        await message.reply("✅ Повідомлення користувачу надіслано")
    except:
        await message.reply("⚠️ Не вдалося доставити повідомлення")

@dp.message_handler(lambda m: m.from_user.id in OPERATORS and m.reply_to_message)
async def swipe_operator(message: types.Message):
    original_text = message.reply_to_message.text
    for uid, data in user_state.items():
        if data['name'] in original_text:
            await bot.send_message(uid, f"👨‍💻 Оператор: {message.text}", reply_markup=end_keyboard())
            return await message.reply("✅ Надіслано користувачу")
    await message.reply("❌ Не вдалося визначити користувача")

@dp.message_handler(lambda m: m.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    with open("full_temp_terms.pdf", "rb") as doc:
        await bot.send_document(message.chat.id, doc, caption="📄 Умови використання Temp")

async def auto_end(uid):
    await asyncio.sleep(600)
    if uid in user_state and user_state[uid].get('active'):
        user_state[uid]['active'] = False
        for op in OPERATORS:
            await bot.send_message(op, f"⏱️ Розмову з {user_state[uid]['name']} завершено через неактивність.")
        await bot.send_message(uid, "⌛ Розмову завершено через неактивність.", reply_markup=start_keyboard())

def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add("📄 Умови використання Temp")
    return kb

def end_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 Завершити розмову")
    return kb

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
