import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS = [5498505652]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Надіслати номер телефону", request_contact=True))
    return kb

def waiting_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити розмову"))
    return kb

def operator_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Прийняти розмову"), KeyboardButton("❌ Завершити розмову"))
    return kb

# Старт
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_state.pop(message.from_user.id, None)
    await message.answer(
        "👋 Вітаємо у службі підтримки <b>TEMP</b>!\n\n"
        "Будь ласка, надішліть свій номер телефону, натиснувши кнопку нижче 👇",
        reply_markup=start_keyboard()
    )

# Контакт
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    user_state[message.from_user.id] = {'phone': message.contact.phone_number}
    await message.answer("🖊 Введіть ваше ім’я:")

# Ім'я
@dp.message_handler(lambda m: m.from_user.id in user_state and 'name' not in user_state[m.from_user.id])
async def name_handler(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("📝 Коротко опишіть вашу проблему або запитання:")

# Питання
@dp.message_handler(lambda m: m.from_user.id in user_state and 'question' not in user_state[m.from_user.id])
async def question_handler(message: types.Message):
    user_state[message.from_user.id]['question'] = message.text
    user_id = message.from_user.id

    # Повідомлення оператору
    for op_id in OPERATORS:
        await bot.send_message(
            op_id,
            f"🆕 <b>Нове звернення</b> 🆕\n\n"
            f"👤 Ім'я: <b>{user_state[user_id]['name']}</b>\n"
            f"📞 Телефон: <code>{user_state[user_id]['phone']}</code>\n\n"
            f"📝 Питання:\n<blockquote>{user_state[user_id]['question']}</blockquote>\n\n"
            "Натисніть на кнопку нижче, щоб прийняти розмову або завершити.",
            parse_mode="HTML",
            reply_markup=operator_keyboard()  # Кнопки для оператора
        )

    await message.answer(
        "⏳ Дякуємо за ваше звернення!\n"
        "Будь ласка, зачекайте — ми під'єднуємо оператора...",
        reply_markup=waiting_keyboard()
    )

# Оператор приймає розмову
@dp.message_handler(lambda message: message.text == "✅ Прийняти розмову" and message.from_user.id in OPERATORS)
async def accept_chat(message: types.Message):
    user_id = message.reply_to_message.from_user.id
    active_chats[user_id] = {'operator_id': message.from_user.id}
    await bot.send_message(
        user_id,
        f"💬 <b>Оператор TEMP:</b> Оператор прийняв вашу розмову. Ви можете почати спілкування.",
        parse_mode="HTML",
        reply_markup=waiting_keyboard()
    )
    await message.answer("✅ Ви прийняли розмову з користувачем.")

# Оператор завершить розмову
@dp.message_handler(lambda message: message.text == "❌ Завершити розмову" and message.from_user.id in OPERATORS)
async def end_chat_operator(message: types.Message):
    user_id = message.reply_to_message.from_user.id
    await bot.send_message(
        user_id,
        "⏹ Розмову завершено оператором. Дякуємо, що звернулися до нас!",
        parse_mode="HTML",
        reply_markup=start_keyboard()
    )
    active_chats.pop(user_id, None)
    await message.answer("✅ Розмову завершено.")

# Користувач завершує розмову
@dp.message_handler(lambda message: message.text == "🔚 Завершити розмову" and message.from_user.id not in OPERATORS)
async def end_chat_user(message: types.Message):
    user_id = message.from_user.id

    if user_id in active_chats:
        op_id = active_chats[user_id]['operator_id']
        await bot.send_message(op_id, f"🔔 Користувач {user_state[user_id]['name']} завершив розмову.")
        active_chats.pop(user_id, None)
        await message.answer(
            "✅ Розмову завершено. Натисніть /start, щоб почати нову консультацію.",
            reply_markup=start_keyboard()
        )
    else:
        await message.answer("❌ Розмову не можна завершити, оскільки вона ще не була прийнята оператором.")

# Користувач пише оператору
@dp.message_handler(lambda m: m.from_user.id in active_chats)
async def user_message(message: types.Message):
    op_id = active_chats[message.from_user.id]['operator_id']
    await bot.send_message(
        op_id,
        f"👤 <b>{user_state[message.from_user.id]['name']}</b> пише:\n\n{message.text}",
        parse_mode="HTML"
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
