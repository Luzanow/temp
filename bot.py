import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")  # В .env файлi: API_TOKEN=токен
ADMIN_CHAT_ID = 5498505652  # Твiй ID
OPERATOR_NAME = "Роман"  # Ім'я оператора

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

user_state = {}
forwarded_messages = {}
last_user_message_time = {}
waiting_tasks = {}

# Клавiатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання Temp"))
    return kb

def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_state.pop(message.from_user.id, None)
    forwarded_messages.clear()
    last_user_message_time.pop(message.from_user.id, None)
    waiting_tasks.pop(message.from_user.id, None)
    await message.answer("👋 Вітаємо! Поділіться номером телефону або перегляньте умови.", reply_markup=start_keyboard())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Щоб почати спілкування, просто напишіть повідомлення.", reply_markup=back_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def send_terms(message: types.Message):
    try:
        doc = InputFile("full_temp_terms.pdf")
        await bot.send_document(message.chat.id, doc, caption="📎 Ознайомтесь з умовами використання")
    except:
        await message.answer("⚠️ Не вдалося знайти файл умов.")

async def wait_for_reply(user_id):
    await asyncio.sleep(300)  # 5 хвилин
    if user_id in last_user_message_time:
        await bot.send_message(user_id, "⚠️ Вибачте, всі оператори зараз зайняті. Ми швидко знайдемо для вас спеціаліста. Будь ласка, очікуйте.")
        waiting_tasks.pop(user_id, None)

@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    user_state.pop(user_id, None)
    last_user_message_time.pop(user_id, None)
    waiting_tasks.pop(user_id, None)
    forwarded_messages_to_delete = [fid for fid, uid in forwarded_messages.items() if uid == user_id]
    for fid in forwarded_messages_to_delete:
        forwarded_messages.pop(fid, None)
    await message.answer("🔚 Розмову завершено. Натисніть /start, щоб почати знову.", reply_markup=start_keyboard())
    await bot.send_message(ADMIN_CHAT_ID, f"🔔 Користувач завершив розмову.")

@dp.message_handler()
async def forward_to_operator(message: types.Message):
    if message.text == "🔙 Завершити розмову":
        return
    if message.from_user.id in user_state:
        user = user_state.get(message.from_user.id)
        if user:
            header = f"👤 {user['name']} ({user['phone']})"
            await bot.send_message(ADMIN_CHAT_ID, f"👋 Вас вітає служба підтримки TEMP! Очікуйте відповідь оператора.\n\n{header}")
            forwarded = await bot.send_message(ADMIN_CHAT_ID, f"✉️ {message.text}")
            forwarded_messages[forwarded.message_id] = message.from_user.id
            last_user_message_time[message.from_user.id] = message.date
            if message.from_user.id not in waiting_tasks:
                task = asyncio.create_task(wait_for_reply(message.from_user.id))
                waiting_tasks[message.from_user.id] = task

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
        await bot.send_message(
            user_id,
            f"""💬 Повідомлення від служби підтримки TEMP:\n👨‍💼 Оператор: {OPERATOR_NAME}\n\n{message.text}"""
        )
        # Якщо оператор відповів — скасовуємо таймер очікування
        if user_id in waiting_tasks:
            waiting_tasks[user_id].cancel()
            waiting_tasks.pop(user_id, None)
    except:
        await message.answer("⚠️ Не вдалося доставити повідомлення користувачу.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
