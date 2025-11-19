import os
from dotenv import load_dotenv

load_dotenv()

# ==================== BOT CONFIG ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
DB_PATH = "bot_database.db"

# ==================== CRYPTO BOT PAYMENT ====================
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
CRYPTO_BOT_USERNAME = os.getenv("CRYPTO_BOT_USERNAME", "CryptoBot")
REFERRAL_PERCENT = 50
MIN_WITHDRAWAL = 20.00

# ==================== SUBSCRIPTION PLANS ====================
SUBSCRIPTION_PLANS = {
    "1_month": {
        "name": "1 месяц",
        "days": 30,
        "price": 20.00,
        "price_usdt": 20.00,
        "discount": 0,
        "original_price": 20.00,
        "description": "Базовый доступ на 1 месяц"
    },
    "3_months": {
        "name": "3 месяца", 
        "days": 90,
        "price": 50.00,
        "price_usdt": 50.00,
        "discount": 17,
        "original_price": 60.00,
        "description": "Выгодный пакет на 3 месяца"
    },
    "12_months": {
        "name": "12 месяцев", 
        "days": 365,
        "price": 180.00,
        "price_usdt": 180.00,
        "discount": 25,
        "original_price": 240.00,
        "description": "Максимальная выгода на год"
    }
}

DEFAULT_PLAN = "1_month"

# ==================== TEXTS ====================
TEXTS = {
    "ru": {
        "payment_title": "💎 <b>Выбери тариф</b>",
        "payment_features": "✅ Торговые сигналы в реальном времени\n✅ Профессиональный анализ\n✅ Настройка алертов\n✅ Реферальная программа 50%",
        "btn_back": "🔙 Назад"
    },
    "en": {
        "payment_title": "💎 <b>Choose Plan</b>", 
        "payment_features": "✅ Real-time trading signals\n✅ Professional analysis\n✅ Alert settings\n✅ 50% referral program",
        "btn_back": "🔙 Back"
    }
}

def t(lang, key):
    return TEXTS.get(lang, TEXTS["ru"]).get(key, key)
