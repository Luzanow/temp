import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
active_chats = {}
timeout_tasks = {}

TERMS_FILE = InputFile("full_temp_terms.pdf")

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {
        'phone': message.contact.phone_number,
        'step': 'awaiting_name'
    }
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda m: user_state.get(m.from_user.id, {}).get('step') == 'awaiting_name')
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    user_state[message.from_user.id]['step'] = 'menu'
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    keyboard.add("📄 Умови використання Temp")
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda m: m.text == "💬 Зв’язатися з оператором")
async def connect_operator(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]['chat_active'] = True
    active_chats[user_id] = None
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔚 Завершити розмову")
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор побачить повідомлення та відповість вам тут.", reply_markup=keyboard)

    # Автоматичне завершення через 10 хвилин
    if user_id in timeout_tasks:
        timeout_tasks[user_id].cancel()
    timeout_tasks[user_id] = asyncio.create_task(auto_end(user_id))

@dp.message_handler(lambda m: m.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]['chat_active'] = False
    if user_id in timeout_tasks:
        timeout_tasks[user_id].cancel()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    keyboard.add("📄 Умови використання Temp")
    await message.answer("🔕 Розмову завершено.", reply_markup=keyboard)
    if active_chats.get(user_id):
        await bot.send_message(active_chats[user_id], f"❌ Користувач {user_state[user_id]['name']} завершив розмову.")
    active_chats.pop(user_id, None)

@dp.message_handler(lambda m: m.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    await bot.send_document(chat_id=message.chat.id, document=TERMS_FILE)

@dp.message_handler()
async def relay_message(message: types.Message):
    user_id = message.from_user.id
    if not user_state.get(user_id, {}).get('chat_active'):
        return

    # Надсилаємо оператору тільки якщо це перше повідомлення в сесії
    if active_chats[user_id] is None:
        user_info = user_state[user_id]
        for operator_id in OPERATORS:
            sent = await bot.send_message(operator_id,
                f"📩 Запит від <b>{user_info['name']}</b> (<code>{user_info['phone']}</code>):\n{message.text}",
                parse_mode='HTML')
            active_chats[user_id] = operator_id
        await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора.")
    else:
        # Надсилаємо повідомлення оператору
        try:
            await bot.send_message(active_chats[user_id], f"💬 {user_state[user_id]['name']}: {message.text}")
        except:
            pass

@dp.message_handler(lambda msg: msg.reply_to_message)
async def operator_reply(message: types.Message):
    # Обробка відповіді на повідомлення користувача
    for user_id, operator_id in active_chats.items():
        if operator_id == message.from_user.id:
            try:
                await bot.send_message(user_id, f"💬 Відповідь оператора: {message.text}", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову"))
            except:
                await message.reply("❌ Не вдалося доставити повідомлення користувачу")
            break

def back_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("🔚 Завершити розмову")

async def auto_end(user_id):
    await asyncio.sleep(600)  # 10 хвилин
    if user_state.get(user_id, {}).get('chat_active'):
        user_state[user_id]['chat_active'] = False
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("💬 Зв’язатися з оператором")
        keyboard.add("📄 Умови використання Temp")
        await bot.send_message(user_id, "⌛ Час очікування вичерпано. Розмову завершено.", reply_markup=keyboard)
        if active_chats.get(user_id):
            await bot.send_message(active_chats[user_id], f"🔕 Користувач {user_state[user_id]['name']} не відповідав 10 хвилин. Чат завершено.")
        active_chats.pop(user_id, None)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
