import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from collections import deque

# Telegramdan olingan faol token joylashtirildi
TOKEN = "9009245143:AAFUPCxK636Fn766dFxhezIlGugL1XnLzDE"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Navbatlarni xotirada saqlash uchun ro'yxat (FIFO)
queue_savxoz_dustlik = deque()  # 11-savxoz -> Do'stlik
queue_dustlik_savxoz = deque()  # Do'stlik -> 11-savxoz

# Foydalanuvchilar ma'lumotlari ombori
users_db = {}

# Tugmalar (Klaviaturani shakllantirish)
btn_phone = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
)

menu_role = ReplyKeyboardMarkup(resize_keyboard=True).add("🚖 Haydovchi", "👤 Yo'lovchi")

menu_driver = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1).add(
    "🟢 11-savxo'z ➡️ Do'stlik (Navbatga turish)",
    "🟢 Do'stlik ➡️ 11-savxo'z (Navbatga turish)",
    "❌ Navbatdan chiqish"
)

menu_passenger = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1).add(
    "🔍 11-savxo'zdan taksi chaqirish",
    "🔍 Do'stlikdan taksi chaqirish"
)

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum! Taksichilar va yo'lovchilar navbat tizimi botiga xush kelibsiz.\n"
        "Tizimdan foydalanish uchun telefon raqamingizni yuboring:",
        reply_markup=btn_phone
    )

@dp.message_handler(content_types=['contact'])
async def get_contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    name = message.from_user.full_name
    
    users_db[user_id] = {"name": name, "phone": phone, "role": None}
    
    await message.answer("Raqamingiz qabul qilindi. Botdagi rolingizni tanlang:", reply_markup=menu_role)

@dp.message_handler(lambda message: message.text in ["🚖 Haydovchi", "👤 Yo'lovchi"])
async def set_role(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        return await start_cmd(message)
    
    role = message.text
    users_db[user_id]["role"] = role
    
    if role == "🚖 Haydovchi":
        await message.answer("Haydovchi paneli faollashdi. Navbat yo'nalishini tanlang:", reply_markup=menu_driver)
    else:
        await message.answer("Yo'lovchi paneli faollashdi. Qayerdan taksi qidiryapsiz?", reply_markup=menu_passenger)

# HAYDOVCHILAR UCHUN NAVBAT LOGIKASI
@dp.message_handler(lambda message: "Navbatga turish" in message.text)
async def join_queue(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db or users_db[user_id]["role"] != "🚖 Haydovchi":
        return await message.answer("Siz haydovchi sifatida ro'yxatdan o'tmagansiz.")
    
    if "11-savxo'z ➡️ Do'stlik" in message.text:
        if user_id not in queue_savxoz_dustlik:
            queue_savxoz_dustlik.append(user_id)
        pos = queue_savxoz_dustlik.index(user_id) + 1
        await message.answer(f"Siz '11-savxo'z ➡️ Do'stlik' yo'nalishida navbatga turdingiz. O'rningiz: {pos}")
        
    elif "Do'stlik ➡️ 11-savxo'z" in message.text:
        if user_id not in queue_dustlik_savxoz:
            queue_dustlik_savxoz.append(user_id)
        pos = queue_dustlik_savxoz.index(user_id) + 1
        await message.answer(f"Siz 'Do'stlik ➡️ 11-savxo'z' yo'nalishida navbatga turdingiz. O'rningiz: {pos}")

@dp.message_handler(lambda message: message.text == "❌ Navbatdan chiqish")
async def leave_queue(message: types.Message):
    user_id = message.from_user.id
    removed = False
    
    if user_id in queue_savxoz_dustlik:
        queue_savxoz_dustlik.remove(user_id)
        removed = True
    if user_id in queue_dustlik_savxoz:
        queue_dustlik_savxoz.remove(user_id)
        removed = True
        
    if removed:
        await message.answer("Siz barcha navbatlardan muvaffaqiyatli chiqdingiz.")
    else:
        await message.answer("Siz hech qaysi navbatda yo'q edingiz.")

# YO'LOVCHILAR UCHUN TAKSI CHAQIRISH LOGIKASI
@dp.message_handler(lambda message: "taksi chaqirish" in message.text)
async def call_taxi(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        return await start_cmd(message)
    
    passenger = users_db[user_id]
    selected_queue = None
    direction_text = ""
    
    if "11-savxo'zdan" in message.text:
        selected_queue = queue_savxoz_dustlik
        direction_text = "11-savxo'z ➡️ Do'stlik"
    elif "Do'stlikdan" in message.text:
        selected_queue = queue_dustlik_savxoz
        direction_text = "Do'stlik ➡️ 11-savxo'z"
        
    if selected_queue and len(selected_queue) > 0:
        driver_id = selected_queue.popleft()
        driver = users_db[driver_id]
        
        await message.answer(
            f"🚕 Taksi topildi!\n"
            f"Yo'nalish: {direction_text}\n"
            f"Haydovchi: {driver['name']}\n"
            f"Telefon raqami: {driver['phone']}\n"
            f"Iltimos, haydovchi bilan bog'laning."
        )
        
        await bot.send_message(
            driver_id,
            f"🔔 Sizga yangi buyurtma tushdi va siz navbatdan chiqdingiz!\n"
            f"Yo'lovchi: {passenger['name']}\n"
            f"Telefon raqami: {passenger['phone']}\n"
            f"Iltimos, yo'lovchi bilan tezda bog'laning."
        )
    else:
        await message.answer("Hozircha ushbu yo'nalishda navbatda turgan taksi yo'q. Birozdan so'ng qayta urinib ko'ring.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
