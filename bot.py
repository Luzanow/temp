
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
import asyncio

API_TOKEN = '7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o'
OPERATORS = [5498505652]  # ID операторів (можна додати більше)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}

# /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔧 Зв’язатися з оператором"))
    await message.answer(f"Вітаємо, {message.from_user.first_name}!")
Як можемо допомогти?", reply_markup=keyboard)

# Коли користувач натискає на кнопку
@dp.message_handler(lambda message: message.text == "🔧 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id] = {'awaiting_response': True}
    await message.answer("✍️ Опишіть вашу проблему. Оператор відповість вам тут.")
    await asyncio.sleep(180)  # 3 хвилини
    if user_state.get(message.from_user.id, {}).get('awaiting_response'):
        await message.answer("⏳ Всі оператори наразі зайняті. Очікуйте, будь ласка.")

# Всі інші повідомлення → оператору
@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('awaiting_response'))
async def forward_to_operator(message: types.Message):
    for op_id in OPERATORS:
        try:
            await bot.send_message(op_id, f"📩 Запит від @{message.from_user.username or 'Користувач'}:
{message.text}")
        except BotBlocked:
            pass
    await message.answer("✅ Ваше повідомлення передано оператору.")
    user_state[message.from_user.id]['awaiting_response'] = False

# Відповідь оператора (повинна починатись з /reply USER_ID текст)
@dp.message_handler(lambda message: message.from_user.id in OPERATORS and message.text.startswith("/reply"))
async def operator_reply(message: types.Message):
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.reply("❌ Формат: /reply USER_ID текст")
        return
    user_id, text = parts[1], parts[2]
    try:
        await bot.send_message(int(user_id), f"💬 Відповідь оператора:
{text}")
        await message.reply("✅ Відповідь надіслано.")
    except Exception as e:
        await message.reply(f"❌ Помилка: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
