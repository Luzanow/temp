import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_ID = 5498505652  # ID оператора

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_data = {}
active_chats = {}

TERMS_FILE_PATH = "full_temp_terms.pdf"

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add("📄 Умови використання Temp")
    await message.answer("👋 Вітаємо! Поділіться номером або перегляньте умови.", reply_markup=kb)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    user_data[message.from_user.id] = {"phone": message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_data and "name" not in user_data[msg.from_user.id])
async def name_handler(message: types.Message):
    user_data[message.from_user.id]["name"] = message.text
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Дякуємо! Тепер можете зв’язатися з оператором.", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_operator(message: types.Message):
    uid = message.from_user.id
    active_chats[uid] = {"operator": ADMIN_ID, "last_message": asyncio.get_event_loop().time()}
    await message.answer("✍️ Напишіть своє питання. Оператор відповість найближчим часом.", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await message.answer_document(types.InputFile(TERMS_FILE_PATH))
    else:
        await message.answer("❌ Не вдалося знайти файл з умовами використання.")

@dp.message_handler(lambda msg: msg.from_user.id in active_chats)
async def handle_user_message(message: types.Message):
    uid = message.from_user.id
    chat = active_chats.get(uid)
    if chat:
        text = f"📨 Повідомлення від {user_data[uid]['name']} ({user_data[uid]['phone']}):\n{message.text}"
        msg_sent = await bot.send_message(chat["operator"], text)
        # Save the original user's ID in reply_to_message_id
        active_chats["last_message_id"] = msg_sent.message_id
        active_chats["last_user"] = uid
        chat["last_message"] = asyncio.get_event_loop().time()
        await message.answer("✅ Повідомлення надіслано оператору.")

@dp.message_handler(lambda message: message.reply_to_message and message.chat.id == ADMIN_ID)
async def reply_by_operator(message: types.Message):
    uid = active_chats.get("last_user")
    if not uid:
        return await message.answer("❌ Не вдалося визначити користувача.")
    try:
        await bot.send_message(uid, f"💬 Відповідь оператора: {message.text}")
        await message.answer("✅ Відповідь надіслано.")
    except Exception as e:
        await message.answer(f"❌ Помилка надсилання: {e}")

@dp.message_handler(commands=['end'])
async def end_chat(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("⚠️ Формат: /end <user_id>")
    uid = int(parts[1])
    if uid in active_chats:
        del active_chats[uid]
        try:
            await bot.send_message(uid, "🔚 Розмову завершено. Якщо маєте ще питання — напишіть знову.")
        except:
            pass
        await message.answer("✅ Чат завершено.")

async def auto_end_chats():
    while True:
        now = asyncio.get_event_loop().time()
        expired = [uid for uid, data in active_chats.items() if isinstance(uid, int) and now - data["last_message"] > 600]
        for uid in expired:
            try:
                await bot.send_message(uid, "⌛ Розмову завершено через неактивність.")
                await bot.send_message(ADMIN_ID, f"⌛ Користувач {uid} завершив чат через неактивність.")
            except:
                pass
            del active_chats[uid]
        await asyncio.sleep(30)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(auto_end_chats())
    executor.start_polling(dp, skip_updates=True)
