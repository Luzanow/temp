import logging
import asyncio
import os
import re
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

TERMS_FILE_PATH = "full_temp_terms.pdf"

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
    await asyncio.sleep(600)
    if user_state[message.from_user.id].get('awaiting_response'):
        await message.answer("⌛ Усі оператори зараз зайняті. Очікуйте, будь ласка. 🙏", reply_markup=back_keyboard())

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('awaiting_response'))
async def forward_to_operator(message: types.Message):
    user = user_state[message.from_user.id]
    user['awaiting_response'] = False
    operator_reply_mode[message.from_user.id] = message.chat.id
    text = f"📩 Запит від <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{message.text}\n\n👨‍💻 Для відповіді: просто зробіть reply на це повідомлення"
    for op in OPERATORS:
        await bot.send_message(op, text, parse_mode='HTML')
    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора. 🙌", reply_markup=back_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    if os.path.exists(TERMS_FILE_PATH):
        await bot.send_document(message.chat.id, open(TERMS_FILE_PATH, 'rb'))
    else:
        await message.answer("❌ Не вдалося знайти файл умов використання.")

@dp.message_handler(lambda msg: msg.text == "🔙 Повернутись назад")
async def back_to_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("🔄 Ви повернулись у головне меню.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id in OPERATORS)
async def handle_operator_reply(msg: types.Message):
    if not msg.reply_to_message:
        return

    text = msg.reply_to_message.text
    match = re.search(r"<code>(\+?\d+)</code>", text)
    if not match:
        await msg.reply("❗ Не вдалося визначити користувача.")
        return
    phone = match.group(1)

    for user_id, data in user_state.items():
        if data.get("phone") == phone:
            await bot.send_message(user_id, f"💬 Відповідь оператора:\n{msg.text}", reply_markup=back_keyboard())
            await msg.reply("✅ Відповідь надіслано.")
            return

    await msg.reply("❗ Користувача з цим номером не знайдено.")

def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Повернутись назад"))
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
