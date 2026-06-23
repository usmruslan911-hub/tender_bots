import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ТОКЕН (вставьте свой) ---
# ВАЖНО: замените "ВАШ_ТОКЕН" на реальный токен от @TenderGidSupportbot
TOKEN = "8692610495:AAFCZ3u6-iWlAc5vGsWdDhrdksDxvpz_NrI"

if not TOKEN or TOKEN == "ВАШ_ТОКЕН_ОТ_BOTFATHER":
    print("❌ ОШИБКА: Токен не указан! Замените 'ВАШ_ТОКЕН_ОТ_BOTFATHER' на реальный токен.")
    exit()

print("✅ Токен загружен успешно!")


# --- ОБРАБОТЧИКИ КОМАНД ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.first_name} запустил бота")
    
    await update.message.reply_text(
        f"🤝 Привет, {user.first_name}!\n\n"
        f"Я — бот поддержки «Тендерного гида».\n\n"
        f"📌 Напишите мне свой вопрос, и я свяжу вас с экспертом.\n"
        f"⏳ Обычно мы отвечаем в течение 30 минут.\n\n"
        f"🧭 Основной канал: @TenderniyGid\n"
        f"🔥 Актуальные закупки: @TenderGidDeals"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    await update.message.reply_text(
        "/start — Запустить бота\n"
        "/help — Помощь\n\n"
        "Просто напишите мне свой вопрос."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка любого текстового сообщения"""
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"Сообщение от {user.first_name}: {text[:100]}...")
    
    await update.message.reply_text(
        f"✅ Ваше сообщение получено, {user.first_name}!\n\n"
        f"📩 Текст: «{text[:200]}»\n\n"
        f"Я передал его экспертам. Обычно мы отвечаем в течение 30 минут."
    )


# --- ЗАПУСК БОТА ---

async def main() -> None:
    """Запуск бота"""
    try:
        print("🚀 Запуск бота поддержки...")
        
        app = Application.builder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот поддержки успешно запущен!")
        print("📌 Отправьте /start в Telegram: @TenderGidSupportbot")
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Бесконечное ожидание
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
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
        print("👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")