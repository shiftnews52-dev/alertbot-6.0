import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

from config import BOT_TOKEN, ADMIN_IDS, TEST_MODE, TEST_PASSWORD, TEST_USER_IDS
from database import init_db, create_user, update_user_activity, get_user, is_subscription_active, is_test_user, grant_access
from payment_handlers import show_plans_comparison, handle_payment_start, handle_payment_check

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==================== HANDLERS ====================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Создаем/обновляем пользователя
    await create_user(user_id, username, first_name, last_name)
    await update_user_activity(user_id)
    
    # Проверяем подписку (включая тестовый режим)
    has_access = await is_subscription_active(user_id) or await is_test_user(user_id)
    
    text = "🤖 <b>Добро пожаловать в Crypto Signals Bot!</b>\n\n"
    
    if has_access:
        text += "✅ <b>У тебя есть доступ к боту!</b>\n\n"
        if await is_test_user(user_id):
            text += "🎯 <i>Тестовый режим (7 дней)</i>\n\n"
        
        text += "📊 Доступные функции:\n"
        text += "• Торговые сигналы в реальном времени\n"
        text += "• Профессиональный анализ рынка\n"
        text += "• Настройка персональных алертов\n"
        text += "• Реферальная программа 50%\n\n"
        text += "Используй меню ниже для управления ботом"
    else:
        text += "🔒 <b>Premium доступ закрыт</b>\n\n"
        text += "Чтобы получить доступ ко всем функциям:\n"
        text += "• Торговые сигналы\n"
        text += "• Профессиональный анализ\n"
        text += "• Персональные алерты\n"
        text += "• Реферальная программа\n\n"
        text += "👇 Выбери тариф ниже"
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    
    if has_access:
        kb.add(types.InlineKeyboardButton("📈 Сигналы", callback_data="signals"))
        kb.add(types.InlineKeyboardButton("⚙️ Настройки", callback_data="settings"))
    else:
        kb.add(types.InlineKeyboardButton("💎 Купить доступ", callback_data="menu_pay"))
    
    kb.add(types.InlineKeyboardButton("👥 Реферальная программа", callback_data="referral"))
    kb.add(types.InlineKeyboardButton("ℹ️ Помощь", callback_data="help"))
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.message_handler(commands=['test'])
async def cmd_test(message: types.Message):
    """Тестовый вход"""
    if not TEST_MODE:
        await message.answer("❌ Тестовый режим отключен")
        return
    
    args = message.get_args()
    if args == TEST_PASSWORD:
        user_id = message.from_user.id
        TEST_USER_IDS.append(user_id)
        
        # Даём тестовый доступ
        await grant_access(user_id)
        
        await message.answer("✅ <b>Тестовый доступ активирован!</b>\n\n"
                           "Тебе открыт полный доступ к боту на 7 дней!\n\n"
                           "Нажми /start для начала работы", 
                           parse_mode="HTML")
    else:
        await message.answer("❌ Неверный пароль")

@dp.callback_query_handler(lambda c: c.data == "menu_pay")
async def menu_pay_handler(call: types.CallbackQuery):
    """Меню оплаты"""
    await show_plans_comparison(call)

@dp.callback_query_handler(lambda c: c.data.startswith("select_plan_"))
async def select_plan_handler(call: types.CallbackQuery):
    """Выбор тарифа"""
    plan_type = call.data.replace("select_plan_", "")
    await handle_payment_start(call, plan_type)

@dp.callback_query_handler(lambda c: c.data.startswith("check_pay_"))
async def check_payment_handler(call: types.CallbackQuery):
    """Проверка оплаты"""
    await handle_payment_check(call)

@dp.callback_query_handler(lambda c: c.data == "back_main")
async def back_main_handler(call: types.CallbackQuery):
    """Назад в главное меню"""
    await cmd_start(call.message)

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_handler(call: types.CallbackQuery):
    """Реферальная программа"""
    user = await get_user(call.from_user.id)
    lang = user["language"] if user else "ru"
    
    text = "👥 <b>Реферальная программа</b>\n\n"
    text += f"💸 <b>Получай {REFERRAL_PERCENT}% с каждой оплаты твоих рефералов!</b>\n\n"
    text += "🔗 <b>Твоя реферальная ссылка:</b>\n"
    text += f"<code>https://t.me/your_bot?start=ref{call.from_user.id}</code>\n\n"
    text += "📊 <b>Как это работает:</b>\n"
    text += "1. Делишься ссылкой с друзьями\n"
    text += "2. Они покупают любой тариф\n"
    text += f"3. Ты получаешь {REFERRAL_PERCENT}% от их оплаты\n"
    text += "4. Выводишь средства в любой момент\n\n"
    text += "💰 <b>Минимальный вывод:</b> 20 USDT"
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "help")
async def help_handler(call: types.CallbackQuery):
    """Помощь"""
    text = "ℹ️ <b>Помощь</b>\n\n"
    text += "📞 <b>Поддержка:</b> @your_support\n"
    text += "🌐 <b>Канал с сигналами:</b> @your_channel\n"
    text += "📚 <b>Обучение:</b> @your_tutorial\n\n"
    text += "💡 <b>Частые вопросы:</b>\n"
    text += "• Оплата проходит через @CryptoBot\n"
    text += "• Доступ открывается автоматически\n"
    text += "• Реферальные выплаты - раз в неделю\n"
    text += "• Минимальный вывод - 20 USDT"
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

# ==================== ADMIN HANDLERS ====================

@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    """Админ панель"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    
    text = "👑 <b>Админ панель</b>\n\n"
    text += "Доступные команды:\n"
    text += "/stats - Статистика бота\n"
    text += "/users - Список пользователей\n"
    text += "/broadcast - Рассылка\n"
    
    await message.answer(text, parse_mode="HTML")

# ==================== SYSTEM FUNCTIONS ====================

async def on_startup(dp):
    """Запуск бота"""
    logger.info("🤖 Bot starting...")
    
    # Инициализация БД
    await init_db()
    logger.info("✅ Database initialized")
    
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Bot started successfully!")

async def on_shutdown(dp):
    """Завершение работы бота"""
    logger.info("🛑 Bot shutting down...")
    await bot.session.close()

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, reset_webhook=True)
