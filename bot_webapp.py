import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import time
from telethon import TelegramClient, events

from config import *
from ai_assistant import analyze_product, extract_price_from_text

logging.basicConfig(level=logging.INFO)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client_gs = gspread.authorize(creds)
sheet = client_gs.open_by_key(GOOGLE_SHEET_KEY).get_worksheet(0)

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

API_ID = 34261454
API_HASH = "355f2253d46d196f78d9c704d631818e"
PHONE_NUMBER = "+491623938331"
client_tg = TelegramClient('dana_session', API_ID, API_HASH)

pending_products = {}


# === ГОЛОВНЕ МЕНЮ (ПРИБРАНО ДУБЛЮЮЧІ КНОПКИ) ===
@bot.message_handler(commands=['start'])
def start(message):
    intro_text = (
        "👋 *Ласкаво просимо до DANA SHOP!*\n\n"
        "Ми — магазин стильного та якісного одягу для жінок і чоловіків. "
        "У нас ви знайдете трендові речі, взуття та аксесуари.\n\n"
        "✨ *Чому обирають нас:*\n"
        "• Тільки перевірені постачальники\n"
        "• Швидка доставка\n"
        "• Зручне оформлення замовлення\n\n"
        "👇 *Оберіть розділ:*"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🛍 КАТАЛОГ"),
        types.KeyboardButton("ℹ️ ПРО НАС"),
        types.KeyboardButton("💳 ОПЛАТА/ДОСТАВКА"),
        types.KeyboardButton("📞 КОНТАКТИ")
    )

    bot.send_message(message.chat.id, intro_text, parse_mode="Markdown", reply_markup=markup)


# === КНОПКА КАТАЛОГ (ВІДКРИВАЄ WEBAPP) ===
@bot.message_handler(func=lambda m: m.text == "🛍 КАТАЛОГ")
def catalog(message):
    markup = types.InlineKeyboardMarkup()
    webapp_btn = types.InlineKeyboardButton(
        text="🛒 ВІДКРИТИ КАТАЛОГ",
        url="http://127.0.0.1:5000"
    )
    markup.add(webapp_btn)
    bot.send_message(
        message.chat.id,
        "👇 Натисніть кнопку, щоб перейти до каталогу:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == "ℹ️ ПРО НАС")
def about(message):
    text = (
        "✨ *DANA SHOP* — це команда професіоналів, яка обирає для вас найкраще.\n\n"
        "Ми працюємо з 2026 року та цінуємо кожного клієнта."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "💳 ОПЛАТА/ДОСТАВКА")
def payment(message):
    text = (
        "💳 *ОПЛАТА:*\n"
        "• Накладений платіж (Нова Пошта)\n"
        "• Оплата на карту (ПриватБанк / Моно)\n\n"
        "🚚 *ДОСТАВКА:*\n"
        "• Нова Пошта — 1-3 дні\n"
        "• Укрпошта — 3-7 днів\n\n"
        "Вартість доставки за тарифами перевізника."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "📞 КОНТАКТИ")
def contacts(message):
    bot.send_message(message.chat.id, "📞 Менеджер: @dana_shop_manager\n💬 Відповідаємо з 10:00 до 20:00")


# === ШІ-АСИСТЕНТ (БЕЗ ЗМІН) ===
async def ai_assistant():
    await client_tg.start(phone=PHONE_NUMBER)
    logging.info("🤖 ШІ-асистент запущено")

    @client_tg.on(events.NewMessage(from_users=ADMIN_CHAT_ID))
    async def handler(event):
        message = event.message
        if not message.fwd_from:
            return

        text = message.text or ""
        photo = message.photo
        cost_price = extract_price_from_text(text)

        if not cost_price:
            await client_tg.send_message(ADMIN_CHAT_ID, "❌ Не знайдено ціну.")
            return

        analysis = analyze_product(text, cost_price)

        caption = (
            f"✨ *{analysis['name']}*\n\n"
            f"{analysis['description']}\n\n"
            f"💰 *Ціна:* {analysis['price']} {CURRENCY}"
        )

        product_id = f"prod{int(time.time())}"
        pending_products[product_id] = {
            "name": analysis['name'],
            "price": analysis['price'],
            "description": analysis['description'],
            "photo": photo,
            "original_text": text
        }

        if photo:
            tmp = await client_tg.download_media(photo, file="temp_photo.jpg")
            sent = await client_tg.send_file(
                ADMIN_CHAT_ID,
                tmp,
                caption=f"📦 *ТОВАР НА ЗАТВЕРДЖЕННЯ*\n\n{caption}",
                parse_mode="Markdown"
            )
        else:
            sent = await client_tg.send_message(
                ADMIN_CHAT_ID,
                f"📦 *ТОВАР НА ЗАТВЕРДЖЕННЯ*\n\n{caption}",
                parse_mode="Markdown"
            )

        pending_products[product_id]["msg_id"] = sent.id
        await client_tg.send_message(
            ADMIN_CHAT_ID,
            "👆 *Напиши 'так' або 'ні' у відповідь*",
            parse_mode="Markdown"
        )

    @client_tg.on(events.NewMessage(from_users=ADMIN_CHAT_ID))
    async def reply_handler(event):
        message = event.message
        if not message.is_reply:
            return

        replied_msg_id = message.reply_to.reply_to_msg_id
        reply_text = message.text.lower().strip()

        product_id = None
        product = None
        for pid, p in pending_products.items():
            if p.get("msg_id") == replied_msg_id:
                product_id = pid
                product = p
                break

        if not product:
            await message.reply("❌ Товар не знайдено.")
            return

        if reply_text in ["так", "yes", "ок", "ok", "✅", "👍"]:
            try:
                sheet.append_row([
                    product_id,
                    product["name"],
                    product["price"],
                    "S,M,L,XL",
                    "",
                    product["description"],
                    "active"
                ])
                await message.reply(f"✅ Додано в Таблицю! ID: {product_id}")
            except Exception as e:
                await message.reply(f"❌ Помилка Таблиці: {e}")
                return

            try:
                caption = (
                    f"🖤 *NEW DROP*\n\n"
                    f"✨ *{product['name']}*\n\n"
                    f"{product['description']}\n\n"
                    f"💰 *Ціна:* {product['price']} {CURRENCY}\n\n"
                    f"👇 *Замовляй у боті:* @dana_shop_bot"
                )

                if product["photo"]:
                    with open("temp_photo.jpg", "rb") as f:
                        bot.send_photo(
                            CHANNEL_USERNAME,
                            f,
                            caption=caption,
                            parse_mode="Markdown"
                        )
                else:
                    bot.send_message(
                        CHANNEL_USERNAME,
                        caption,
                        parse_mode="Markdown"
                    )

                await message.reply("✅ ОПУБЛІКОВАНО!")
            except Exception as e:
                await message.reply(f"❌ Помилка публікації: {e}")

            del pending_products[product_id]

        elif reply_text in ["ні", "нет", "no", "❌"]:
            del pending_products[product_id]
            await message.reply("❌ ВІДХИЛЕНО.")

    await client_tg.run_until_disconnected()


# === ЗАПУСК ===
if __name__ == "__main__":
    import asyncio
    import threading


    def run_telethon():
        asyncio.run(ai_assistant())


    threading.Thread(target=run_telethon).start()
    print("🚀 DANA PREMIUM запущено!")
    bot.infinity_polling()