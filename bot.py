import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import requests
from bs4 import BeautifulSoup

# Загружаем переменные окружения
load_dotenv()

# --- КОНФИГУРАЦИЯ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле!")

# Названия каналов
MAIN_CHANNEL = "@TenderniyGid"
DEALS_CHANNEL = "@TenderGidDeals"
SUPPORT_BOT = "@TenderGidSupport"

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище подписок
user_subscriptions = {}
sent_tenders = set()


# --- ФУНКЦИИ ПОИСКА ТЕНДЕРОВ ---

async def search_tenders_by_keyword(keyword: str, max_results: int = 10) -> List[Dict]:
    """Ищет тендеры на ЕИС по ключевому слову"""
    logger.info(f"Поиск тендеров по ключевому слову: {keyword}")
    
    try:
        search_url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
        params = {
            "fz44": "on",
            "fz223": "on",
            "searchString": keyword,
            "pageNumber": 1,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        tenders = []
        
        for item in soup.select(".search-registry-entry-block"):
            try:
                link_elem = item.select_one("a.registry-entry__title")
                if not link_elem:
                    continue
                    
                tender_number = link_elem.text.strip()
                tender_url = "https://zakupki.gov.ru" + link_elem.get("href", "")
                
                customer_elem = item.select_one(".registry-entry__body-info .cell-org-name span")
                customer = customer_elem.text.strip() if customer_elem else "Не указан"
                
                price_elem = item.select_one(".price .price-value")
                price = price_elem.text.strip() if price_elem else "Не указана"
                
                date_elem = item.select_one(".data-wrap .data")
                publish_date = date_elem.text.strip() if date_elem else "Не указана"
                
                law_elem = item.select_one(".registry-entry__header-law")
                law = law_elem.text.strip() if law_elem else "Не указан"
                
                tenders.append({
                    "number": tender_number,
                    "url": tender_url,
                    "customer": customer,
                    "price": price,
                    "publish_date": publish_date,
                    "law": law,
                    "keyword": keyword,
                })
                
                if len(tenders) >= max_results:
                    break
                    
            except Exception as e:
                logger.warning(f"Ошибка при парсинге: {e}")
                continue
                
        logger.info(f"Найдено {len(tenders)} тендеров по запросу '{keyword}'")
        return tenders
        
    except Exception as e:
        logger.error(f"Ошибка при поиске тендеров: {e}")
        return []


# --- ОБРАБОТЧИКИ КОМАНД ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.first_name} (ID: {user.id}) запустил бота")
    
    keyboard = [
        [InlineKeyboardButton("🔍 Найти тендеры", callback_data="search")],
        [InlineKeyboardButton("📌 Мои подписки", callback_data="subscriptions")],
        [InlineKeyboardButton("📊 Дайджест", callback_data="digest")],
        [InlineKeyboardButton("🧭 Основной канал", url=f"https://t.me/{MAIN_CHANNEL[1:]}")],
        [InlineKeyboardButton("🔥 Горячие закупки", url=f"https://t.me/{DEALS_CHANNEL[1:]}")],
        [InlineKeyboardButton("🤝 Нужна помощь?", url=f"https://t.me/{SUPPORT_BOT[1:]}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ИСПРАВЛЕНО: убраны HTML-теги вокруг "слово"
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🧭 Я — бот-поисковик «Тендерного гида».\n\n"
        f"🔎 Я умею находить актуальные тендеры по 44-ФЗ и 223-ФЗ.\n\n"
        f"📌 Как пользоваться:\n"
        f"• Отправь мне ключевое слово (например, «строительство»)\n"
        f"• Используй команду /search (например: /search строительство)\n"
        f"• Подпишись на ключевые слова: /subscribe строительство\n\n"
        f"🤝 Нужна помощь с подачей заявки? Пиши: {SUPPORT_BOT}",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    await update.message.reply_text(
        "🤖 Помощь по командам:\n\n"
        "/start - Запустить бота\n"
        "/search слово - Найти тендеры\n"
        "/subscribe слово - Подписаться\n"
        "/subscriptions - Мои подписки\n"
        "/unsubscribe слово - Отписаться\n"
        "/digest - Дайджест для Дзена\n"
        "/help - Помощь"
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /search"""
    if not context.args:
        await update.message.reply_text("Укажите ключевое слово. Пример: /search строительство")
        return
    
    keyword = " ".join(context.args)
    update.message.text = keyword
    await handle_message(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений как поисковых запросов"""
    keyword = update.message.text.strip()
    
    if len(keyword) < 2:
        await update.message.reply_text("Введите ключевое слово длиной от 2 символов.")
        return
    
    status_msg = await update.message.reply_text(f"🔍 Ищу тендеры по запросу «{keyword}»...")
    
    tenders = await search_tenders_by_keyword(keyword)
    
    await status_msg.delete()
    
    if not tenders:
        await update.message.reply_text(
            f"😕 По запросу «{keyword}» тендеров не найдено.\n\n"
            f"💡 Попробуйте другое ключевое слово."
        )
        return
    
    await update.message.reply_text(
        f"📋 Найдено {len(tenders)} тендеров по запросу «{keyword}»:"
    )
    
    for i, tender in enumerate(tenders[:5], 1):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Открыть на ЕИС", url=tender['url'])],
        ])
        
        text = (
            f"{i}. {tender['number']}\n"
            f"Заказчик: {tender['customer']}\n"
            f"Сумма: {tender['price']}\n"
            f"Опубликован: {tender['publish_date']}"
        )
        await update.message.reply_text(text, reply_markup=keyboard)
        await asyncio.sleep(0.3)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписка на ключевое слово"""
    if not context.args:
        await update.message.reply_text("Укажите ключевое слово. Пример: /subscribe медицина")
        return
    
    keyword = " ".join(context.args).lower()
    user_id = update.effective_user.id
    
    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = set()
    
    if keyword in user_subscriptions[user_id]:
        await update.message.reply_text(f"✅ Вы уже подписаны на «{keyword}»")
        return
    
    user_subscriptions[user_id].add(keyword)
    await update.message.reply_text(f"✅ Подписка на «{keyword}» оформлена!")


async def my_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать подписки"""
    user_id = update.effective_user.id
    
    if user_id not in user_subscriptions or not user_subscriptions[user_id]:
        await update.message.reply_text("📭 У вас нет активных подписок.")
        return
    
    keywords = "\n• ".join(sorted(user_subscriptions[user_id]))
    await update.message.reply_text(f"📌 Ваши подписки:\n\n• {keywords}")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отписка от ключевого слова"""
    if not context.args:
        await update.message.reply_text("Укажите ключевое слово. Пример: /unsubscribe медицина")
        return
    
    keyword = " ".join(context.args).lower()
    user_id = update.effective_user.id
    
    if user_id not in user_subscriptions or keyword not in user_subscriptions[user_id]:
        await update.message.reply_text(f"❌ Вы не подписаны на «{keyword}»")
        return
    
    user_subscriptions[user_id].remove(keyword)
    await update.message.reply_text(f"✅ Подписка на «{keyword}» отменена.")


async def digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Дайджест для Дзена"""
    user_id = update.effective_user.id
    
    if user_id not in user_subscriptions or not user_subscriptions[user_id]:
        await update.message.reply_text("📭 Нет подписок для дайджеста.")
        return
    
    all_tenders = []
    for keyword in user_subscriptions[user_id]:
        tenders = await search_tenders_by_keyword(keyword, max_results=5)
        all_tenders.extend(tenders)
        await asyncio.sleep(0.5)
    
    if not all_tenders:
        await update.message.reply_text("📭 По вашим подпискам тендеров не найдено.")
        return
    
    text = f"Дайджест тендеров от «Тендерного гида»\n📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
    
    for keyword in sorted(user_subscriptions[user_id]):
        keyword_tenders = [t for t in all_tenders if t.get("keyword") == keyword]
        if keyword_tenders:
            text += f"По запросу «{keyword}» — {len(keyword_tenders)} тендеров:\n\n"
            for tender in keyword_tenders[:3]:
                text += f"{tender['number']}\nЗаказчик: {tender['customer']}\nСумма: {tender['price']}\nСсылка: {tender['url']}\n\n"
    
    await update.message.reply_text(text[:4000])


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "search":
        await query.message.reply_text("🔍 Отправьте мне ключевое слово текстом.")
    elif query.data == "subscriptions":
        await my_subscriptions(update, context)
    elif query.data == "digest":
        await digest(update, context)


# --- ЗАПУСК БОТА ---

async def main() -> None:
    """Запуск бота"""
    try:
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрируем команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("search", search_command))
        app.add_handler(CommandHandler("subscribe", subscribe))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe))
        app.add_handler(CommandHandler("subscriptions", my_subscriptions))
        app.add_handler(CommandHandler("digest", digest))
        
        # Обработчики
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(callback_handler))
        
        logger.info("🤖 Бот «Тендерный гид» успешно запущен!")
        logger.info("✅ Отправьте /start в Telegram")
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        if 'app' in locals():
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")