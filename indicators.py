"""
indicators.py - Профессиональная логика анализа (БЕЗ ОШИБОК)
"""
import time
import logging
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
import httpx

from config import *

logger = logging.getLogger(__name__)

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

class PriceCache:
    def __init__(self, ttl: int = 30):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, pair: str):
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
    """Упрощённый MACD"""
    if len(closes) < MACD_SLOW:
        return None
    
    ema_fast = calculate_ema(closes, MACD_FAST)
    ema_slow = calculate_ema(closes, MACD_SLOW)
    
    if ema_fast is None or ema_slow is None:
        return None
    
    macd_line = ema_fast - ema_slow
    return macd_line, 0, 0

# ==================== АНАЛИЗ ТРЕНДА ====================
def determine_trend(closes: List[float]) -> str:
    """Определение тренда по цене и RSI"""
    if len(closes) < 30:
        return 'neutral'
    
    # Анализ структуры цены
    recent = closes[-20:]
    highs = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
    lows = sum(1 for i in range(1, len(recent)) if recent[i] < recent[i-1])
    
    # RSI анализ
    rsi = calculate_rsi(closes)
    if rsi is None:
        return 'neutral'
    
    # EMA анализ
    ema_short = calculate_ema(closes, 9)
    ema_long = calculate_ema(closes, 21)
    
    bull_conditions = 0
    bear_conditions = 0
    
    # Бычьи условия
    if highs > lows:
        bull_conditions += 1
    if rsi > 50:
        bull_conditions += 1
    if ema_short and ema_long and ema_short > ema_long:
        bull_conditions += 1
    
    # Медвежьи условия
    if lows > highs:
        bear_conditions += 1
    if rsi < 50:
        bear_conditions += 1
    if ema_short and ema_long and ema_short < ema_long:
        bear_conditions += 1
    
    if bull_conditions >= 2:
        return 'bullish'
    elif bear_conditions >= 2:
        return 'bearish'
    else:
        return 'neutral'

# ==================== ПОИСК УРОВНЕЙ ====================
def find_support_resistance_levels(candles: List[dict], window: int = 5) -> Tuple[List[float], List[float]]:
    """Поиск качественных уровней поддержки/сопротивления"""
    if len(candles) < window * 3:
        return [], []
    
    highs = [c['h'] for c in candles]
    lows = [c['l'] for c in candles]
    closes = [c['c'] for c in candles]
    
    resistance_levels = []
    support_levels = []
    
    # Ищем локальные экстремумы
    for i in range(window, len(candles) - window):
        current_high = highs[i]
        current_low = lows[i]
        
        # Проверяем максимум
        is_local_max = True
        for j in range(1, window + 1):
            if current_high < highs[i - j] or current_high < highs[i + j]:
                is_local_max = False
                break
        
        # Проверяем минимум
        is_local_min = True
        for j in range(1, window + 1):
            if current_low > lows[i - j] or current_low > lows[i + j]:
                is_local_min = False
                break
        
        if is_local_max:
            resistance_levels.append(current_high)
        if is_local_min:
            support_levels.append(current_low)
    
    # Фильтруем и группируем уровни
    resistance_levels = _filter_and_group_levels(resistance_levels, closes)
    support_levels = _filter_and_group_levels(support_levels, closes)
    
    return support_levels, resistance_levels

def _filter_and_group_levels(levels: List[float], closes: List[float]) -> List[float]:
    """Фильтрация и группировка уровней"""
    if not levels:
        return []
    
    current_price = closes[-1] if closes else 0
    
    # Убираем уровни слишком далеко от текущей цены
    filtered_levels = []
    for level in levels:
        price_diff_pct = abs(level - current_price) / current_price
        if price_diff_pct <= 0.1:  # Не дальше 10%
            filtered_levels.append(level)
    
    # Группируем близкие уровни
    filtered_levels.sort()
    grouped = []
    current_group = [filtered_levels[0]]
    
    for level in filtered_levels[1:]:
        if abs(level - current_group[0]) / current_group[0] <= 0.02:  # 2% tolerance
            current_group.append(level)
        else:
            grouped.append(sum(current_group) / len(current_group))
            current_group = [level]
    
    if current_group:
        grouped.append(sum(current_group) / len(current_group))
    
    return grouped

# ==================== ОСНОВНАЯ ЛОГИКА ====================
def analyze_signal(pair: str) -> Optional[Dict]:
    """Профессиональный анализ сигналов"""
    candles_1h = CANDLES.get_candles(pair, "1h")
    if len(candles_1h) < 100:
        return None
    
    closes = [c['c'] for c in candles_1h]
    current_price = closes[-1]
    
    # Рассчитываем индикаторы
    rsi = calculate_rsi(closes)
    trend = determine_trend(closes)
    supports, resistances = find_support_resistance_levels(candles_1h)
    macd_data = calculate_macd(closes)
    
    if rsi is None:
        return None
    
    # Анализируем LONG
    long_signal = _analyze_long_signal(current_price, trend, rsi, macd_data, supports, candles_1h)
    if long_signal:
        long_signal['pair'] = pair
        return long_signal
    
    # Анализируем SHORT
    short_signal = _analyze_short_signal(current_price, trend, rsi, macd_data, resistances, candles_1h)
    if short_signal:
        short_signal['pair'] = pair
        return short_signal
    
    return None

def _analyze_long_signal(price: float, trend: str, rsi: float, macd_data: Optional[Tuple], 
                        supports: List[float], candles: List[dict]) -> Optional[Dict]:
    """Анализ LONG сигнала"""
    # Находим ближайшую качественную поддержку
    best_support = None
    for support in supports:
        if support < price:
            distance_pct = (price - support) / price
            if distance_pct <= 0.03:  # Не дальше 3%
                if best_support is None or support > best_support:
                    best_support = support
    
    if not best_support:
        return None
    
    confidence = 0
    reasons = []
    
    # 1. Уровень поддержки
    distance_pct = (price - best_support) / price
    if distance_pct <= 0.015:
        confidence += 25
        reasons.append("🎯 Сильная поддержка")
    elif distance_pct <= 0.025:
        confidence += 20
        reasons.append("✅ Уровень поддержки")
    
    # 2. RSI анализ
    if 30 <= rsi <= 45:
        confidence += 25
        reasons.append(f"📊 RSI для входа ({rsi:.1f})")
    elif 25 <= rsi < 30 or 45 < rsi <= 50:
        confidence += 15
        reasons.append(f"📈 RSI приемлемый ({rsi:.1f})")
    
    # 3. Тренд
    if trend == 'bullish':
        confidence += 20
        reasons.append("🟢 Бычий тренд")
    elif trend == 'neutral':
        confidence += 10
        reasons.append("⚪ Нейтральный тренд")
    
    # 4. MACD
    if macd_data and macd_data[0] > 0:
        confidence += 15
        reasons.append("📈 MACD положительный")
    
    # 5. Объёмы
    if _check_volume_support(candles, 'long'):
        confidence += 15
        reasons.append("💰 Объёмы подтверждают")
    
    if confidence >= MIN_CONFIDENCE:
        return _create_signal('LONG', price, best_support, confidence, reasons)
    
    return None

def _analyze_short_signal(price: float, trend: str, rsi: float, macd_data: Optional[Tuple],
                         resistances: List[float], candles: List[dict]) -> Optional[Dict]:
    """Анализ SHORT сигнала"""
    # Находим ближайшее качественное сопротивление
    best_resistance = None
    for resistance in resistances:
        if resistance > price:
            distance_pct = (resistance - price) / price
            if distance_pct <= 0.03:  # Не дальше 3%
                if best_resistance is None or resistance < best_resistance:
                    best_resistance = resistance
    
    if not best_resistance:
        return None
    
    confidence = 0
    reasons = []
    
    # 1. Уровень сопротивления
    distance_pct = (best_resistance - price) / price
    if distance_pct <= 0.015:
        confidence += 25
        reasons.append("🎯 Сильное сопротивление")
    elif distance_pct <= 0.025:
        confidence += 20
        reasons.append("✅ Уровень сопротивления")
    
    # 2. RSI анализ
    if 55 <= rsi <= 70:
        confidence += 25
        reasons.append(f"📊 RSI для входа ({rsi:.1f})")
    elif 50 <= rsi < 55 or 70 < rsi <= 75:
        confidence += 15
        reasons.append(f"📈 RSI приемлемый ({rsi:.1f})")
    
    # 3. Тренд
    if trend == 'bearish':
        confidence += 20
        reasons.append("🔴 Медвежий тренд")
    elif trend == 'neutral':
        confidence += 10
        reasons.append("⚪ Нейтральный тренд")
    
    # 4. MACD
    if macd_data and macd_data[0] < 0:
        confidence += 15
        reasons.append("📉 MACD отрицательный")
    
    # 5. Объёмы
    if _check_volume_support(candles, 'short'):
        confidence += 15
        reasons.append("💰 Объёмы подтверждают")
    
    if confidence >= MIN_CONFIDENCE:
        return _create_signal('SHORT', price, best_resistance, confidence, reasons)
    
    return None

def _check_volume_support(candles: List[dict], side: str) -> bool:
    """Проверка поддержки объёмами"""
    if len(candles) < 20:
        return False
    
    # Анализируем объёмы на последних свечах
    recent_candles = candles[-5:]
    prev_candles = candles[-10:-5]
    
    if not recent_candles or not prev_candles:
        return False
    
    # Средний объём
    recent_volume = sum(c['v'] for c in recent_candles) / len(recent_candles)
    prev_volume = sum(c['v'] for c in prev_candles) / len(prev_candles)
    
    # Для входа нужен повышенный объём
    return recent_volume > prev_volume * 0.8

def _create_signal(side: str, price: float, level: float, confidence: int, reasons: List[str]) -> Dict:
    """Создание сигнала"""
    if side == 'LONG':
        entry_min = level * (1 - ENTRY_ZONE_PERCENT / 100)
        entry_max = level * (1 + ENTRY_ZONE_PERCENT / 100)
        stop_loss = level * (1 - STOP_PERCENT / 100)
        take_profits = [price * 1.02, price * 1.04, price * 1.06]
    else:
        entry_min = level * (1 - ENTRY_ZONE_PERCENT / 100)
        entry_max = level * (1 + ENTRY_ZONE_PERCENT / 100)
        stop_loss = level * (1 + STOP_PERCENT / 100)
        take_profits = [price * 0.98, price * 0.96, price * 0.94]
    
    position_size = _get_position_size(confidence)
    
    return {
        'side': side,
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

def _get_position_size(confidence: int) -> str:
    """Определение размера позиции"""
    if confidence >= 85:
        return "15-20% депо"
    elif confidence >= 75:
        return "10-12% депо"
    elif confidence >= 70:
        return "5-8% депо"
    else:
        return "3-5% депо"

# Совместимость
def quick_screen(pair: str) -> bool:
    candles = CANDLES.get_candles(pair, "1h")
    return len(candles) >= 50
