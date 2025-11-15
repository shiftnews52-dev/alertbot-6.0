"""
tasks.py - Фоновые задачи (ПОЛНОСТЬЮ ОБНОВЛЕННЫЙ)
"""
import time
import asyncio
import logging
from collections import defaultdict
import httpx
from aiogram import Bot
from aiogram.utils.exceptions import RetryAfter, TelegramAPIError

from config import (
    CHECK_INTERVAL, DEFAULT_PAIRS, TIMEFRAMES,
    MAX_SIGNALS_PER_DAY, BATCH_SEND_SIZE, BATCH_SEND_DELAY
)
from database import (
    get_all_tracked_pairs, get_pairs_with_users,
    count_signals_today, log_signal
)
from indicators import (
    CANDLES, PRICE_CACHE, fetch_price, 
    analyze_signal, fetch_candles_binance
)

logger = logging.getLogger(__name__)

# Глобальный словарь для cooldown сигналов
LAST_SIGNALS = {}

# ==================== HELPER FUNCTIONS ====================
async def send_message_safe(bot: Bot, user_id: int, text: str, **kwargs):
    """Безопасная отправка с обработкой rate limit"""
    try:
        await bot.send_message(user_id, text, **kwargs)
        return True
    except RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return await send_message_safe(bot, user_id, text, **kwargs)
    except TelegramAPIError:
        return False

# ==================== TASKS ====================
async def price_collector(bot: Bot):
    """Сбор рыночных данных для CryptoMicky"""
    logger.info("🔄 CryptoMicky Price Collector started")
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Собираем цены для всех пар
                pairs = await get_all_tracked_pairs()
                pairs = list(set(pairs + DEFAULT_PAIRS))
                
                ts = time.time()
                for pair in pairs:
                    price_data = await fetch_price(client, pair)
                    if price_data:
                        price, volume = price_data
                        # Добавляем в 1H свечи (для совместимости)
                        CANDLES.add_candle(pair, "1h", {
                            't': ts, 'o': price, 'h': price, 
                            'l': price, 'c': price, 'v': volume
                        })
                
                # Собираем исторические данные для анализа
                for pair in DEFAULT_PAIRS:
                    for tf in TIMEFRAMES:
                        candles = await fetch_candles_binance(pair, tf, 100)
                        if candles:
                            for candle in candles:
                                CANDLES.add_candle(pair, tf, candle)
                            logger.debug(f"Updated {pair} {tf}: {len(candles)} candles")
                
                # Очистка старого кэша
                PRICE_CACHE.clear_old()
                
                logger.info(f"📊 Market data updated for {len(pairs)} pairs")
                
            except Exception as e:
                logger.error(f"Price collector error: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)

async def signal_analyzer(bot: Bot):
    """Анализ и отправка сигналов по новой логике CryptoMicky"""
    logger.info("🎯 CryptoMicky Signal Analyzer started")
    
    while True:
        try:
            # Получаем пары и пользователей
            rows = await get_pairs_with_users()
            
            # Группируем по парам
            pairs_users = defaultdict(list)
            for row in rows:
                pairs_users[row["pair"]].append(row["user_id"])
            
            # Анализируем каждую пару
            now = time.time()
            for pair, users in pairs_users.items():
                # Проверка лимита сигналов за день
                signals_today = await count_signals_today(pair)
                if signals_today >= MAX_SIGNALS_PER_DAY:
                    continue
                
                # Ключ для cooldown (только пара)
                key = pair
                
                # Проверка cooldown (1 сигнал в час на пару)
                if now - LAST_SIGNALS.get(key, 0) < 3600:
                    continue
                
                # АНАЛИЗ ПО НОВОЙ ЛОГИКЕ CRYPTOMICKY
                signal = analyze_signal(pair)
                if not signal:
                    continue
                
                # Формируем сообщение в новом формате
                side_emoji = "🟢" if signal['side'] == 'LONG' else "🔴"
                
                text = f"{side_emoji} <b>{signal['pair']} — {signal['side']}</b>\n\n"
                
                # Логика сигнала
                text += "<b>Логика:</b>\n"
                for reason in signal['reasons']:
                    text += f"• {reason}\n"
                text += "\n"
                
                # Уровни входа
                entry_min, entry_max = signal['entry_zone']
                text += f"🎯 <b>Вход:</b> {entry_min:.2f} – {entry_max:.2f}\n"
                text += f"🎯 <b>Цели:</b>\n"
                text += f"   TP1: {signal['take_profit_1']:.2f} (+{signal['tp1_percent']:.2f}%)\n"
                text += f"   TP2: {signal['take_profit_2']:.2f} (+{signal['tp2_percent']:.2f}%)\n"
                text += f"   TP3: {signal['take_profit_3']:.2f} (+{signal['tp3_percent']:.2f}%)\n"
                text += f"🛡 <b>Стоп:</b> {signal['stop_loss']:.2f} (-{signal['sl_percent']:.2f}%)\n\n"
                
                # Риск-менеджмент
                text += f"💰 <b>Объём позиции:</b> {signal['position_size']}\n"
                text += f"📊 <b>Confidence Score:</b> {signal['confidence']}%\n\n"
                
                text += "⏰ " + time.strftime('%H:%M:%S') + "\n"
                text += "⚠️ <i>Не финансовый совет</i>"
                
                # Батчинг отправки
                sent_count = 0
                for i, user_id in enumerate(users):
                    if await send_message_safe(bot, user_id, text):
                        await log_signal(user_id, pair, signal['side'], signal['price'], signal['confidence'])
                        sent_count += 1
                    
                    if (i + 1) % BATCH_SEND_SIZE == 0:
                        await asyncio.sleep(1)
                    else:
                        await asyncio.sleep(BATCH_SEND_DELAY)
                
                LAST_SIGNALS[key] = now
                logger.info(f"🎯 CryptoMicky Signal: {pair} {signal['side']} to {sent_count} users (Confidence: {signal['confidence']}%)")
                
        except Exception as e:
            logger.error(f"Signal analyzer error: {e}")
        
        await asyncio.sleep(60)  # Проверяем каждую минуту

# ==================== СОВМЕСТИМОСТЬ СО СТАРОЙ ЛОГИКОЙ ====================
async def collect_market_data_legacy():
    """Совместимость со старой логикой"""
    pass

async def analyze_signals_legacy():
    """Совместимость со старой логикой"""
    pass
