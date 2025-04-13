import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
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

TERMS_FILE = "terms.pdf"  # Файл повинен бути у тій же директорії

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться своїм номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['awaiting_response'] = True
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор побачить повідомлення та відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())
    await asyncio.sleep(180)
    if user_state[message.from_user.id].get('awaiting_response'):
        await message.answer("⌛ Усі оператори зараз зайняті. Очікуйте, будь ласка. 🙏", reply_markup=back_keyboard())

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('awaiting_response'))
async def forward_to_operator(message: types.Message):
    user = user_state[message.from_user.id]
    user['awaiting_response'] = False
    operator_reply_mode[message.from_user.id] = message.chat.id
    text = f"📩 Запит від <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{message.text}\n\n👨‍💻 Для відповіді: /reply {message.from_user.id} ваше_повідомлення"
    for op in OPERATORS:
        await bot.send_message(op, text, parse_mode='HTML')
    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора. 🙌", reply_markup=end_chat_keyboard())

@dp.message_handler(commands=['reply'])
async def operator_reply(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <повідомлення>")
    user_id = int(args[1])
    text = args[2]
    try:
        await bot.send_message(user_id, f"💡 Відповідь оператора: {text}", reply_markup=end_chat_keyboard())
        await message.reply("✅ Відповідь надіслано")
    except:
        await message.reply("❌ Не вдалося надіслати повідомлення користувачу")

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("🔕 Розмову завершено. Ви можете звернутись ще раз у будь-який час.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    try:
        doc = InputFile(TERMS_FILE)
        await bot.send_document(message.chat.id, doc, caption="📎 Умови використання додатка TEMP")
    except Exception as e:
        await message.answer("⚠️ Файл не знайдено. Зверніться до адміністратора.")


def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔚 Завершити розмову"))
    return keyboard

def end_chat_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔚 Завершити розмову")
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
