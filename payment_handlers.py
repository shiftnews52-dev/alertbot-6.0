import logging
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUBSCRIPTION_PLANS, CRYPTO_BOT_USERNAME, REFERRAL_PERCENT
from payment import create_payment, check_payment, process_successful_payment
from database import get_user, update_payment_status

logger = logging.getLogger(__name__)

async def show_plans_comparison(call: types.CallbackQuery):
    """Показать сравнение тарифов"""
    user = await get_user(call.from_user.id)
    lang = user["language"] if user else "ru"
    
    text = "🏆 <b>Сравнение тарифов</b>\n\n"
    
    # Таблица сравнения
    text += "┌──────────────┬──────────┬──────────┬────────────┐\n"
    text += "│   <b>Тариф</b>   │  <b>Цена</b>   │ <b>Скидка</b>  │ <b>Экономия</b>  │\n"
    text += "├──────────────┼──────────┼──────────┼────────────┤\n"
    
    for plan_key, plan in SUBSCRIPTION_PLANS.items():
        tariff_name = plan["name"].ljust(8)
        price = f"{plan['price']}$".ljust(6)
        
        if plan["discount"] > 0:
            discount = f"{plan['discount']}%".ljust(6)
            savings = f"{plan['original_price'] - plan['price']}$".ljust(8)
        else:
            discount = "—".ljust(6)
            savings = "—".ljust(8)
        
        text += f"│ {tariff_name}    │  {price}  │  {discount}  │   {savings}  │\n"
    
    text += "└──────────────┴──────────┴──────────┴────────────┘\n\n"
    
    text += "💡 <b>Рекомендуем:</b>\n"
    text += "• <b>3 месяца</b> - оптимальная цена\n"
    text += "• <b>12 месяцев</b> - максимальная выгода\n\n"
    
    text += "👇 Выбери подходящий тариф:"
    
    kb = InlineKeyboardMarkup(row_width=1)
    
    for plan_key, plan in SUBSCRIPTION_PLANS.items():
        if plan["discount"] > 0:
            button_text = f"🎯 {plan['name']} - {plan['price']} USDT (-{plan['discount']}%)"
        else:
            button_text = f"📦 {plan['name']} - {plan['price']} USDT"
        
        kb.add(InlineKeyboardButton(button_text, callback_data=f"select_plan_{plan_key}"))
    
    kb.add(InlineKeyboardButton("❌ Назад", callback_data="back_main"))
    
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

async def handle_payment_start(call: types.CallbackQuery, plan_type: str = "1_month"):
    """Начало процесса оплаты для выбранного тарифа"""
    user = await get_user(call.from_user.id)
    lang = user["language"] if user else "ru"
    
    plan = SUBSCRIPTION_PLANS.get(plan_type)
    if not plan:
        await call.answer("❌ Ошибка выбора тарифа", show_alert=True)
        return
    
    # Создаём счёт в Crypto Bot
    payment_data = await create_payment(call.from_user.id, plan_type)
    
    if not payment_data:
        await call.answer("❌ Ошибка создания платежа. Попробуйте позже.", show_alert=True)
        return
    
    invoice_id = payment_data["invoice_id"]
    pay_url = payment_data["pay_url"]
    
    text = f"💎 <b>Оплата {plan['name']}</b>\n\n"
    text += f"💰 Сумма: <code>{plan['price_usdt']} USDT</code>\n"
    
    if plan["discount"] > 0:
        text += f"💸 Было: <s>{plan['original_price']} USDT</s>\n"
        text += f"🎁 Скидка: {plan['discount']}%\n"
        text += f"💵 Экономия: {plan['original_price'] - plan['price']} USDT\n"
    
    text += f"⏰ Срок: {plan['days']} дней\n"
    text += f"👥 Рефералка: {REFERRAL_PERCENT}%\n\n"
    text += f"🔹 Нажми кнопку ниже для оплаты\n"
    text += f"🔹 После оплаты доступ откроется автоматически\n\n"
    text += f"💡 Оплата через @{CRYPTO_BOT_USERNAME}"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 Оплатить в Crypto Bot", url=pay_url))
    kb.add(InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_pay_{invoice_id}"))
    kb.add(InlineKeyboardButton("📋 Выбрать другой тариф", callback_data="menu_pay"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="back_main"))
    
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

async def handle_payment_check(call: types.CallbackQuery):
    """Проверка оплаты"""
    user = await get_user(call.from_user.id)
    lang = user["language"] if user else "ru"
    
    invoice_id = int(call.data.split("_")[2])
    
    await call.answer("🔍 Проверяем оплату...")
    
    is_paid = await check_payment(invoice_id)
    
    if is_paid:
        await update_payment_status(invoice_id, "paid")
        await process_successful_payment(call.from_user.id, SUBSCRIPTION_PLANS["1_month"]["price"])
        
        text = "🎉 <b>Оплата подтверждена!</b>\n\n"
        text += "✅ Premium доступ активирован!\n\n"
        text += "<b>Теперь тебе доступно:</b>\n"
        text += "• 📈 Получение торговых сигналов\n"
        text += "• ⚡ Быстрые уведомления\n"
        text += "• 🎯 Профессиональный анализ\n"
        text += "• 👥 Реферальная программа 50%\n\n"
        text += "Нажми /start для начала!"
        
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🚀 Начать использовать", callback_data="back_main"))
        
        await call.message.edit_text(text, reply_markup=kb)
        
    else:
        text = "⏳ <b>Оплата ещё не поступила</b>\n\n"
        text += "Если ты уже оплатил, подожди 2-3 минуты\n"
        text += "Или проверь:\n"
        text += "• Правильность перевода\n"
        text += "• Достаточность суммы\n"
        text += "• Комиссию сети\n\n"
        text += "Попробуй проверить ещё раз через минуту"
        
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 Проверить ещё раз", callback_data=f"check_pay_{invoice_id}"))
        kb.add(InlineKeyboardButton("💳 Оплатить снова", callback_data="menu_pay"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="back_main"))
        
        await call.message.edit_text(text, reply_markup=kb)
