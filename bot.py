import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
OPERATORS = [5498505652]  # заміни на реальні ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
operator_reply_mode = {}
active_chats = {}

TERMS_FILE_PATH = "full_temp_terms.pdf"

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

# Контакт
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {
        'phone': message.contact.phone_number,
        'state': 'awaiting_name'
    }
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: user_state.get(msg.from_user.id, {}).get('state') == 'awaiting_name')
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    user_state[message.from_user.id]['state'] = 'ready'
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете зв’язатися з оператором.", reply_markup=keyboard)

# Умови
@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await message.answer_document(types.InputFile(TERMS_FILE_PATH))
    else:
        await message.answer("⚠️ Файл умов не знайдено.")

# Зв'язок
@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['dialog_active'] = True
    active_chats[uid] = {
        'operator': None,
        'last_activity': asyncio.get_event_loop().time()
    }
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔚 Завершити розмову"))
    await message.answer("📝 Опишіть свою проблему. Після відповіді оператора ви зможете вільно спілкуватися.", reply_markup=keyboard)
    asyncio.create_task(auto_timeout_check(uid))

# Обробка повідомлень від користувача
@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('dialog_active'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    active_chats[uid]['last_activity'] = asyncio.get_event_loop().time()
    for op in OPERATORS:
        try:
            operator_reply_mode[op] = uid
            await bot.send_message(op, f"📨 <b>{user_state[uid]['name']}</b>:
{message.text}", parse_mode='HTML')
        except BotBlocked:
            continue
    await message.answer("✅ Повідомлення надіслано оператору.")

# Відповідь оператора через reply
@dp.message_handler(lambda message: message.reply_to_message and message.from_user.id in OPERATORS)
async def handle_operator_reply(message: types.Message):
    original_text = message.reply_to_message.text or ""
    for uid, state in user_state.items():
        if state.get('dialog_active') and state.get('name') in original_text:
            try:
                await bot.send_message(uid, f"💬 Відповідь оператора: {message.text}")
                return
            except:
                await message.reply("⚠️ Не вдалося надіслати відповідь користувачу.")
                return
    await message.reply("⚠️ Користувача не знайдено або розмова завершена.")

# Завершення розмови
@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    uid = message.from_user.id
    user_state[uid]['dialog_active'] = False
    if uid in active_chats:
        del active_chats[uid]
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором", "📄 Умови використання Temp")
    await message.answer("🔚 Розмову завершено.", reply_markup=keyboard)
    for op in OPERATORS:
        await bot.send_message(op, f"❌ Користувач <b>{user_state[uid]['name']}</b> завершив розмову.", parse_mode='HTML')

# Таймер неактивності
async def auto_timeout_check(uid):
    await asyncio.sleep(600)  # 10 хвилин
    if user_state.get(uid, {}).get('dialog_active') and (asyncio.get_event_loop().time() - active_chats[uid]['last_activity'] > 590):
        user_state[uid]['dialog_active'] = False
        del active_chats[uid]
        await bot.send_message(uid, "⌛ Розмову завершено через неактивність. Спробуйте пізніше.")
        for op in OPERATORS:
            await bot.send_message(op, f"⌛ Користувач <b>{user_state[uid]['name']}</b> не відповідав 10 хвилин. Розмову завершено.", parse_mode='HTML')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
