import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from collections import defaultdict
import os

API_TOKEN = "7import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from collections import defaultdict
import os

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_ID = 5498505652  # заміни на свій ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
timers = {}

# 📂 Файл умов
TERMS_PATH = "full_temp_terms.pdf"  # Повинен бути в цій же папці

def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add("📄 Умови використання Temp")
    return kb

def support_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💬 Зв’язатися з оператором")
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 Завершити розмову")
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привіт! Щоб почати, поділіться номером або перегляньте умови:", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=support_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_PATH):
        await bot.send_document(message.chat.id, InputFile(TERMS_PATH))
    else:
        await message.answer("❌ Файл умов не знайдено.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def contact_operator(message: types.Message):
    uid = message.from_user.id
    if uid not in active_chats:
        active_chats[uid] = True
        operator_text = f"📩 Нове повідомлення від {user_state[uid]['name']} ({user_state[uid]['phone']}): очікує запит."
        await bot.send_message(ADMIN_ID, operator_text)
        await message.answer("📝 Опишіть вашу проблему. Очікуйте відповіді оператора.", reply_markup=back_keyboard())
        start_inactivity_timer(uid)
    else:
        await message.answer("📨 Ви вже у діалозі. Очікуйте відповіді або завершіть розмову.", reply_markup=back_keyboard())

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        del active_chats[uid]
        stop_inactivity_timer(uid)
        await message.answer("✅ Розмову завершено.", reply_markup=support_keyboard())
        await bot.send_message(ADMIN_ID, f"🔕 Користувач {user_state[uid]['name']} завершив розмову.")
    else:
        await message.answer("❗ У вас немає активної розмови.")

@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    user = user_state.get(uid)
    if not user:
        return
    text = f"👤 <b>{user['name']}</b> (<code>{user['phone']}</code>):\n{message.text}"
    await bot.send_message(ADMIN_ID, text, parse_mode='HTML')
    start_inactivity_timer(uid)

@dp.message_handler(lambda msg: msg.reply_to_message and msg.chat.id == ADMIN_ID)
async def reply_from_operator(message: types.Message):
    text = message.text
    replied_text = message.reply_to_message.text
    # витягнути user_id з replied_text
    for uid, user in user_state.items():
        if user['name'] in replied_text or user['phone'] in replied_text:
            if uid in active_chats:
                await bot.send_message(uid, f"💬 Оператор: {text}", reply_markup=back_keyboard())
                return
    await message.reply("❌ Не вдалося визначити користувача.")

def start_inactivity_timer(user_id):
    if user_id in timers:
        timers[user_id].cancel()

    async def timeout():
        await asyncio.sleep(600)  # 10 хв
        if user_id in active_chats:
            del active_chats[user_id]
            await bot.send_message(user_id, "⌛ Розмову завершено через неактивність.")
            await bot.send_message(ADMIN_ID, f"⚠️ Розмова з {user_state[user_id]['name']} завершена через неактивність.")
    
    loop = asyncio.get_event_loop()
    timers[user_id] = loop.create_task(timeout())

def stop_inactivity_timer(user_id):
    if user_id in timers:
        timers[user_id].cancel()
        del timers[user_id]

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
"
ADMIN_ID = 5498505652  # заміни на свій ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
timers = {}

# 📂 Файл умов
TERMS_PATH = "full_temp_terms.pdf"  # Повинен бути в цій же папці

def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add("📄 Умови використання Temp")
    return kb

def support_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💬 Зв’язатися з оператором")
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 Завершити розмову")
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привіт! Щоб почати, поділіться номером або перегляньте умови:", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=support_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_PATH):
        await bot.send_document(message.chat.id, InputFile(TERMS_PATH))
    else:
        await message.answer("❌ Файл умов не знайдено.")

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def contact_operator(message: types.Message):
    uid = message.from_user.id
    if uid not in active_chats:
        active_chats[uid] = True
        operator_text = f"📩 Нове повідомлення від {user_state[uid]['name']} ({user_state[uid]['phone']}): очікує запит."
        await bot.send_message(ADMIN_ID, operator_text)
        await message.answer("📝 Опишіть вашу проблему. Очікуйте відповіді оператора.", reply_markup=back_keyboard())
        start_inactivity_timer(uid)
    else:
        await message.answer("📨 Ви вже у діалозі. Очікуйте відповіді або завершіть розмову.", reply_markup=back_keyboard())

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        del active_chats[uid]
        stop_inactivity_timer(uid)
        await message.answer("✅ Розмову завершено.", reply_markup=support_keyboard())
        await bot.send_message(ADMIN_ID, f"🔕 Користувач {user_state[uid]['name']} завершив розмову.")
    else:
        await message.answer("❗ У вас немає активної розмови.")

@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    user = user_state.get(uid)
    if not user:
        return
    text = f"👤 <b>{user['name']}</b> (<code>{user['phone']}</code>):\n{message.text}"
    await bot.send_message(ADMIN_ID, text, parse_mode='HTML')
    start_inactivity_timer(uid)

@dp.message_handler(lambda msg: msg.reply_to_message and msg.chat.id == ADMIN_ID)
async def reply_from_operator(message: types.Message):
    text = message.text
    replied_text = message.reply_to_message.text
    # витягнути user_id з replied_text
    for uid, user in user_state.items():
        if user['name'] in replied_text or user['phone'] in replied_text:
            if uid in active_chats:
                await bot.send_message(uid, f"💬 Оператор: {text}", reply_markup=back_keyboard())
                return
    await message.reply("❌ Не вдалося визначити користувача.")

def start_inactivity_timer(user_id):
    if user_id in timers:
        timers[user_id].cancel()

    async def timeout():
        await asyncio.sleep(600)  # 10 хв
        if user_id in active_chats:
            del active_chats[user_id]
            await bot.send_message(user_id, "⌛ Розмову завершено через неактивність.")
            await bot.send_message(ADMIN_ID, f"⚠️ Розмова з {user_state[user_id]['name']} завершена через неактивність.")
    
    loop = asyncio.get_event_loop()
    timers[user_id] = loop.create_task(timeout())

def stop_inactivity_timer(user_id):
    if user_id in timers:
        timers[user_id].cancel()
        del timers[user_id]

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
