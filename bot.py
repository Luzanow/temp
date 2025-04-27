import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS = [5498505652]  # Список операторів

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

user_state = {}
active_chats = {}

# Клавіатури
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитись номером", request_contact=True))
    return kb

def waiting_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити розмову"))
    return kb

def operator_accept_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Прийняти розмову"))
    return kb

def operator_finish_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершити діалог"))
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
    if message.contact:
        user_state[message.from_user.id] = {'phone': message.contact.phone_number}
        await message.delete_reply_markup()  # Видаляємо кнопку після того, як номер надіслано
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

    # Повідомлення оператору з кнопкою прийняти розмову
    for op_id in OPERATORS:
        await bot.send_message(
            op_id,
            f"🆕 <b>Нове звернення</b> 🆕\n\n"
            f"👤 Ім'я: <b>{user_state[user_id]['name']}</b>\n"
            f"📞 Телефон: <code>{user_state[user_id]['phone']}</code>\n\n"
            f"📝 Питання:\n<blockquote>{user_state[user_id]['question']}</blockquote>\n\n"
            "Натисніть у відповіді, щоб почати діалог ⬇️",
            parse_mode="HTML",
            reply_markup=operator_accept_keyboard()
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
@dp.message_handler(lambda message: message.text == "✅ Прийняти розмову" and message.from_user.id in OPERATORS)
async def operator_accept(message: types.Message):
    user_id = message.reply_to_message.from_user.id
    active_chats[user_id] = {'operator_id': message.from_user.id}

    # Повідомлення користувачу
    await bot.send_message(
        user_id,
        f"💬 Оператор TEMP почав з вами спілкуватися! 🚀",
        reply_markup=waiting_keyboard()
    )

    # Повідомлення оператору
    await bot.send_message(
        message.from_user.id,
        f"🔔 Ви почали розмову з користувачем {user_state[user_id]['name']}.",
        reply_markup=operator_finish_keyboard()  # Кнопка завершення для оператора
    )
    await message.answer("💬 Тепер ви можете вільно відповідати на повідомлення користувача.")

# Оператор відповідає користувачу
@dp.message_handler(lambda message: message.from_user.id in OPERATORS and message.reply_to_message)
async def operator_reply(message: types.Message):
    original_text = message.reply_to_message.text

    target_user = None
    for uid, info in user_state.items():
        if info.get('name') in original_text and info.get('phone') in original_text:
            target_user = uid
            break

    if target_user:
        await bot.send_message(
            target_user,
            f"💬 <b>Оператор TEMP:</b>\n\n{message.text}",
            parse_mode="HTML",
            reply_markup=waiting_keyboard()
        )
    else:
        await message.reply("⚠️ Не вдалося знайти користувача для відповіді.")

# Користувач пише оператору
@dp.message_handler(lambda m: m.from_user.id in active_chats)
async def user_message(message: types.Message):
    op_id = active_chats[message.from_user.id]['operator_id']
    await bot.send_message(
        op_id,
        f"👤 <b>{user_state[message.from_user.id]['name']}</b> пише:\n\n{message.text}",
        parse_mode="HTML"
    )

# Завершення розмови
@dp.message_handler(lambda m: m.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id

    if user_id in active_chats:
        op_id = active_chats[user_id]['operator_id']
        await bot.send_message(op_id, f"🔔 Користувач {user_state[user_id]['name']} завершив розмову.")
        active_chats.pop(user_id, None)
        await message.answer(
            "✅ Розмову завершено. Дякуємо за звернення! Будь ласка, натисніть /start для початку нової консультації.",
            reply_markup=start_keyboard()
        )
        # Повідомлення користувачу після завершення
        await bot.send_message(
            user_id,
            "💬 Дякуємо, що звернулися до нас! Якщо у вас будуть ще питання, ми завжди на зв'язку. Бажаємо вам чудового дня! 🌟"
        )

    elif user_id in [chat.get('operator_id') for chat in active_chats.values()]:
        for uid, chat in list(active_chats.items()):
            if chat.get('operator_id') == user_id:
                await bot.send_message(uid, "🔔 Оператор завершив розмову.")
                active_chats.pop(uid, None)

        await message.answer(
            "✅ Ви завершили обслуговування клієнта.",
            reply_markup=types.ReplyKeyboardRemove()
        )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
