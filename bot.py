import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = "7862608221:AAEixkRNQwwkhBVv0sLGevAdrcA9egHr20o"
ADMIN_CHAT_ID = 5498505652

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

user_states = {}
active_chats = {}

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📞 Зв’язатися з оператором"))
    keyboard.add(KeyboardButton("📄 Умови використання Temp"))
    return keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Поділитися номером", request_contact=True))
    keyboard.add("📄 Умови використання Temp")
    await message.answer("👋 Привіт! Щоб почати, поділіться номером або перегляньте умови.", reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_name(message: types.Message):
    user_states[message.from_user.id] = {
        "phone": message.contact.phone_number,
        "chat_active": False
    }
    await message.answer("✏️ Введіть ваше ім’я:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda message: message.from_user.id in user_states and "name" not in user_states[message.from_user.id])
async def save_name(message: types.Message):
    user_states[message.from_user.id]["name"] = message.text
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💬 Зв’язатися з оператором")
    await message.answer("✅ Дякуємо! Тепер ви можете написати оператору.", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "📄 Умови використання Temp")
async def show_terms(message: types.Message):
    await bot.send_document(message.chat.id, open("full_temp_terms.pdf", "rb"))

@dp.message_handler(lambda message: message.text == "💬 Зв’язатися з оператором")
async def connect(message: types.Message):
    user_states[message.from_user.id]["chat_active"] = True
    active_chats[message.from_user.id] = ADMIN_CHAT_ID
    await message.answer("📝 Опишіть вашу проблему. Оператор відповість вам тут.")
    await asyncio.sleep(600)
    if user_states.get(message.from_user.id, {}).get("chat_active"):
        await message.answer("⌛ Вибачте, оператор наразі не відповів. Спробуйте пізніше.", reply_markup=get_main_keyboard())
        user_states[message.from_user.id]["chat_active"] = False

@dp.message_handler(lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("chat_active"))
async def handle_user_message(message: types.Message):
    data = user_states[message.from_user.id]
    text = f"📩 Повідомлення від користувача:
👤 Ім’я: {data['name']}
📱 Телефон: {data['phone']}
🆔: {message.from_user.id}

{message.text}"
    await bot.send_message(ADMIN_CHAT_ID, text)
    await message.answer("✅ Ваше повідомлення надіслано. Очікуйте відповідь оператора.")

@dp.message_handler(commands=['reply'])
async def reply_to_user(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("❗ Відповідай на повідомлення користувача (свайпом)")

    args = message.text.replace("/reply", "").strip()
    lines = message.reply_to_message.text.splitlines()
    user_line = next((line for line in lines if line.startswith("🆔")), None)
    if not user_line:
        return await message.reply("❌ Не вдалося визначити користувача.")

    try:
        user_id = int(user_line.split(":")[1].strip())
        await bot.send_message(user_id, f"💬 Відповідь оператора:
{args}")
        await message.reply("✅ Відповідь надіслано.")
    except Exception as e:
        await message.reply(f"❌ Не вдалося надіслати повідомлення: {e}")

@dp.message_handler(lambda message: message.text == "🔚 Завершити розмову")
async def end_chat(message: types.Message):
    if message.from_user.id in user_states:
        user_states[message.from_user.id]["chat_active"] = False
        await message.answer("✅ Розмову завершено. Дякуємо!", reply_markup=get_main_keyboard())
        await bot.send_message(ADMIN_CHAT_ID, f"❗ Користувач {message.from_user.id} завершив розмову.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
