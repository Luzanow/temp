import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from collections import defaultdict

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_ID = 5498505652
TERMS_FILE = "full_temp_terms.pdf"  # Переконайся, що цей файл у тій же папці!

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
chat_links = {}
timeouts = {}

# Кнопки
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add("📄 Умови використання Temp")
    return kb

def chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Зв’язатися з оператором"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити розмову"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    await message.answer("👋 Вітаємо у TEMP! Поділіться номером або перегляньте умови використання.", reply_markup=start_keyboard())

# Контакт
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

# Ім’я
@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=chat_keyboard())

# Умови використання
@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def handle_terms(message: types.Message):
    try:
        await message.answer_document(InputFile(TERMS_FILE))
    except Exception as e:
        await message.answer("⚠️ Не вдалося надіслати PDF. Перевір правильність шляху до файлу.")
        logging.error(e)

# Зв’язок з оператором
@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def handle_contact_operator(message: types.Message):
    uid = message.from_user.id
    active_chats[uid] = True
    chat_links[ADMIN_ID] = uid
    await message.answer("✍️ Напишіть ваше запитання оператору. Ви можете надсилати кілька повідомлень.", reply_markup=back_keyboard())

    await bot.send_message(
        ADMIN_ID,
        f"📩 Запит від <b>{user_state[uid]['name']}</b> (<code>{user_state[uid]['phone']}</code>)",
        parse_mode="HTML"
    )

    if uid in timeouts:
        timeouts[uid].cancel()
    timeouts[uid] = asyncio.create_task(auto_timeout(uid))

# Повідомлення від користувача
@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id))
async def forward_user_message(message: types.Message):
    uid = message.from_user.id
    user = user_state[uid]
    forward_text = f"📩 <b>{user['name']}</b>: {message.text}"
    await bot.send_message(ADMIN_ID, forward_text, parse_mode="HTML", reply_to_message_id=None)

# Відповідь оператора
@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id == ADMIN_ID)
async def operator_reply(message: types.Message):
    uid = chat_links.get(ADMIN_ID)
    if not uid:
        return await message.reply("❌ Немає активного діалогу з користувачем.")
    try:
        await bot.send_message(uid, f"💬 Відповідь оператора: {message.text}", reply_markup=back_keyboard())
    except Exception as e:
        logging.error(e)
        await message.reply("❌ Не вдалося надіслати повідомлення користувачу.")

# Завершення розмови
@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def finish_chat(message: types.Message):
    uid = message.from_user.id
    active_chats.pop(uid, None)
    chat_links.pop(ADMIN_ID, None)
    if uid in timeouts:
        timeouts[uid].cancel()

    await message.answer("✅ Розмову завершено.", reply_markup=chat_keyboard())
    await bot.send_message(ADMIN_ID, f"❌ Користувач {user_state[uid]['name']} завершив розмову.")

# Автоматичне завершення
async def auto_timeout(user_id):
    await asyncio.sleep(600)
    if active_chats.get(user_id):
        active_chats.pop(user_id)
        chat_links.pop(ADMIN_ID, None)
        await bot.send_message(user_id, "⌛ Час очікування перевищено. Розмову завершено.", reply_markup=chat_keyboard())
        await bot.send_message(ADMIN_ID, f"❌ Розмова з {user_state[user_id]['name']} завершена через таймаут.")

# Запуск
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
