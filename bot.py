import os
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS = [5498505652]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

class ChatState(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    active_chat = State()

user_sessions = {}  # user_id: {"accepted": False, "operator_id": None, "last_active": datetime}

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_keyboard.add(KeyboardButton("📞 Поділитись номером", request_contact=True))

end_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
end_keyboard.add(KeyboardButton("❌ Завершити розмову"))

def start_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💬 Зв’язатись з оператором", callback_data="contact_operator"))
    return kb

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_sessions.pop(message.from_user.id, None)
    await message.answer("👋 Привіт! Це служба підтримки TEMP 💬\n\nМи тут, щоб допомогти вам якнайшвидше 🙌", reply_markup=start_keyboard())

@dp.callback_query_handler(lambda c: c.data == "contact_operator")
async def contact_operator(callback_query: types.CallbackQuery, state: FSMContext):
    await ChatState.waiting_name.set()
    await callback_query.message.answer("😎 Як можу до вас звертатись?", reply_markup=ReplyKeyboardRemove())
    await callback_query.answer()

@dp.message_handler(state=ChatState.waiting_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await ChatState.waiting_phone.set()
    await message.answer("📱 Поділіться номером або просто введіть його вручну, ми не передамо його інопланетянам 👽", reply_markup=phone_keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT, state=ChatState.waiting_phone)
@dp.message_handler(lambda m: True, state=ChatState.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    data = await state.get_data()
    name = data['name']
    user_id = message.from_user.id

    user_sessions[user_id] = {"accepted": False, "operator_id": None, "last_active": datetime.now()}

    for op_id in OPERATORS:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Прийняти", callback_data=f"accept_{user_id}")
        )
        await bot.send_message(op_id, f"🔔 Нове звернення:\n\n• Ім’я: {name}\n• Телефон: {phone}", reply_markup=kb)

    await state.finish()
    await message.answer("⏳ Дякуємо! Ваше звернення зареєстровано.\nОчікуйте на відповідь від нашого 🧑‍💼 оператора...", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda m: m.text == "❌ Завершити розмову")
async def user_end_chat_button(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        op_id = user_sessions[user_id].get("operator_id")
        if op_id:
            await bot.send_message(op_id, f"❌ Користувач завершив чат.")
        await message.answer("✅ Ви завершили розмову. Якщо ще буде питання — ми тут як тут 🤝", reply_markup=ReplyKeyboardRemove())
        await cmd_start(message)
        user_sessions.pop(user_id)

@dp.callback_query_handler(lambda c: c.data.startswith("accept_"))
async def accept_chat(callback_query: types.CallbackQuery):
    await callback_query.answer(cache_time=0)
    user_id = int(callback_query.data.split("_")[1])
    if user_id in user_sessions:
        user_sessions[user_id]["accepted"] = True
        user_sessions[user_id]["operator_id"] = callback_query.from_user.id
        user_sessions[user_id]["last_active"] = datetime.now()

        await bot.send_message(user_id, "👨‍💻 Хоп! Ми на зв'язку 🙌\nПишіть ваше питання прямо сюди ⌨️", reply_markup=end_keyboard)

        await bot.send_message(callback_query.from_user.id,
                               f"✅ Ви прийняли звернення користувача {user_id}.", 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("❌ Завершити", callback_data=f"end_{user_id}")
                               ))

@dp.message_handler(lambda m: m.from_user.id in user_sessions)
async def handle_user_message(message: types.Message):
    session = user_sessions.get(message.from_user.id)
    if not session or not session.get("accepted"):
        return
    operator_id = session["operator_id"]
    session["last_active"] = datetime.now()
    await bot.send_message(operator_id, f"👤 Користувач:\n{message.text}")

@dp.message_handler(lambda m: m.from_user.id in OPERATORS)
async def handle_operator_message(message: types.Message):
    for user_id, session in user_sessions.items():
        if session.get("operator_id") == message.from_user.id and session.get("accepted"):
            session["last_active"] = datetime.now()
            await bot.send_message(user_id, f"👨‍💻 Оператор:\n{message.text}")
            break

@dp.callback_query_handler(lambda c: c.data.startswith("end_"))
async def end_chat(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    if user_id in user_sessions:
        await bot.send_message(user_id, "❌ Чат завершено. Дякуємо!")
        await bot.send_message(user_id, "🔁 Щоб розпочати новий чат, натисніть /start")
        await bot.send_message(callback_query.from_user.id, "✅ Ви завершили чат.")
        user_sessions.pop(user_id)
    await callback_query.answer()

async def monitor_timeouts():
    while True:
        now = datetime.now()
        to_remove = []
        for user_id, session in user_sessions.items():
            if session.get("accepted") and now - session["last_active"] > timedelta(minutes=10):
                await bot.send_message(user_id, "❌ Чат завершено через неактивність.")
                await bot.send_message(session["operator_id"], f"⚠️ Чат з користувачем {user_id} завершено через неактивність.")
                to_remove.append(user_id)
        for uid in to_remove:
            user_sessions.pop(uid)
        await asyncio.sleep(60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_timeouts())
    executor.start_polling(dp, skip_updates=True)
