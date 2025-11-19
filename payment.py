import os
import asyncio
import logging
import httpx
from typing import Optional, Dict
from config import CRYPTO_BOT_TOKEN, SUBSCRIPTION_PLANS, REFERRAL_PERCENT
from database import create_payment_record, get_payment_by_invoice, add_referral_payment, update_user_balance, grant_access

logger = logging.getLogger(__name__)

class CryptoBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
    
    async def create_invoice(self, user_id: int, amount: float, currency: str = "USDT") -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/createInvoice",
                    headers={"Crypto-Pay-API-Token": self.token},
                    json={
                        "asset": currency,
                        "amount": str(amount),
                        "description": "💰 Premium доступ к торговым сигналам",
                        "hidden_message": f"Оплата подписки\nUser ID: {user_id}",
                        "paid_btn_name": "open_bot", 
                        "paid_btn_url": f"https://t.me/your_bot",
                        "payload": str(user_id),
                        "allow_comments": False,
                        "allow_anonymous": False,
                        "expires_in": 3600
                    }
                )
                data = response.json()
                
                if data.get("ok"):
                    logger.info(f"Invoice created: {data['result']['invoice_id']} for user {user_id}")
                    return data["result"]
                else:
                    logger.error(f"CryptoBot API error: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Create invoice error: {e}")
            return None
    
    async def check_invoice(self, invoice_id: int) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/getInvoices",
                    headers={"Crypto-Pay-API-Token": self.token},
                    params={"invoice_ids": str(invoice_id)}
                )
                data = response.json()
                
                if data.get("ok") and data["result"]["items"]:
                    return data["result"]["items"][0]
                return None
                
        except Exception as e:
            logger.error(f"Check invoice error: {e}")
            return None

crypto_bot = CryptoBot(CRYPTO_BOT_TOKEN)

async def create_payment(user_id: int, plan_type: str = "1_month") -> Optional[Dict]:
    plan = SUBSCRIPTION_PLANS.get(plan_type)
    if not plan:
        return None
    
    payment_data = await crypto_bot.create_invoice(user_id, plan["price_usdt"])
    
    if payment_data:
        await create_payment_record(user_id, plan_type, plan["price_usdt"], 
                                  payment_data["invoice_id"])
    return payment_data

async def check_payment(invoice_id: int) -> bool:
    invoice = await crypto_bot.check_invoice(invoice_id)
    return invoice and invoice.get("status") == "paid"

async def process_successful_payment(user_id: int, amount: float, referral_id: int = None):
    await grant_access(user_id)
    
    if referral_id:
        referral_bonus = amount * (REFERRAL_PERCENT / 100)
        await update_user_balance(referral_id, referral_bonus)
        
        payment = await get_payment_by_invoice(invoice_id)
        if payment:
            await add_referral_payment(referral_id, user_id, payment["id"], referral_bonus)
        
        logger.info(f"Referral bonus {referral_bonus} added to {referral_id}")
