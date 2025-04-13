import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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
    await message.answer("✏️ Введіть своє ім’я:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text and msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def save_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_state[message.from_user.id]['awaiting_response'] = True
    await message.answer("📝 Опишіть вашу проблему нижче. Оператор побачить повідомлення та відповість вам тут.", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(180)
    if user_state[message.from_user.id].get('awaiting_response'):
        await message.answer("⌛ Усі оператори зараз зайняті. Очікуйте, будь ласка. 🙏", reply_markup=back_keyboard())

@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('awaiting_response'))
async def forward_to_operator(message: types.Message):
    user = user_state[message.from_user.id]
    user['awaiting_response'] = False
    operator_reply_mode[message.from_user.id] = message.chat.id
    text = f"📩 Запит від <b>{user.get('name')}</b> (<code>{user.get('phone')}</code>):\n{message.text}"
    for op in OPERATORS:
        await bot.send_message(op, text, parse_mode='HTML', reply_markup=operator_reply_keyboard(message.from_user.id))
    await message.answer("📨 Ваше повідомлення надіслано. Очікуйте відповідь оператора. 🙌", reply_markup=back_keyboard())

@dp.message_handler(lambda msg: msg.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    try:
        await bot.send_document(message.chat.id, open(TERMS_FILE_PATH, 'rb'))
    except Exception as e:
        await message.answer("❌ Не вдалося знайти документ з умовами використання.")

@dp.callback_query_handler(lambda c: c.data.startswith("reply_"))
async def operator_quick_reply(callback_query: types.CallbackQuery):
    target_user_id = int(callback_query.data.split("_")[1])
    await bot.send_message(callback_query.message.chat.id, f"✏️ Введіть відповідь для користувача {target_user_id}:")
    operator_reply_mode[callback_query.from_user.id] = target_user_id

@dp.message_handler(lambda message: message.from_user.id in OPERATORS and message.from_user.id in operator_reply_mode)
async def send_operator_response(message: types.Message):
    target_user_id = operator_reply_mode[message.from_user.id]
    try:
        await bot.send_message(target_user_id, f"💡 Відповідь оператора: {message.text}", reply_markup=back_keyboard())
        await message.answer("✅ Відповідь надіслано")
        del operator_reply_mode[message.from_user.id]
    except:
        await message.answer("❌ Не вдалося надіслати повідомлення користувачу")

@dp.message_handler(lambda msg: msg.text == "🔙 Повернутись назад")
async def back_to_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Зв’язатися з оператором"))
    await message.answer("🔄 Ви повернулись у головне меню.", reply_markup=keyboard)

def back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Повернутись назад"))
    return keyboard

def operator_reply_keyboard(user_id):
    inline = types.InlineKeyboardMarkup()
    inline.add(types.InlineKeyboardButton("↩️ Відповісти", callback_data=f"reply_{user_id}"))
    return inline

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
