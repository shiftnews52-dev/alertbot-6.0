"""
indicators.py - Новая логика анализа по ТЗ CryptoMicky (БЕЗ numpy)
"""
import time
import logging
import math
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
import httpx

from config import *

logger = logging.getLogger(__name__)

# ==================== CANDLE STORAGE ====================
class CandleStorage:
    def __init__(self):
        self.candles: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    
    def add_candle(self, pair: str, tf: str, candle: dict):
        self.candles[pair][tf].append(candle)
        if len(self.candles[pair][tf]) > 500:
            self.candles[pair][tf] = self.candles[pair][tf][-500:]
    
    def get_candles(self, pair: str, tf: str) -> List[dict]:
        return self.candles[pair].get(tf, [])

CANDLES = CandleStorage()

# ==================== PRICE CACHE ====================
class PriceCache:
    def __init__(self, ttl: int = 30):
        self.cache: Dict[str, Tuple[float, float, float]] = {}
        self.ttl = ttl
    
    def get(self, pair: str) -> Optional[Tuple[float, float]]:
        if pair in self.cache:
            price, volume, cached_at = self.cache[pair]
            if time.time() - cached_at < self.ttl:
                return price, volume
        return None
    
    def set(self, pair: str, price: float, volume: float):
        self.cache[pair] = (price, volume, time.time())
    
    def clear_old(self):
        now = time.time()
        self.cache = {k: v for k, v in self.cache.items() if now - v[2] < self.ttl}

PRICE_CACHE = PriceCache()

# ==================== API FUNCTIONS ====================
async def fetch_price(client: httpx.AsyncClient, pair: str) -> Optional[Tuple[float, float]]:
    """Получить цену с Binance"""
    cached = PRICE_CACHE.get(pair)
    if cached:
        return cached
    
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair.upper()}"
        resp = await client.get(url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        price = float(data["lastPrice"])
        volume = float(data["volume"])
        
        PRICE_CACHE.set(pair, price, volume)
        return price, volume
    except Exception as e:
        logger.error(f"Error fetching {pair}: {e}")
        return None

async def fetch_candles_binance(pair: str, tf: str, limit: int = 100):
    """Получение свечей с Binance"""
    try:
        async with httpx.AsyncClient() as client:
            tf_map = {"1h": "1h", "4h": "4h"}
            interval = tf_map.get(tf, "1h")
            
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                "symbol": pair,
                "interval": interval,
                "limit": limit
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            klines = response.json()
            candles = []
            
            for kline in klines:
                candle = {
                    't': kline[0] / 1000,
                    'o': float(kline[1]),
                    'h': float(kline[2]),
                    'l': float(kline[3]),
                    'c': float(kline[4]),
                    'v': float(kline[5])
                }
                candles.append(candle)
            
            return candles
            
    except Exception as e:
        logger.error(f"Error fetching candles {pair} {tf}: {e}")
        return None

# ==================== ИНДИКАТОРЫ ====================
def calculate_rsi(closes: List[float], period: int = RSI_PERIOD) -> Optional[float]:
    """Расчёт RSI"""
    if len(closes) < period + 1:
        return None
    
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(values: List[float], period: int) -> Optional[float]:
    """Exponential Moving Average"""
    if len(values) < period:
        return None
    
    k = 2 / (period + 1)
    ema = values[0]
    for value in values[1:]:
        ema = value * k + ema * (1 - k)
    return ema

# ==================== ЛОГИКА АНАЛИЗА ====================
def determine_trend(closes: List[float]) -> str:
    """Определение тренда по ТЗ"""
    if len(closes) < 20:
        return 'neutral'
    
    recent_closes = closes[-10:]
    higher_highs = sum(1 for i in range(1, len(recent_closes)) 
                      if recent_closes[i] > recent_closes[i-1])
    lower_lows = sum(1 for i in range(1, len(recent_closes)) 
                   if recent_closes[i] < recent_closes[i-1])
    
    rsi = calculate_rsi(closes)
    if rsi is None:
        return 'neutral'
    
    bull_conditions = 0
    if higher_highs > lower_lows:
        bull_conditions += 1
    if rsi > 50:
        bull_conditions += 1
    
    bear_conditions = 0
    if lower_lows > higher_highs:
        bear_conditions += 1
    if rsi < 50:
        bear_conditions += 1
    
    if bull_conditions >= 2:
        return 'bullish'
    elif bear_conditions >= 2:
        return 'bearish'
    else:
        return 'neutral'

def find_support_resistance_levels(candles: List[dict], window: int = 5) -> Tuple[List[float], List[float]]:
    """Поиск уровней поддержки и сопротивления"""
    if len(candles) < window * 2:
        return [], []
    
    highs = [c['h'] for c in candles]
    lows = [c['l'] for c in candles]
    
    resistance_levels = []
    support_levels = []
    
    for i in range(window, len(candles) - window):
        # Проверка сопротивления (локальный максимум)
        is_resistance = True
        for j in range(1, window + 1):
            if highs[i] < highs[i - j] or highs[i] < highs[i + j]:
                is_resistance = False
                break
        if is_resistance:
            resistance_levels.append(highs[i])
        
        # Проверка поддержки (локальный минимум)
        is_support = True
        for j in range(1, window + 1):
            if lows[i] > lows[i - j] or lows[i] > lows[i + j]:
                is_support = False
                break
        if is_support:
            support_levels.append(lows[i])
    
    resistance_levels = _group_levels(resistance_levels)
    support_levels = _group_levels(support_levels)
    
    return support_levels, resistance_levels

def _group_levels(levels: List[float], tolerance: float = 0.02) -> List[float]:
    """Группировка близких уровней"""
    if not levels:
        return []
    
    levels.sort()
    grouped = []
    current_group = [levels[0]]
    
    for level in levels[1:]:
        if abs(level - current_group[0]) / current_group[0] <= tolerance:
            current_group.append(level)
        else:
            grouped.append(sum(current_group) / len(current_group))
            current_group = [level]
    
    if current_group:
        grouped.append(sum(current_group) / len(current_group))
    
    return grouped

def analyze_signal(pair: str) -> Optional[Dict]:
    """
    ГЛАВНАЯ ФУНКЦИЯ - анализ сигнала по ТЗ CryptoMicky
    """
    candles_1h = CANDLES.get_candles(pair, "1h")
    if len(candles_1h) < 50:
        return None
    
    closes = [c['c'] for c in candles_1h]
    current_price = closes[-1]
    
    # Индикаторы
    rsi = calculate_rsi(closes)
    trend = determine_trend(closes)
    supports, resistances = find_support_resistance_levels(candles_1h)
    
    if rsi is None:
        return None
    
    # Проверяем LONG условия
    long_signal = _check_long_conditions(current_price, trend, rsi, supports, candles_1h)
    if long_signal:
        long_signal['pair'] = pair
        return long_signal
    
    # Проверяем SHORT условия  
    short_signal = _check_short_conditions(current_price, trend, rsi, resistances, candles_1h)
    if short_signal:
        short_signal['pair'] = pair
        return short_signal
    
    return None

def _check_long_conditions(price: float, trend: str, rsi: float, 
                          supports: List[float], candles: List[dict]) -> Optional[Dict]:
    """Проверка условий для LONG"""
    nearest_support = None
    for support in supports:
        if support < price and (nearest_support is None or support > nearest_support):
            if abs(price - support) / price <= 0.03:
                nearest_support = support
    
    if not nearest_support:
        return None
    
    confidence = 0
    reasons = []
    
    # Условие 1: Цена у поддержки
    if abs(price - nearest_support) / price <= 0.015:
        confidence += 25
        reasons.append("🎯 Цена у проверенной поддержки")
    
    # Условие 2: RSI в зоне выкупа
    if 30 <= rsi <= 45:
        confidence += 25
        reasons.append(f"📊 RSI в зоне выкупа ({rsi:.1f})")
    
    # Условие 3: Бычий тренд
    if trend == 'bullish':
        confidence += 20
        reasons.append("🟢 Бычий тренд")
    
    # Условие 4: Объёмы подтверждают
    if _check_volume_confirmation(candles, 'long'):
        confidence += 20
        reasons.append("📈 Объёмы подтверждают разворот")
    
    # Бонус за сильный сетап
    if confidence >= 70:
        confidence = min(95, confidence + 10)
        reasons.append("⚡ Сильный сетап")
    
    if confidence >= MIN_CONFIDENCE:
        return _calculate_long_signal(price, nearest_support, confidence, reasons)
    
    return None

def _check_short_conditions(price: float, trend: str, rsi: float,
                           resistances: List[float], candles: List[dict]) -> Optional[Dict]:
    """Проверка условий для SHORT"""
    nearest_resistance = None
    for resistance in resistances:
        if resistance > price and (nearest_resistance is None or resistance < nearest_resistance):
            if abs(price - resistance) / price <= 0.03:
                nearest_resistance = resistance
    
    if not nearest_resistance:
        return None
    
    confidence = 0
    reasons = []
    
    # Условие 1: Цена у сопротивления
    if abs(price - nearest_resistance) / price <= 0.015:
        confidence += 25
        reasons.append("🎯 Цена у проверенного сопротивления")
    
    # Условие 2: RSI в зоне продаж
    if 55 <= rsi <= 70:
        confidence += 25
        reasons.append(f"📊 RSI в зоне продаж ({rsi:.1f})")
    
    # Условие 3: Медвежий тренд
    if trend == 'bearish':
        confidence += 20
        reasons.append("🔴 Медвежий тренд")
    
    # Условие 4: Объёмы подтверждают
    if _check_volume_confirmation(candles, 'short'):
        confidence += 20
        reasons.append("📉 Объёмы подтверждают разворот")
    
    if confidence >= 70:
        confidence = min(95, confidence + 10)
        reasons.append("⚡ Сильный сетап")
    
    if confidence >= MIN_CONFIDENCE:
        return _calculate_short_signal(price, nearest_resistance, confidence, reasons)
    
    return None

def _check_volume_confirmation(candles: List[dict], side: str) -> bool:
    """Проверка подтверждения объёмами"""
    if len(candles) < 10:
        return False
    
    recent_volumes = [c['v'] for c in candles[-5:]]
    prev_volumes = [c['v'] for c in candles[-10:-5]]
    
    if not recent_volumes or not prev_volumes:
        return False
    
    avg_recent = sum(recent_volumes) / len(recent_volumes)
    avg_prev = sum(prev_volumes) / len(prev_volumes)
    
    return avg_recent > avg_prev * 0.8

def _calculate_long_signal(price: float, support: float, confidence: int, reasons: List[str]) -> Dict:
    """Расчёт сигнала LONG"""
    entry_min = support * (1 - ENTRY_ZONE_PERCENT / 100)
    entry_max = support * (1 + ENTRY_ZONE_PERCENT / 100)
    stop_loss = support * (1 - STOP_PERCENT / 100)
    
    # 3 цели как в ТЗ
    take_profits = [
        price * 1.02,  # TP1
        price * 1.04,  # TP2  
        price * 1.06   # TP3
    ]
    
    position_size = _calculate_position_size(confidence)
    
    return {
        'side': 'LONG',
        'price': price,
        'entry_zone': (entry_min, entry_max),
        'stop_loss': stop_loss,
        'take_profit_1': take_profits[0],
        'take_profit_2': take_profits[1],
        'take_profit_3': take_profits[2],
        'score': confidence,  # Для совместимости
        'confidence': confidence,
        'reasons': reasons,
        'position_size': position_size,
        'sl_percent': abs((stop_loss - price) / price * 100),
        'tp1_percent': abs((take_profits[0] - price) / price * 100),
        'tp2_percent': abs((take_profits[1] - price) / price * 100),
        'tp3_percent': abs((take_profits[2] - price) / price * 100)
    }

def _calculate_short_signal(price: float, resistance: float, confidence: int, reasons: List[str]) -> Dict:
    """Расчёт сигнала SHORT"""
    entry_min = resistance * (1 - ENTRY_ZONE_PERCENT / 100)
    entry_max = resistance * (1 + ENTRY_ZONE_PERCENT / 100)
    stop_loss = resistance * (1 + STOP_PERCENT / 100)
    
    take_profits = [
        price * 0.98,  # TP1
        price * 0.96,  # TP2
        price * 0.94   # TP3
    ]
    
    position_size = _calculate_position_size(confidence)
    
    return {
        'side': 'SHORT',
        'price': price,
        'entry_zone': (entry_min, entry_max),
        'stop_loss': stop_loss,
        'take_profit_1': take_profits[0],
        'take_profit_2': take_profits[1],
        'take_profit_3': take_profits[2],
        'score': confidence,
        'confidence': confidence,
        'reasons': reasons,
        'position_size': position_size,
        'sl_percent': abs((stop_loss - price) / price * 100),
        'tp1_percent': abs((take_profits[0] - price) / price * 100),
        'tp2_percent': abs((take_profits[1] - price) / price * 100),
        'tp3_percent': abs((take_profits[2] - price) / price * 100)
    }

def _calculate_position_size(confidence: int) -> str:
    """Расчёт размера позиции по confidence"""
    if confidence >= 85:
        return "15-20% депо"
    elif confidence >= 75:
        return "10-12% депо"
    elif confidence >= 70:
        return "5-8% депо"
    else:
        return "3-5% депо"

# ==================== СОВМЕСТИМОСТЬ СО СТАРОЙ ЛОГИКОЙ ====================
def quick_screen(pair: str) -> bool:
    """Быстрый скрининг - для совместимости"""
    candles = CANDLES.get_candles(pair, "1h")
    return len(candles) >= 50
