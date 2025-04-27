from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Створення клавіатури для оператора
def operator_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Прийняти діалог"))
    kb.add(KeyboardButton("🔙 Завершити розмову"))
    return kb

# Старт розмови з користувачем (Користувач натискає кнопку "Зв'язатись з оператором")
@dp.message_handler(lambda msg: msg.text == "💬 Зв’язатися з оператором")
async def connect_to_operator(message: types.Message):
    user_id = message.from_user.id
    user = user_state.get(user_id)
    if not user:
        return await message.answer("⚠️ Помилка. Спочатку поділіться номером телефону.")
    
    user_state[user_id]['chat_active'] = True
    active_chats[user_id] = True
    
    # Оператор отримує повідомлення з кнопкою "Прийняти діалог"
    for op in OPERATORS:
        await bot.send_message(op, f"📨 Нове звернення від <b>{user['name']}</b> <code>{user['phone']}</code>.\nЩоб відповісти, натисніть кнопку 'Прийняти діалог'.", reply_markup=operator_keyboard(), parse_mode='HTML')
    
    await message.answer("📝 Опишіть вашу проблему нижче.", reply_markup=types.ReplyKeyboardRemove())

# Обробка повідомлень від оператора
@dp.message_handler(lambda msg: active_chats.get(msg.from_user.id) and msg.text != "🔙 Завершити розмову")
async def relay_to_operator(message: types.Message):
    user = user_state.get(message.from_user.id)
    if not user:
        return
    for op in OPERATORS:
        await bot.send_message(op, f"✉️ {user['name']}: {message.text}")

# Обробка відповіді оператора на повідомлення користувача
@dp.message_handler(lambda msg: msg.reply_to_message and msg.from_user.id in OPERATORS)
async def operator_reply(message: types.Message):
    reply_text = message.reply_to_message.text
    try:
        # Визначаємо користувача, на чиє повідомлення відповідає оператор
        user_id_line = [line for line in reply_text.split('\n') if '>' not in line][-1]
        name = user_id_line.split(':')[0].replace('✉️', '').strip()
        user_id = next((uid for uid, data in user_state.items() if data.get('name') == name), None)
        if not user_id:
            return await message.reply("⚠️ Не вдалося визначити користувача")
        
        # Надсилаємо відповідь користувачу
        await bot.send_message(user_id, f"💬 Відповідь оператора: {message.text}")
    except Exception as e:
        await message.reply("❌ Помилка відповіді користувачу")

# Завершення розмови
@dp.message_handler(lambda msg: msg.text == "🔙 Завершити розмову")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    active_chats.pop(user_id, None)
    user_state.get(user_id, {}).pop('chat_active', None)
    await message.answer("🔚 Розмову завершено. Натисніть /start, щоб почати знову.", reply_markup=types.ReplyKeyboardRemove())
    
    # Повідомлення оператору про завершення розмови
    for op in OPERATORS:
        await bot.send_message(op, f"🔔 Користувач {user_state.get(user_id, {}).get('name', 'Користувач')} завершив розмову.")
