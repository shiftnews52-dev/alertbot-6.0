import os
import time
import asyncio
import logging
from typing import Optional, Dict, List
import aiosqlite
from contextlib import asynccontextmanager
from config import DB_PATH, SUBSCRIPTION_PLANS, REFERRAL_PERCENT

logger = logging.getLogger(__name__)

INIT_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language TEXT DEFAULT 'ru',
    invited_by INTEGER,
    balance REAL DEFAULT 0.0,
    created_ts INTEGER NOT NULL,
    last_activity_ts INTEGER,
    is_blocked INTEGER DEFAULT 0,
    FOREIGN KEY (invited_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_type TEXT NOT NULL,
    starts_ts INTEGER NOT NULL,
    expires_ts INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_ts INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_type TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USDT',
    invoice_id INTEGER UNIQUE,
    status TEXT DEFAULT 'pending',
    created_ts INTEGER NOT NULL,
    paid_ts INTEGER,
    crypto_bot_data TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS referral_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referral_id INTEGER NOT NULL,
    payment_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    created_ts INTEGER NOT NULL,
    FOREIGN KEY (referrer_id) REFERENCES users(id),
    FOREIGN KEY (referral_id) REFERENCES users(id),
    FOREIGN KEY (payment_id) REFERENCES payments(id)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON user_subscriptions(is_active, expires_ts);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
"""

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def get_connection(self):
        async with self._lock:
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            try:
                yield conn
            finally:
                await conn.close()
    
    async def init_db(self):
        async with self.get_connection() as conn:
            await conn.executescript(INIT_SQL)
            await conn.commit()
            logger.info("✅ Database initialized")

db_manager = DatabaseManager()

async def create_user(user_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, invited_by: int = None):
    async with db_manager.get_connection() as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO users 
            (id, username, first_name, last_name, invited_by, created_ts, last_activity_ts) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, first_name, last_name, invited_by, 
             int(time.time()), int(time.time()))
        )
        await conn.commit()

async def update_user_activity(user_id: int):
    async with db_manager.get_connection() as conn:
        await conn.execute(
            "UPDATE users SET last_activity_ts = ? WHERE id = ?",
            (int(time.time()), user_id)
        )
        await conn.commit()

async def get_user(user_id: int) -> Optional[Dict]:
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_subscription(user_id: int, plan_type: str):
    plan = SUBSCRIPTION_PLANS.get(plan_type)
    if not plan:
        raise ValueError(f"Invalid plan type: {plan_type}")
    
    starts_ts = int(time.time())
    expires_ts = starts_ts + (plan["days"] * 86400)
    
    async with db_manager.get_connection() as conn:
        await conn.execute(
            "UPDATE user_subscriptions SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )
        
        await conn.execute(
            """INSERT INTO user_subscriptions 
            (user_id, plan_type, starts_ts, expires_ts, created_ts) 
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, plan_type, starts_ts, expires_ts, starts_ts)
        )
        await conn.commit()

async def get_user_subscription(user_id: int) -> Optional[Dict]:
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """SELECT * FROM user_subscriptions 
            WHERE user_id = ? AND is_active = 1 AND expires_ts > ? 
            ORDER BY id DESC LIMIT 1""",
            (user_id, int(time.time()))
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def is_subscription_active(user_id: int) -> bool:
    subscription = await get_user_subscription(user_id)
    return subscription is not None

async def create_payment_record(user_id: int, plan_type: str, amount: float, 
                              invoice_id: int = None, crypto_data: str = None):
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """INSERT INTO payments 
            (user_id, plan_type, amount, invoice_id, crypto_bot_data, created_ts) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, plan_type, amount, invoice_id, crypto_data, int(time.time()))
        )
        await conn.commit()
        return cursor.lastrowid

async def update_payment_status(invoice_id: int, status: str, crypto_data: str = None):
    paid_ts = int(time.time()) if status == "paid" else None
    
    async with db_manager.get_connection() as conn:
        await conn.execute(
            "UPDATE payments SET status = ?, paid_ts = ?, crypto_bot_data = ? WHERE invoice_id = ?",
            (status, paid_ts, crypto_data, invoice_id)
        )
        await conn.commit()

async def get_payment_by_invoice(invoice_id: int) -> Optional[Dict]:
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM payments WHERE invoice_id = ?", (invoice_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_referral_payment(referrer_id: int, referral_id: int, payment_id: int, amount: float):
    async with db_manager.get_connection() as conn:
        await conn.execute(
            """INSERT INTO referral_payments 
            (referrer_id, referral_id, payment_id, amount, created_ts) 
            VALUES (?, ?, ?, ?, ?)""",
            (referrer_id, referral_id, payment_id, amount, int(time.time()))
        )
        await conn.commit()

async def update_user_balance(user_id: int, amount: float):
    async with db_manager.get_connection() as conn:
        await conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (amount, user_id)
        )
        await conn.commit()

async def get_user_balance(user_id: int) -> float:
    user = await get_user(user_id)
    return user["balance"] if user else 0.0

async def init_db():
    await db_manager.init_db()

# Совместимость
async def grant_access(uid: int):
    await create_subscription(uid, "1_month")

async def add_balance(uid: int, amount: float):
    await update_user_balance(uid, amount)
