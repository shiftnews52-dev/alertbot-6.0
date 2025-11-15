"""
tasks.py - Фоновые задачи (ОБНОВЛЕННАЯ ВЕРСИЯ)
"""
import time
import asyncio
import logging
from collections import defaultdict
import httpx
from aiogram import Bot
from aiogram.utils.exceptions import RetryAfter, TelegramAPIError

from config import *
from database import *
from indicators import CANDLES, fetch_price, analyze_signal, fetch_candles_binance

logger = logging.getLogger(__name__)
LAST_SIGNALS = {}

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

async def price_collector(bot: Bot):
    """Сбор рыночных данных"""
    logger.info("🔄 CryptoMicky Price Collector started")
    
    while True:
        try:
            # Собираем данные для всех пар
            for pair in DEFAULT_PAIRS:
                for tf in TIMEFRAMES:
                    candles = await fetch_candles_binance(pair, tf, 100)
                    if candles:
                        for candle in candles:
                            CANDLES.add_candle(pair, tf, candle)
            
            logger.info(f"📊 Market data updated for {len(DEFAULT_PAIRS)} pairs")
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Price collector error: {e}")
            await asyncio.sleep(60)

async def signal_analyzer(bot: Bot):
    """Анализ и отправка сигналов ПО НОВОЙ ЛОГИКЕ"""
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
                # Проверка лимита сигналов
                signals_today = await count_signals_today(pair)
                if signals_today >= MAX_SIGNALS_PER_DAY:
                    continue
                
                # Ключ для cooldown
                key = pair  # Только пара, без стороны
                
                # Проверка cooldown
                if now - LAST_SIGNALS.get(key, 0) < 3600:  # 1 час
                    continue
                
                # АНАЛИЗ ПО НОВОЙ ЛОГИКЕ
                signal = analyze_signal(pair)
                if not signal:
                    continue
                
                # Формируем сообщение в новом формате
                side_emoji = "🟢" if signal['side'] == 'LONG' else "🔴"
                
                text = f"{side_emoji} <b>{pair} — {signal['side']}</b>\n\n"
                
                # Логика сигнала
                text += "<b>Логика:</b> "
                text += " ".join(signal['reasons']) + "\n\n"
                
                # Уровни входа
                entry_min, entry_max = signal['entry_zone']
                text += f"<b>Вход:</b> {entry_min:.2f} – {entry_max:.2f}\n"
                text += f"<b>Цели:</b> {signal['take_profit_1']:.2f} → {signal['take_profit_2']:.2f} → {signal['take_profit_3']:.2f}\n"
                text += f"<b>Стоп:</b> {signal['stop_loss']:.2f}\n\n"
                
                # Риск-менеджмент
                text += f"<b>Объём:</b> {signal['position_size']}\n"
                text += f"<b>Confidence:</b> {signal['confidence']}%\n\n"
                
                text += "⚠️ <i>Не финансовый совет</i>"
                
                # Отправка пользователям
                sent_count = 0
                for user_id in users:
                    if await send_message_safe(bot, user_id, text):
                        await log_signal(user_id, pair, signal['side'], signal['price'], signal['confidence'])
                        sent_count += 1
                    
                    await asyncio.sleep(0.05)
                
                LAST_SIGNALS[key] = now
                logger.info(f"🎯 CryptoMicky Signal: {pair} {signal['side']} to {sent_count} users")
                
        except Exception as e:
            logger.error(f"Signal analyzer error: {e}")
        
        await asyncio.sleep(60)
