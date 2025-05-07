import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS = [5498505652]  # список ID операторів  # Telegram ID оператора

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Стани діалогу
class Dialog(StatesGroup):
    chatting = State()

# Зберігає незавершені звернення
pending_requests = {}  # user_id: [messages]
active_chats = {}  # operator_id: user_id      # operator_id: user_id

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Вітаємо! Напишіть ваше запитання, оператор скоро відповість.")

@dp.message_handler(lambda message: message.chat.id != ADMIN_ID)
async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    if user_id not in pending_requests:
        pending_requests[user_id] = []
        text = f"🆕 Нове звернення від @{message.from_user.username or user_id} (ID: {user_id})"
        btn = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Прийняти", callback_data=f"accept_{user_id}"))
        await bot.send_message(ADMIN_ID, text, reply_markup=btn)

    pending_requests[user_id].append(message.text)

    # Якщо оператор уже веде чат із цим користувачем — надсилаємо повідомлення
    if any(op_id == user_id for op_id in active_chats.values()):
        await bot.send_message(ADMIN_ID, f"💬 {user_id}: {message.text}")

@dp.callback_query_handler(lambda c: c.data.startswith("accept_"))
async def accept_chat(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("accept_", ""))
    active_chats[callback.from_user.id] = user_id
    await bot.send_message(ADMIN_ID, f"🔓 Ви прийняли звернення від {user_id}. Тепер ви можете відповідати.")
    await Dialog.chatting.set()
    await state.update_data(user_id=user_id)
    # Показати історію повідомлень
    for msg in pending_requests.get(user_id, []):
        await bot.send_message(ADMIN_ID, f"📨 {msg}")
    await callback.answer()

@dp.message_handler(lambda message: message.chat.id in OPERATORS, state=Dialog.chatting)
async def handle_operator_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    if user_id:
        await bot.send_message(user_id, f"👨‍💼 Оператор: {message.text}")

@dp.message_handler(commands=['end'], state=Dialog.chatting)
async def end_chat(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    await bot.send_message(user_id, "✅ Дякуємо! Розмову завершено.")
    await bot.send_message(message.chat.id, "🔚 Ви завершили чат.")
    active_chats.pop(message.chat.id, None)
    pending_requests.pop(user_id, None)
    await state.finish()

    # Показати наступне звернення, якщо є
    for uid in pending_requests:
        if uid not in active_chats.values():
            text = f"🆕 Нове звернення від ID: {uid}"
            btn = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Прийняти", callback_data=f"accept_{uid}"))
            await bot.send_message(message.chat.id, text, reply_markup=btn)
            break

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
