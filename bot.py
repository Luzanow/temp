import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_CHAT_ID = 5498505652

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    user_state[message.from_user.id]['chatting'] = False
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def start_chat(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['chatting'] = True
    active_chats[uid] = ADMIN_CHAT_ID
    await message.answer("📝 Напишіть повідомлення для оператора:", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(600)
    if user_state[uid].get('chatting'):
        user_state[uid]['chatting'] = False
        await message.answer("⌛ Розмову завершено через неактивність. Натисніть /start щоб почати знову.")
        await bot.send_message(ADMIN_CHAT_ID, f"❗ Розмова з {uid} завершена через 10 хв неактивності.")

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    with open("full_temp_terms.pdf", "rb") as doc:
        await message.answer_document(doc)

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('chatting'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    user = user_state[uid]
    text = f"📩 Повідомлення від {user['name']} ({user['phone']}):\n{message.text}"
    await bot.send_message(ADMIN_CHAT_ID, text)

@dp.message_handler(commands=['reply'])
async def reply_command(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer("❗ Формат команди: /reply user_id текст")
    uid, text = int(parts[1]), parts[2]
    if user_state.get(uid, {}).get('chatting'):
        await bot.send_message(uid, f"💬 Відповідь оператора: {text}")
    else:
        await message.answer("❌ Користувач завершив розмову або не в чаті.")

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['chatting'] = False
    await message.answer("✅ Розмову завершено. Дякуємо за звернення!", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("/start"))
    await bot.send_message(ADMIN_CHAT_ID, f"❗ Користувач {uid} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
