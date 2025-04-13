import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o")
OPERATORS = [5498505652]  # заміни на реальні ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}

# Старт
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Поділитися номером", request_contact=True))
    await message.answer("Привіт! Щоб почати, поділіться своїм номером телефону.", reply_markup=keyboard)

# Обробка контакту
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("Дякуємо! Введіть своє ім’я:", reply_markup=types.ReplyKeyboardRemove())

# Отримання імені та кнопка зв'язку
@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🖋 Зв’язатися з оператором"))
    await message.answer("Дякуємо! Тепер можете зв’язатися з оператором.", reply_markup=keyboard)

# Зв'язок з оператором
@dp.message_handler(lambda msg: msg.text == "🖋 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['awaiting_response'] = True
    await message.answer("✍️ Опишіть вашу проблему. Оператор відповість вам тут.", reply_markup=types.ReplyKeyboardRemove())
    await asyncio.sleep(180)
    if user_state[message.from_user.id].get('awaiting_response'):
        await message.answer("⏳ Всі оператори наразі зайняті. Очікуйте, будь ласка.", reply_markup=back_keyboard())

# Повідомлення ➝ оператору
@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('awaiting_response'))
async def forward_to_operator(message: types.Message):
    user = user_state[message.from_user.id]
    user['awaiting_response'] = False
    text = f"📩 Запит від {user.get('name')} ({user.get('phone')}):\n{message.text}"
    for op in OPERATORS:
        await bot.send_message(op, text)
    await message.answer("✅ Дякуємо, оператор відповість вам найближчим часом.", reply_markup=back_keyboard())

# Повернення назад
@dp.message_handler(lambda msg: msg.text == "🔙 Повернутись назад")
async def back_to_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🖋 Зв’язатися з оператором"))
    await message.answer("Ви повернулись в головне меню.", reply_markup=keyboard)

def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Повернутись назад"))
    return keyboard

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
