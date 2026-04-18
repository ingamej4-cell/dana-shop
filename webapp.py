from flask import Flask, render_template, jsonify, request, send_from_directory
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEET_KEY, CURRENCY, ADMIN_CHAT_ID
import telebot
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ==== Правильний шлях до credentials.json (Render / локально) ====
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# На Render секретний файл монтується в /etc/secrets/
creds_path = '/etc/secrets/credentials.json'
if not os.path.exists(creds_path):
    creds_path = 'credentials.json'  # локально

creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_KEY).get_worksheet(0)

# Тимчасово для сповіщень (бот)
BOT_TOKEN = "8761808805:AAGB2YrGSScbTra1j8BxvcmLyemojCuz354"
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

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
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
