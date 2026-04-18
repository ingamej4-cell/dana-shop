import google.generativeai as genai
from config import GEMINI_API_KEY, MARKUP_COEFFICIENT, CURRENCY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


def analyze_product(text: str, cost_price: float) -> dict:
    retail_price = int(cost_price * MARKUP_COEFFICIENT)
    prompt = f"""Ти — професійний копірайтер для Instagram/Telegram магазину одягу DANA.
    На основі тексту постачальника створи ПРОДАВАЛЬНИЙ опис товару українською мовою.

    Вимоги:
    - 3-4 речення максимум
    - Емодзі
    - Виділи переваги
    - Згадай якість, стиль, універсальність

    Текст постачальника: {text}
    Роздрібна ціна: {retail_price} {CURRENCY}

    Формат відповіді:
    НАЗВА: [коротка назва товару]
    ОПИС: [продавальний опис]
    """
    response = model.generate_content(prompt)
    result = response.text
    name = ""
    description = ""
    for line in result.split('\n'):
        if line.startswith('НАЗВА:'):
            name = line.replace('НАЗВА:', '').strip()
        elif line.startswith('ОПИС:'):
            description = line.replace('ОПИС:', '').strip()
    return {
        "name": name or text[:50],
        "description": description or text,
        "price": retail_price,
        "original_text": text
    }


def extract_price_from_text(text: str) -> float | None:
    import re
    match = re.search(r'(\d+(?:\.\d+)?)', text.replace(',', '.'))
    return float(match.group(1)) if match else None