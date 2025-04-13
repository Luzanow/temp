import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o")  # Забери токен із .env файлу або встав напряму
OPERATORS = [5498505652]  # Список ID операторів

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}
operator_reply_mode = {}

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
    user_state[message.from_user.id]['chat_active'] = False
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['awaiting_response'] = True
    user_state[message.from_user.id]['chat_active'] = True
    operator_reply_mode[message.from_user.id] = message.chat.id
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор побачить повідомлення та відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())
    await asyncio.sleep(600)
    if user_state[message.from_user.id].get('awaiting_response'):
        await message.answer("⌛ Розмову завершено через неактивність.", reply_markup=back_keyboard())
        await notify_operator_end(message.from_user.id)
        user_state[message.from_user.id]['chat_active'] = False

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('chat_active'))
async def forward_to_operator(message: types.Message):
    uid = message.from_user.id
    if not user_state[uid].get("chat_active"):
        return
    user_state[uid]['awaiting_response'] = False
    text = f"📩 Повідомлення від <b>{user_state[uid]['name']}</b> (<code>{user_state[uid]['phone']}</code>):\n{message.text}\n\n👨‍💻 Для відповіді: /reply {uid} ваше_повідомлення"
    for op in OPERATORS:
        await bot.send_message(op, text, parse_mode='HTML')
    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора.", reply_markup=end_keyboard())

@dp.message_handler(commands=['reply'])
async def operator_reply(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❗ Формат: /reply <user_id> <повідомлення>")
    user_id = int(args[1])
    text = args[2]
    try:
        await bot.send_message(user_id, f"💡 Відповідь оператора: {text}", reply_markup=end_keyboard())
        await message.reply("✅ Відповідь надіслано")
    except:
        await message.reply("❌ Не вдалося надіслати повідомлення користувачу")

@dp.message_handler(lambda msg: msg.text == "🔚 Завершити розмову")
async def end_conversation(message: types.Message):
    uid = message.from_user.id
    if uid in user_state:
        user_state[uid]['chat_active'] = False
        await message.answer("❎ Розмову завершено.", reply_markup=main_keyboard())
        await notify_operator_end(uid)

def notify_operator_end(uid):
    text = f"⚠️ Користувач <b>{user_state[uid]['name']}</b> завершив розмову."
    return asyncio.gather(*(bot.send_message(op, text, parse_mode='HTML') for op in OPERATORS))

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    try:
        with open("terms_temp.pdf", "rb") as doc:
            await message.answer_document(doc, caption="📄 Умови використання додатка Temp")
    except Exception as e:
        await message.answer("❗ Помилка: не вдалося знайти файл з умовами.")

@dp.message_handler(lambda msg: msg.text == "🔙 Повернутись назад")
async def back_to_menu(message: types.Message):
    await message.answer("🔄 Ви повернулись у головне меню.", reply_markup=main_keyboard())

def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Повернутись назад"))
    return keyboard

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    keyboard.add("📄 Умови використання Temp")
    return keyboard

def end_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔚 Завершити розмову")
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
