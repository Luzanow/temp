import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = os.getenv("ADMIN_CHAT_ID")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

class Form(StatesGroup):
    location = State()
    size = State()
    duration = State()
    name = State()
    phone = State()

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📍 Переглянути локації", callback_data="view_locations"),
        InlineKeyboardButton("📦 Орендувати бокс", callback_data="rent_box"),
        InlineKeyboardButton("📞 Зв’язатись з нами", callback_data="contact")
    )
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("👋 Вітаємо в MyBox! Оберіть дію:", reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("👋 Вітаємо в MyBox! Оберіть дію:", reply_markup=get_main_menu())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "contact")
async def contact_info(callback_query: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🌐 Сайт MyBox", url="https://www.mybox.kiev.ua"),
        InlineKeyboardButton("💬 Написати в Telegram", url="https://t.me/+380959387317"),
        InlineKeyboardButton("⬅️ Повернутись назад", callback_data="back_to_main")
    )
    await bot.send_message(callback_query.from_user.id, "📞 Контактна інформація:\n👤 Тарас\n📱 +380 95 938 7317", reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "view_locations")
async def view_locations(callback_query: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    locations = [
        ("📍 вул. Новокостянтинівська, 22/15", "https://maps.app.goo.gl/RpDz2E671UVgkQg57"),
        ("📍 просп. Відрадний, 107", "https://maps.app.goo.gl/gjmy3mC4TmWH27r87"),
        ("📍 вул. Кирилівська, 41", "https://maps.app.goo.gl/5QYTYfAWqQ7W8pcm7"),
        ("📍 вул. Дегтярівська, 21", "https://maps.app.goo.gl/2zrWpCkeF3r5TMh39"),
        ("📍 вул. Cадова, 16", "https://maps.app.goo.gl/sCb6wYY3YQtVwVao7"),
        ("📍 вул. Безняковская, 21", "https://maps.google.com/?q=50.402645,30.324247"),
        ("📍 вул. Миколи Василенка, 2", "https://maps.app.goo.gl/Cp6tUB7DGbLz3bdFA"),
        ("📍 вул. Вінстона Черчилля, 42", "https://maps.app.goo.gl/FNuaeyQHFxaxgCai9"),
        ("📍 вул. Лугова 9", "https://maps.app.goo.gl/aCrfjN9vbBjhM17YA"),
        ("📍 вул. Євгенія Харченка, 35", "https://maps.app.goo.gl/MpGAvtA6awMYKn7s6"),
        ("📍 вул. Володимира Брожка, 38/58", "https://maps.app.goo.gl/vZAjD6eo84t8qyUk6"),
        ("📍 вул. Межигірська, 78", "https://maps.app.goo.gl/MpGAvtA6awMYKn7s6")
    ]
    for name, url in locations:
        kb.add(InlineKeyboardButton(name, url=url))
    kb.add(InlineKeyboardButton("⬅️ Повернутись назад", callback_data="back_to_main"))
    await bot.send_message(callback_query.from_user.id, "📌 Оберіть локацію для перегляду на карті:", reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "rent_box")
async def start_request(callback_query: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    addresses = [
        "📍 вул. Новокостянтинівська, 22/15",
        "📍 просп. Відрадний, 107",
        "📍 вул. Кирилівська, 41",
        "📍 вул. Дегтярівська, 21",
        "📍 вул. Cадова, 16",
        "📍 вул. Безняковская, 21",
        "📍 вул. Миколи Василенка, 2",
        "📍 вул. Вінстона Черчилля, 42",
        "📍 вул. Лугова 9",
        "📍 вул. Євгенія Харченка, 35",
        "📍 вул. Володимира Брожка, 38/58",
        "📍 вул. Межигірська, 78"
    ]
    for addr in addresses:
        kb.add(InlineKeyboardButton(addr, callback_data=f"loc_{addr}"))
    kb.add(InlineKeyboardButton("⬅️ Повернутись назад", callback_data="back_to_main"))
    await Form.location.set()
    await bot.send_message(callback_query.from_user.id, "📍 Оберіть локацію для оренди:", reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("loc_"), state=Form.location)
async def get_location(callback_query: types.CallbackQuery, state: FSMContext):
    location = callback_query.data.replace("loc_", "")
    await state.update_data(location=location)
    kb = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("📐 5 м²", callback_data="size_5"),
        InlineKeyboardButton("📐 10 м²", callback_data="size_10"),
        InlineKeyboardButton("📐 15 м²", callback_data="size_15")
    )
    await Form.size.set()
    await bot.send_message(callback_query.from_user.id, "📦 Оберіть розмір контейнера:", reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("size_"), state=Form.size)
async def get_size(callback_query: types.CallbackQuery, state: FSMContext):
    size = callback_query.data.replace("size_", "") + " м²"
    await state.update_data(size=size)
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🗓 1–3 місяці", callback_data="dur_1"),
        InlineKeyboardButton("🗓 3–6 місяців (-5%)", callback_data="dur_3"),
        InlineKeyboardButton("🗓 6–12 місяців (-10%)", callback_data="dur_6")
    )
    await Form.duration.set()
    await bot.send_message(callback_query.from_user.id, "🧾 Знижка діє лише при повній оплаті за вибраний період.\n⏳ Оберіть термін оренди:", reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("dur_"), state=Form.duration)
async def get_duration(callback_query: types.CallbackQuery, state: FSMContext):
    duration = {
        "dur_1": "1–3 місяці",
        "dur_3": "3–6 місяців (-5%)",
        "dur_6": "6–12 місяців (-10%)"
    }[callback_query.data]
    await state.update_data(duration=duration)
    await Form.name.set()
    await bot.send_message(callback_query.from_user.id, "👤 Введіть ваше ім’я:")
    await callback_query.answer()

@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Form.phone.set()
    await message.answer("📞 Введіть ваш номер телефону:")

@dp.message_handler(state=Form.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    text = (
        f"✅ Нова заявка!\n\n📍 Локація: {data['location']}\n"
        f"📐 Розмір: {data['size']}\n"
        f"⏳ Термін: {data['duration']}\n"
        f"👤 Ім’я: {data['name']}\n"
        f"📞 Телефон: {data['phone']}"
    )
    await bot.send_message(ADMIN_ID, text)
    await message.answer("🚀 Ваша заявка надіслана!", reply_markup=get_main_menu())
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)
