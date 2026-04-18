from flask import Flask, render_template, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEET_KEY, CURRENCY, ADMIN_CHAT_ID
import telebot
import logging
import os

app = Flask(__name__, template_folder='templates')
logging.basicConfig(level=logging.INFO)

# Підключення до Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_KEY).get_worksheet(0)

# Тимчасово для сповіщень (бот)
BOT_TOKEN = "8761808805:AAGB2YrGSScbTra1j8BxvcmLyemojCuz354"
bot = telebot.TeleBot(BOT_TOKEN)


@app.route('/')
def index():
    return render_template('index.html', currency=CURRENCY)


@app.route('/api/products')
def get_products():
    rows = sheet.get_all_values()[1:]
    products = []
    for row in rows:
        if len(row) >= 7 and row[6].lower() == "active":
            products.append({
                "id": row[0],
                "name": row[1],
                "price": int(row[2]),
                "sizes": row[3],
                "photo": row[4],
                "description": row[5]
            })
    return jsonify(products)


@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.json
    product_id = data.get('product_id')
    size = data.get('size')
    name = data.get('name')
    city = data.get('city')
    address = data.get('address')
    phone = data.get('phone')
    payment = data.get('payment')

    try:
        cell = sheet.find(product_id, in_column=1)
        row = sheet.row_values(cell.row)
        product_name = row[1]
        price = row[2]
    except:
        return jsonify({"status": "error", "message": "Товар не знайдено"}), 404

    admin_msg = (
        f"🔥 *НОВЕ ЗАМОВЛЕННЯ!*\n\n"
        f"🛍 *{product_name}*\n"
        f"📏 Розмір: {size}\n"
        f"💰 Ціна: {price} {CURRENCY}\n"
        f"💳 Оплата: {payment}\n\n"
        f"👤 *Клієнт:* {name}\n"
        f"📍 *Місто:* {city}\n"
        f"📦 *Адреса:* {address}\n"
        f"📞 *Телефон:* {phone}"
    )
    bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown")
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))