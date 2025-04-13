import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # ID оператора

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}  # для зберігання стану користувача
active_chats = {}  # для активного чату між користувачем і оператором

TERMS_PATH = "full_temp_terms.pdf"

# Кнопка назад

def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Повернутись назад"))
    return keyboard

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

# Отримання контакту
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

# Збереження імені
@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

# Умови використання
@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    try:
        await bot.send_document(message.chat.id, InputFile(TERMS_PATH))
    except Exception as e:
        await message.answer("❌ Не вдалося надіслати файл. Перевірте його наявність.")

# Почати розмову з оператором
@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['active'] = True
    active_chats[message.from_user.id] = None
    await message.answer("📝 Опишіть вашу проблему. Оператор побачить повідомлення та відповість.", reply_markup=types.ReplyKeyboardRemove())

    await asyncio.sleep(600)
    if user_state.get(message.from_user.id, {}).get('active'):
        await message.answer("⌛ Оператор наразі не відповів. Розмову завершено.", reply_markup=main_menu_keyboard())
        user_state[message.from_user.id]['active'] = False
        for op in OPERATORS:
            await bot.send_message(op, f"❗ Розмова з користувачем {message.from_user.id} завершена через неактивність")

# Основне меню

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    return keyboard

# Отримання повідомлення користувача
@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('active'))
async def forward_to_operator(message: types.Message):
    user = user_state[message.from_user.id]
    for op in OPERATORS:
        sent = await bot.send_message(op, f"📩 Від: {user['name']} ({user['phone']}):\n{message.text}")
        active_chats[msg.from_user.id] = op
        active_chats[op] = msg.from_user.id

# Відповідь оператора свайпом
@dp.message_handler()
async def operator_reply(message: types.Message):
    if message.reply_to_message:
        for uid, opid in active_chats.items():
            if opid == message.from_user.id:
                try:
                    await bot.send_message(uid, f"💡 Відповідь оператора: {message.text}", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову"))
                except:
                    await message.answer("❌ Не вдалося надіслати повідомлення користувачу")

# Завершити розмову
@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        op = active_chats[uid]
        del active_chats[uid]
        if op:
            del active_chats[op]
            await bot.send_message(op, f"🔕 Користувач {uid} завершив розмову")
    await message.answer("🔚 Розмову завершено. Ви можете знову звернутись за потреби.", reply_markup=main_menu_keyboard())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
