import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import os
import re

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # Заміни на свій ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}  # user_id: {name, phone, awaiting}
active_chats = {}  # operator_reply_mode: user_id

# Старт
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати — поділіться номером або перегляньте умови:", reply_markup=keyboard)

# Номер телефону
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✍️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

# Ім’я
@dp.message_handler(lambda m: m.text and m.from_user.id in user_state and 'name' not in user_state[m.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    user_state[message.from_user.id]['awaiting'] = False
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Дякуємо! Тепер можете зв’язатися з оператором.", reply_markup=keyboard)

# Показати умови
@dp.message_handler(lambda m: m.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    with open("full_temp_terms.pdf", "rb") as doc:
        await bot.send_document(message.chat.id, doc)

# Зв’язок із оператором
@dp.message_handler(lambda m: m.text == "💬 Зв’язатися з оператором")
async def connect_operator(message: types.Message):
    user_state[message.from_user.id]['awaiting'] = True
    user_state[message.from_user.id]['active'] = True
    await message.answer("📝 Напишіть повідомлення. Оператор побачить його та відповість.", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову"))

    # Автозавершення через 10 хв
    async def auto_close():
        await asyncio.sleep(600)
        if user_state.get(message.from_user.id, {}).get('active'):
            user_state[message.from_user.id]['active'] = False
            await bot.send_message(message.chat.id, "⌛ Розмову завершено через неактивність.")
            for op in OPERATORS:
                await bot.send_message(op, f"⚠️ Розмова з <b>{user_state[message.from_user.id]['name']}</b> завершена (не було відповіді 10 хв).", parse_mode='HTML')
    asyncio.create_task(auto_close())

# Вихід із чату
@dp.message_handler(lambda m: m.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]['active'] = False
    await message.answer("✅ Ви завершили розмову.", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("💬 Зв’язатися з оператором"))
    for op in OPERATORS:
        await bot.send_message(op, f"❌ Користувач <b>{user_state[user_id]['name']}</b> завершив розмову.", parse_mode='HTML')

# Повідомлення від користувача
@dp.message_handler(lambda m: user_state.get(m.from_user.id, {}).get("active"))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    user = user_state[uid]
    text = f"📩 Запит від <b>{user['name']}</b> (<code>{user['phone']}</code>):\n{message.text}\n\n<user_id:{uid}>"
    for op in OPERATORS:
        await bot.send_message(op, text, parse_mode='HTML')

    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора.")

# Відповідь оператора (по reply)
@dp.message_handler(lambda m: m.from_user.id in OPERATORS and m.reply_to_message)
async def handle_operator_reply(message: types.Message):
    match = re.search(r"<user_id:(\d+)>", message.reply_to_message.text or "")
    if not match:
        return await message.reply("❗ Неможливо визначити користувача. Відповідайте через reply на повідомлення.")
    user_id = int(match.group(1))
    try:
        await bot.send_message(user_id, f"👨‍💼 Відповідь оператора:\n{message.text}")
    except:
        await message.reply("❌ Не вдалося доставити повідомлення користувачу.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
