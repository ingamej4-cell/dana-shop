from flask import Flask, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEET_KEY, CURRENCY, ADMIN_CHAT_ID
import telebot
import os

app = Flask(__name__)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_path = '/etc/secrets/credentials.json' if os.path.exists('/etc/secrets/credentials.json') else 'credentials.json'
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client_gs = gspread.authorize(creds)
sheet = client_gs.open_by_key(GOOGLE_SHEET_KEY).get_worksheet(0)

BOT_TOKEN = "8761808805:AAGB2YrGSScbTra1j8BxvcmLyemojCuz354"
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/api/products')
def get_products():
    rows = sheet.get_all_values()[1:]
    products = []
    for row in rows:
        if len(row) >= 8 and row[7].lower() == "active":
            products.append({
                "id": row[0],
                "name": row[1],
                "price": int(row[2]),
                "sizes": row[3],
                "photo": row[4],
                "description": row[5],
                "category": row[6].strip()
            })
    return jsonify(products)

@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.json
    try:
        cell = sheet.find(data['product_id'], in_column=1)
        row = sheet.row_values(cell.row)
        admin_msg = f"🔥 *НОВЕ ЗАМОВЛЕННЯ*\n\n🛍️ {row[1]}\n💰 {row[2]} {CURRENCY}\n👤 {data['name']}\n📍 {data['city']}\n📦 {data['address']}\n📞 {data['phone']}"
        bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="Markdown")
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
