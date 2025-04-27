import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_CHAT_ID = 5498505652
OPERATOR_NAME = "Тарас"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

active_chats = {}  # user_id -> operator_id
waiting_users = {}

# Клавiатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    return kb

def end_chat_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити розмову"))
    return kb

def operator_accept_keyboard(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Взяти в роботу", callback_data=f"accept_{user_id}"))
    return kb

def operator_end_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔚 Завершити розмову", callback_data="end_chat"))
    return kb

# /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("🚀 Почнемо нашу розмову! Надішліть свій номер телефону — і ми миттєво з вами на зв'язку. ❤️", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    await message.answer("✏️ Напишіть своє ім'я:", reply_markup=ReplyKeyboardRemove())
    active_chats[message.from_user.id] = {'phone': message.contact.phone_number, 'name': None, 'operator': None}

@dp.message_handler(lambda msg: msg.from_user.id in active_chats and active_chats[msg.from_user.id]['name'] is None)
async def handle_name(message: types.Message):
    active_chats[message.from_user.id]['name'] = message.text
    await message.answer("👋 Дякуємо! Очікуйте відповідь оператора. 🚀", reply_markup=end_chat_keyboard())

    user = active_chats[message.from_user.id]
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"🆕 Нове звернення!\nІм'я: {user['name']}\nТелефон: {user['phone']}",
        reply_markup=operator_accept_keyboard(message.from_user.id)
    )

    task = asyncio.create_task(wait_operator_response(message.from_user.id))
    waiting_users[message.from_user.id] = task

async def wait_operator_response(user_id):
    await asyncio.sleep(300)
    if user_id in active_chats and active_chats[user_id]['operator'] is None:
        await bot.send_message(user_id, "😔 Вибачте, всі оператори зайняті. Ми обов'язково скоро з вами зв'яжемось! ❤️")
        waiting_users.pop(user_id, None)

@dp.callback_query_handler(lambda c: c.data.startswith('accept_'))
async def accept_chat(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    active_chats[user_id]['operator'] = ADMIN_CHAT_ID

    await bot.send_message(user_id, f"🎉 Оператор {OPERATOR_NAME} приєднався до чату! Можете ставити питання.")
    await callback_query.message.edit_text(f"✅ Ви прийняли звернення від {active_chats[user_id]['name']}", reply_markup=operator_end_keyboard())

    if user_id in waiting_users:
        waiting_users[user_id].cancel()
        waiting_users.pop(user_id, None)

@dp.callback_query_handler(lambda c: c.data == 'end_chat')
async def operator_end_chat(callback_query: types.CallbackQuery):
    user_id = None
    for uid, chat in active_chats.items():
        if chat.get('operator') == ADMIN_CHAT_ID:
            user_id = uid
            break
    if user_id:
        await bot.send_message(user_id, "🔚 Дякуємо за звернення! Гарного дня! 🌟", reply_markup=ReplyKeyboardRemove())
        await callback_query.message.edit_text("✅ Ви завершили розмову. Можете прийняти новий чат.")
        active_chats.pop(user_id, None)

@dp.message_handler(lambda msg: msg.from_user.id == ADMIN_CHAT_ID)
async def operator_messages(message: types.Message):
    for user_id, info in active_chats.items():
        if info.get('operator') == ADMIN_CHAT_ID:
            await bot.send_message(user_id, f"💬 {OPERATOR_NAME}:\n\n{message.text}")
            break

@dp.message_handler()
async def user_messages(message: types.Message):
    if message.text == "🔚 Завершити розмову":
        if message.from_user.id in active_chats:
            await bot.send_message(message.from_user.id, "🔚 Дякуємо за звернення! Гарного дня! 🌟", reply_markup=ReplyKeyboardRemove())
            if active_chats[message.from_user.id]['operator']:
                await bot.send_message(ADMIN_CHAT_ID, f"🔔 Користувач {active_chats[message.from_user.id]['name']} завершив розмову.")
            active_chats.pop(message.from_user.id, None)
        return
    if message.from_user.id in active_chats and active_chats[message.from_user.id]['operator']:
        await bot.send_message(ADMIN_CHAT_ID, f"💬 {active_chats[message.from_user.id]['name']}:\n\n{message.text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
