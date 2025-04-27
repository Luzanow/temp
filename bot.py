import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")  # У .env файлi: API_TOKEN=токен твого бота
ADMIN_CHAT_ID = 5498505652  # ID оператора

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}
forwarded_messages = {}  # Зберiгаємо який forward_message_id належить якому user_id

# Клавiатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання Temp"))
    return kb

def contact_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Зв'язатися з оператором"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Старт бота
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    forwarded_messages.clear()
    await message.answer("👋 Вітаємо! Поділіться номером телефону або перегляньте умови.", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Натисніть кнопку нижче, щоб зв'язатися з оператором.", reply_markup=contact_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    try:
        doc = InputFile("full_temp_terms.pdf")
        await bot.send_document(message.chat.id, doc, caption="📎 Ознайомтесь з умовами використання")
    except:
        await message.answer("⚠️ Не вдалося знайти файл умов.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв'язатися з оператором")
async def connect_to_operator(message: types.Message):
    if message.from_user.id not in user_state:
        return await message.answer("⚠️ Спочатку натисніть /start та поділіться номером.")
    user_state[message.from_user.id]['chat_active'] = True
    await message.answer("📝 Опишіть вашу проблему нижче.", reply_markup=back_keyboard())

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('chat_active'))
async def forward_to_operator(message: types.Message):
    user = user_state.get(message.from_user.id)
    if user:
        header = f"👤 {user['name']} ({user['phone']})"
        header_msg = await bot.send_message(ADMIN_CHAT_ID, header)
        forwarded = await bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.message_id)
        # Зберiгаємо в словнику прив'язку forward_id -> user_id
        forwarded_messages[forwarded.message_id] = message.from_user.id

@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id == ADMIN_CHAT_ID)
async def admin_reply(message: types.Message):
    reply = message.reply_to_message
    if not reply:
        return
    user_id = forwarded_messages.get(reply.message_id)
    if not user_id:
        await message.answer("⚠️ Неможливо знайти користувача для відповіді.")
        return
    try:
        await bot.send_message(user_id, f"💬 Відповідь оператора: {message.text}")
    except:
        await message.answer("⚠️ Не вдалося доставити повідомлення користувачу.")

@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    user_state.pop(user_id, None)
    # Видалити всі forwarded повідомлення, що були від користувача
    forwarded_messages_to_delete = [fid for fid, uid in forwarded_messages.items() if uid == user_id]
    for fid in forwarded_messages_to_delete:
        forwarded_messages.pop(fid, None)
    await message.answer("🔚 Розмову завершено. Натисніть /start, щоб почати знову.", reply_markup=start_keyboard())
    await bot.send_message(ADMIN_CHAT_ID, f"🔔 Користувач завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
