import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import BotBlocked
import asyncio

API_TOKEN = '7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o'
OPERATORS = [5498505652]  # ID операторів

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_state = {}

# /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📞 Зв’язатися з оператором"))
    await message.answer("Як можемо допомогти?", reply_markup=keyboard)

# Коли користувач натискає на кнопку
@dp.message_handler(lambda message: message.text == "📞 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id] = {'awaiting_response': True}
    await message.answer("🟡 Опишіть вашу проблему. Оператор відповість вам тут.")
    await asyncio.sleep(180)
    if user_state.get(message.from_user.id, {}).get('awaiting_response'):
        await message.answer("🔘 Всі оператори наразі зайняті. Очікуйте, будь ласка.")

# Всі інші повідомлення -> оператору
@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('awaiting_response'))
async def forward_to_operator(message: types.Message):
    for op_id in OPERATORS:
        try:
            await bot.send_message(op_id, f"📩 Запит від @{message.from_user.username or 'Користувач'}: \n{message.text}")
        except BotBlocked:
            continue
    await message.answer("✅ Ваше повідомлення надіслано оператору. Очікуйте відповідь.")
    user_state[message.from_user.id]['awaiting_response'] = False

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

