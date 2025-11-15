"""
config.py - Все настройки и константы бота (ОБНОВЛЕННЫЙ)
"""
import os

# ==================== BOT SETTINGS ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", "CryptoMicky Alerts")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/support")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB_PATH = os.getenv("DB_PATH", "bot.db")

# ==================== TRADING SETTINGS ====================
DEFAULT_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "TONUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]

# ==================== НОВЫЕ НАСТРОЙКИ CRYPTOMICKY ====================
TIMEFRAMES = ["1h", "4h"]
CANDLE_TF = 3600
CHECK_INTERVAL = 300

# Настройки сигналов
MIN_CONFIDENCE = 70
MIN_LEVEL_TOUCHES = 2
ENTRY_ZONE_PERCENT = 1.0
STOP_PERCENT = 1.5
MAX_SIGNALS_PER_DAY = 3

# Индикаторы
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ==================== СТАРЫЕ НАСТРОЙКИ (оставляем) ====================
# Таймфрейм (фиксированный)
TIMEFRAME = "1h"
MAX_CANDLES = 300

# Фильтры (упрощённые для новой логики)
MIN_SIGNAL_SCORE = 70
MIN_VOLUME_RATIO = 1.3
MIN_VOLATILITY = 0.003
MAX_SPREAD_PERCENT = 0.5

# Оптимизация
PRICE_CACHE_TTL = 30
BATCH_SEND_SIZE = 30
BATCH_SEND_DELAY = 0.05

# Картинки
IMG_START = os.getenv("IMG_START", "")
IMG_ALERTS = os.getenv("IMG_ALERTS", "")
IMG_REF = os.getenv("IMG_REF", "")
IMG_PAYWALL = os.getenv("IMG_PAYWALL", "")
IMG_GUIDE = os.getenv("IMG_GUIDE", "")

# ==================== TRANSLATIONS ====================
TEXTS = {
    "ru": {
        # Общие
        "welcome": "Выбери язык / Choose language",
        "main_menu": "Главное меню",
        "back": "⬅️ Назад",
        
        # Стартовое сообщение
        "start_text": f"<b>🚀 {BOT_NAME}</b>\n\n🎯 Профессиональные сигналы по уровням\n\n• Анализ поддержки/сопротивления\n• RSI + тренд + объёмы\n• 3 цели + стоп-лосс\n• Confidence score для каждого сигнала\n\n📖 Жми Инструкция для деталей",
        
        # Кнопки главного меню
        "btn_alerts": "📈 Алерты",
        "btn_ref": "👥 Рефералка",
        "btn_guide": "📖 Инструкция",
        "btn_support": "💬 Поддержка",
        "btn_unlock": "🔓 Открыть доступ",
        "btn_admin": "👑 Админ",
        "btn_back": "⬅️ Назад",
        "btn_stats": "📊 Статистика",
        
        # Алерты
        "alerts_title": "📈 <b>Управление алертами</b>\n\n⏰ Таймфрейм: 1 час + 4 часа\nВыбери монеты (до 10)\n\nАктивно: {count}/10",
        "add_custom_coin": "➕ Своя монета",
        "my_coins": "📋 Мои монеты",
        "how_it_works": "💡 Как это работает?",
        "access_required": "Оплатите доступ для использования алертов!",
        "coin_removed": "❌ {pair} удалён",
        "coin_added": "✅ {pair} добавлен",
        "max_coins": "Максимум 10 монет!",
        "no_active_coins": "Нет активных монет",
        "all_removed": "🗑 Всё удалено",
        "send_coin_symbol": "➕ Отправь символ монеты\nПример: <code>SOLUSDT</code>",
        "invalid_format": "❌ Неверный формат. Пример: SOLUSDT",
        "pair_not_found": "❌ Пара {pair} не найдена",
        
        # Инструкция
        "guide_title": "📖 <b>Инструкция</b>",
        "guide_step1": "<b>Шаг 1:</b> Оплати доступ",
        "guide_step2": "<b>Шаг 2:</b> Выбери монеты (до 10)",
        "guide_step3": "<b>Шаг 3:</b> Получай сигналы",
        "guide_signal_info": "<b>В каждом сигнале:</b>\n• Зона входа (диапазон цен)\n• 🎯 3 цели take profit\n• 🛡 Stop Loss\n• Причины входа\n• Confidence Score\n• Рекомендация по объёму\n\n<b>Особенности:</b>\n• Анализ по уровням поддержки/сопротивления\n• RSI + тренд + объёмы\n• Только качественные сетапы",
        "guide_disclaimer": "<b>⚠️ Важно:</b> Это не финансовый совет",
        
        # Оплата
        "payment_title": "🔓 <b>Открыть доступ</b>",
        "payment_features": "✅ Профессиональные сигналы по уровням\n✅ 3 цели + стоп-лосс\n✅ Анализ RSI + тренд\n✅ Confidence score\n✅ До 10 монет\n✅ Рефералка 50%",
        "pay_stars": "⭐ Оплата Stars",
        "pay_crypto": "💎 Крипто",
        "pay_code": "🎟 У меня код",
        "send_promo": "🎟 Отправь промокод одним сообщением",
        "access_granted": "✅ Доступ активирован!\n\nНажми /start",
        "in_development": "В разработке. Используйте промокод.",
        "crypto_payment_info": "💎 <b>Крипто-платёж</b>\n\nНапиши в поддержку для реквизитов.\n\n{support_url}",
        
        # Реферальная программа
        "ref_title": "👥 <b>Рефералка</b>\n\n50% от каждой подписки!\nВывод: крипта или Stars\nМинимум: $20",
        "ref_link": "🔗 <b>Твоя ссылка:</b>\n\n<code>{link}</code>\n\nДелись и зарабатывай 50%!",
        "ref_balance": "💰 <b>Баланс</b>\n\nДоступно: ${balance:.2f}\nРефералов: {refs}\n\nМинимум для вывода: $20",
        "ref_guide_text": "📖 <b>Гайд для партнёров</b>\n\n1. Получи свою ссылку\n2. Делись с друзьями\n3. Получай 50% с подписок\n4. Выводи от $20",
        "withdraw_crypto_format": "💎 <b>Вывод крипты</b>\n\nФормат:\n<code>/withdraw USDT TRC20 адрес сумма</code>",
        "withdraw_stars_format": "⭐ <b>Вывод Stars</b>\n\nФормат:\n<code>/withdraw_stars сумма</code>",
        "withdraw_invalid_format": "❌ Формат: /withdraw USDT TRC20 адрес сумма",
        "withdraw_invalid_amount": "❌ Сумма должна быть числом",
        "withdraw_min_amount": "❌ Минимум $20",
        "withdraw_accepted": "✅ Заявка принята: {amount} {currency}\n\nОжидайте обработки (до 24ч)",
        
        # Статистика
        "stats_title": "📊 <b>Твоя статистика</b>",
        "stats_signals": "📈 Получено сигналов: {count}",
        "stats_today": "📅 Сегодня: {count}",
        "stats_accuracy": "🎯 Точность: скоро...",
        "stats_best_pair": "🏆 Лучшая пара: {pair}",
        
        # Админ панель
        "admin_title": "👑 <b>Админ-панель</b>",
        "admin_stats": "📊 <b>Статистика</b>\n\n👥 Всего: {total}\n💎 Оплативших: {paid}\n📈 Активных: {active}\n🔔 Сигналов сегодня: {signals_today}",
        "admin_send_broadcast": "📢 Отправь текст рассылки",
        "admin_send_user_id": "✅ Отправь ID пользователя",
        "admin_send_amount": "Отправь сумму",
        "admin_invalid_id": "❌ ID должен быть числом",
        "admin_access_granted": "✅ Доступ выдан: {uid}",
        "admin_balance_added": "✅ Начислено ${amount:.2f} → {uid}",
        "admin_broadcast_done": "✅ Разослано: {sent}/{total}",
        "admin_no_access": "❌ Нет доступа",
        
        # Язык
        "language_select": "🌐 <b>Выбери язык</b>",
        "language_changed": "✅ Язык изменён на Русский",
    },
    "en": {
        # General
        "welcome": "Выбери язык / Choose language",
        "main_menu": "Main Menu",
        "back": "⬅️ Back",
        
        # Start message
        "start_text": f"<b>🚀 {BOT_NAME}</b>\n\n🎯 Professional level-based signals\n\n• Support/resistance analysis\n• RSI + trend + volume\n• 3 targets + stop loss\n• Confidence score for each signal\n\n📖 Press Guide for details",
        
        # Main menu buttons
        "btn_alerts": "📈 Alerts",
        "btn_ref": "👥 Referrals",
        "btn_guide": "📖 Guide",
        "btn_support": "💬 Support",
        "btn_unlock": "🔓 Unlock Access",
        "btn_admin": "👑 Admin",
        "btn_back": "⬅️ Back",
        "btn_stats": "📊 Statistics",
        
        # Alerts
        "alerts_title": "📈 <b>Manage Alerts</b>\n\n⏰ Timeframe: 1h + 4h\nSelect coins (up to 10)\n\nActive: {count}/10",
        "add_custom_coin": "➕ Custom coin",
        "my_coins": "📋 My coins",
        "how_it_works": "💡 How it works?",
        "access_required": "Please pay for access to use alerts!",
        "coin_removed": "❌ {pair} removed",
        "coin_added": "✅ {pair} added",
        "max_coins": "Maximum 10 coins!",
        "no_active_coins": "No active coins",
        "all_removed": "🗑 All removed",
        "send_coin_symbol": "➕ Send coin symbol\nExample: <code>SOLUSDT</code>",
        "invalid_format": "❌ Invalid format. Example: SOLUSDT",
        "pair_not_found": "❌ Pair {pair} not found",
        
        # Guide
        "guide_title": "📖 <b>Guide</b>",
        "guide_step1": "<b>Step 1:</b> Pay for access",
        "guide_step2": "<b>Step 2:</b> Select coins (up to 10)",
        "guide_step3": "<b>Step 3:</b> Receive signals",
        "guide_signal_info": "<b>Each signal includes:</b>\n• Entry zone (price range)\n• 🎯 3 take profit targets\n• 🛡 Stop Loss\n• Entry reasons\n• Confidence Score\n• Volume recommendation\n\n<b>Features:</b>\n• Support/resistance level analysis\n• RSI + trend + volume\n• Quality setups only",
        "guide_disclaimer": "<b>⚠️ Important:</b> This is not financial advice",
        
        # Payment
        "payment_title": "🔓 <b>Unlock Access</b>",
        "payment_features": "✅ Professional level-based signals\n✅ 3 targets + stop loss\n✅ RSI + trend analysis\n✅ Confidence score\n✅ Up to 10 coins\n✅ 50% referral program",
        "pay_stars": "⭐ Pay with Stars",
        "pay_crypto": "💎 Crypto",
        "pay_code": "🎟 I have a code",
        "send_promo": "🎟 Send promo code in one message",
        "access_granted": "✅ Access activated!\n\nPress /start",
        "in_development": "In development. Use promo code.",
        "crypto_payment_info": "💎 <b>Crypto Payment</b>\n\nContact support for payment details.\n\n{support_url}",
        
        # Referral program
        "ref_title": "👥 <b>Referral Program</b>\n\n50% from each subscription!\nWithdrawal: crypto or Stars\nMinimum: $20",
        "ref_link": "🔗 <b>Your link:</b>\n\n<code>{link}</code>\n\nShare and earn 50%!",
        "ref_balance": "💰 <b>Balance</b>\n\nAvailable: ${balance:.2f}\nReferrals: {refs}\n\nMinimum withdrawal: $20",
        "ref_guide_text": "📖 <b>Partner Guide</b>\n\n1. Get your link\n2. Share with friends\n3. Earn 50% from subscriptions\n4. Withdraw from $20",
        "withdraw_crypto_format": "💎 <b>Crypto Withdrawal</b>\n\nFormat:\n<code>/withdraw USDT TRC20 address amount</code>",
        "withdraw_stars_format": "⭐ <b>Stars Withdrawal</b>\n\nFormat:\n<code>/withdraw_stars amount</code>",
        "withdraw_invalid_format": "❌ Format: /withdraw USDT TRC20 address amount",
        "withdraw_invalid_amount": "❌ Amount must be a number",
        "withdraw_min_amount": "❌ Minimum $20",
        "withdraw_accepted": "✅ Request accepted: {amount} {currency}\n\nProcessing (up to 24h)",
        
        # Statistics
        "stats_title": "📊 <b>Your Statistics</b>",
        "stats_signals": "📈 Signals received: {count}",
        "stats_today": "📅 Today: {count}",
        "stats_accuracy": "🎯 Accuracy: coming soon...",
        "stats_best_pair": "🏆 Best pair: {pair}",
        
        # Admin panel
        "admin_title": "👑 <b>Admin Panel</b>",
        "admin_stats": "📊 <b>Statistics</b>\n\n👥 Total: {total}\n💎 Paid: {paid}\n📈 Active: {active}\n🔔 Signals today: {signals_today}",
        "admin_send_broadcast": "📢 Send broadcast message",
        "admin_send_user_id": "✅ Send user ID",
        "admin_send_amount": "Send amount",
        "admin_invalid_id": "❌ ID must be a number",
        "admin_access_granted": "✅ Access granted: {uid}",
        "admin_balance_added": "✅ Added ${amount:.2f} → {uid}",
        "admin_broadcast_done": "✅ Sent: {sent}/{total}",
        "admin_no_access": "❌ No access",
        
        # Language
        "language_select": "🌐 <b>Choose Language</b>",
        "language_changed": "✅ Language changed to English",
    }
}

def t(uid_or_lang, key: str, **kwargs) -> str:
    """Получить перевод с поддержкой форматирования"""
    if isinstance(uid_or_lang, str):
        lang = uid_or_lang
    else:
        lang = "ru"
    
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text

print("=" * 60)
print("🎯 CRYPTOMICKY ALERTS BOT - READY!")
print("=" * 60)
print(f"⏰ Таймфреймы: {TIMEFRAMES}")
print(f"📊 Пары: {len(DEFAULT_PAIRS)}")
print(f"🎯 Min Confidence: {MIN_CONFIDENCE}%")
print("=" * 60)
