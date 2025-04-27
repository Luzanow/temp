import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")  # Ваш токен бота
OPERATORS = [5498505652]  # Ідентифікатори операторів, змініть на актуальні

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером телефону", request_contact=True))
    return kb

def waiting_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити розмову"))
    return kb

def operator_accept_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"✅ Прийняти розмову від {user_state[user_id]['name']}", callback_data=f"accept_{user_id}"))
    return kb

def operator_end_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔚 Завершити розмову", callback_data="end_chat"))
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
    # Переходимо до наступного етапу після того, як номер поділений
    await message.answer("🖊 Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

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

    # Повідомлення оператору з кнопкою "Прийняти розмову"
    for op_id in OPERATORS:
        await bot.send_message(
            op_id,
            f"🆕 <b>Нове звернення</b> 🆕\n\n"
            f"👤 Ім'я: <b>{user_state[user_id]['name']}</b>\n"
            f"📞 Телефон: <code>{user_state[user_id]['phone']}</code>\n\n"
            f"📝 Питання:\n<blockquote>{user_state[user_id]['question']}</blockquote>\n\n"
            "Натисніть на кнопку нижче, щоб прийняти цю розмову ⬇️",
            parse_mode="HTML",
            reply_markup=operator_accept_keyboard(user_id)
        )

    await message.answer(
        "⏳ Дякуємо за ваше звернення!\n"
        "Будь ласка, зачекайте — ми під'єднуємо оператора...",
        reply_markup=waiting_keyboard()
    )

    asyncio.create_task(waiting_timeout(user_id))

async def waiting_timeout(user_id):
    await asyncio.sleep(300)
    if user_id in user_state and user_id not in active_chats:
        await bot.send_message(user_id, "⏳ Вибачте, всі оператори зайняті. Ми обов'язково вам відповімо найближчим часом!")

# Оператор приймає розмову
@dp.callback_query_handler(lambda c: c.data.startswith("accept_"))
async def accept_chat(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])  # Отримуємо ID користувача з callback data
    operator_id = callback_query.from_user.id
    
    # Повідомлення користувачу про те, що оператор приєднався
    await bot.send_message(user_id, f"🎉 Оператор приєднався до чату! Починайте спілкуватися!")
    active_chats[user_id] = {'operator_id': operator_id}

    # Повідомлення оператору
    await bot.send_message(operator_id, f"💬 Ви тепер у чаті з користувачем {user_state[user_id]['name']}. Починайте спілкуватися.")
    await callback_query.answer()
    await callback_query.message.edit_text("💬 Ви прийняли цю розмову.", reply_markup=operator_end_keyboard())

# Оператор відповідає користувачу
@dp.message_handler(lambda m: m.from_user.id in active_chats)
async def operator_reply(message: types.Message):
    user_id = active_chats[message.from_user.id]['operator_id']
    # Відправляємо повідомлення користувачу
    await bot.send_message(
        user_id,
        f"👤 Оператор пише:\n\n{message.text}",
        parse_mode="HTML"
    )

# Користувач може писати тільки після того, як оператор прийняв розмову
@dp.message_handler(lambda m: m.from_user.id in user_state and m.from_user.id not in active_chats)
async def wait_for_operator(message: types.Message):
    await message.answer("⏳ Чекайте, поки оператор приєднається до чату.")

# Завершення чату
@dp.callback_query_handler(lambda c: c.data == "end_chat")
async def end_chat(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id in active_chats:
        op_id = active_chats[user_id]['operator_id']
        await bot.send_message(op_id, f"🔔 Користувач {user_state[user_id]['name']} завершив розмову.")
        active_chats.pop(user_id, None)
        await bot.send_message(user_id, "✅ Розмову завершено. Натисніть /start, щоб почати нову консультацію.")
        await callback_query.answer()

    elif user_id in [chat.get('operator_id') for chat in active_chats.values()]:
        for uid, chat in list(active_chats.items()):
            if chat.get('operator_id') == user_id:
                await bot.send_message(uid, "🔔 Оператор завершив розмову.")
                active_chats.pop(uid, None)

        await bot.send_message(user_id, "✅ Ви завершили обслуговування клієнта.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
