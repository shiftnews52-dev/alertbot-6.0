"""
indicators.py - Новая логика анализа по ТЗ CryptoMicky (ПОЛНОСТЬЮ НОВЫЙ)
"""
import time
import logging
from typing import Optional, Dict, List, Tuple
from collections import defaultdict, deque
import httpx
import numpy as np

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

def calculate_macd(closes: List[float]) -> Optional[Tuple[float, float, float]]:
    """Расчёт MACD"""
    if len(closes) < MACD_SLOW:
        return None
    
    ema_fast = calculate_ema(closes, MACD_FAST)
    ema_slow = calculate_ema(closes, MACD_SLOW)
    
    if ema_fast is None or ema_slow is None:
        return None
    
    macd_line = ema_fast - ema_slow
    return macd_line, 0, 0  # Упрощённая версия

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
        if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, window+1)):
            resistance_levels.append(highs[i])
        
        if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, window+1)):
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
    Заменяет старую analyze_signal
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
    short_signal = _check_
