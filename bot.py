import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv

# Завантаження токенів з файлу .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")  # Замініть на свій токен
OPERATORS = [5498505652]  # Список ID операторів

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Функція для клавіатури оператора
def operator_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Прийняти діалог"))
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Функція для клавіатури користувача
def start_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add(KeyboardButton("📄 Умови використання Temp"))
    return kb

# Хендлер для /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Привіт! Поділіться номером телефону, щоб розпочати спілкування.", reply_markup=start_keyboard())

# Хендлер для поділу контактом
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    # Тут можна зберігати контакт у словнику
    user_id = message.from_user.id
    user_state[user_id] = {'phone': message.contact.phone_number}
    await message.answer("✏️ Введіть ваше ім'я:", reply_markup=types.ReplyKeyboardRemove())

# Хендлер для введення імені
@dp.message_handler(lambda msg: msg.from_user.id in user_state and 'name' not in user_state[msg.from_user.id])
async def handle_name(message: types.Message):
    user_state[message.from_user.id]['name'] = message.text
    await message.answer("✅ Дякуємо! Натисніть нижче, щоб зв'язатись з оператором.", reply_markup=operator_keyboard())

# Хендлер для кнопки "Зв'язатись з оператором"
@dp.message_handler(lambda msg: msg.text == "✅ Прийняти діалог")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user = user_state.get(user_id)
    if not user:
        return await message.answer("⚠️ Помилка. Спочатку поділіться номером телефону.")
    
    # Повідомлення операторам
    for op in OPERATORS:
        await bot.send_message(op, f"📨 Нове звернення від {user['name']} {user['phone']}. Щоб відповісти, натисніть 'Прийняти діалог'.", reply_markup=operator_keyboard())

    await message.answer("📝 Опишіть вашу проблему.", reply_markup=types.ReplyKeyboardRemove())

# Хендлер для прийому повідомлення від оператора
@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id in OPERATORS)
async def operator_reply(message: types.Message):
    reply_text = message.reply_to_message.text
    user_id_line = [line for line in reply_text.split('\n') if '>' not in line][-1]
    name = user_id_line.split(':')[0].replace('✉️', '').strip()
    user_id = next((uid for uid, data in user_state.items() if data.get('name') == name), None)
    
    if not user_id:
        return await message.reply("⚠️ Не вдалося визначити користувача")
    
    # Відправлення відповіді користувачу
    await bot.send_message(user_id, f"💬 Відповідь оператора: {message.text}")

# Завершення розмови
@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    user_state.get(user_id, {}).pop('chat_active', None)
    await message.answer("🔚 Розмову завершено. Натисніть /start, щоб почати знову.", reply_markup=types.ReplyKeyboardRemove())

    for op in OPERATORS:
        await bot.send_message(op, f"🔔 Користувач {user_state.get(user_id, {}).get('name', 'Користувач')} завершив розмову.")

# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
