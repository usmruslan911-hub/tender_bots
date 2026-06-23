import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения из файла .env
load_dotenv()

# Токен бота поддержки (из переменной окружения)
TOKEN = os.getenv("TENDER_SUPPORT_BOT_TOKEN")

# Если переменная не найдена — используем токен напрямую (на время теста)
if not TOKEN:
    TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"  # Замените на реальный токен @tendersupportbot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- ОБРАБОТЧИКИ КОМАНД ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.first_name} (ID: {user.id}) запустил бота поддержки")
    
    await update.message.reply_text(
        f"🤝 Привет, {user.first_name}!\n\n"
        f"Я — бот поддержки «Тендерного гида».\n\n"
        f"📌 Напишите мне свой вопрос, и я свяжу вас с экспертом.\n"
        f"• Вы можете оставить заявку на сопровождение тендера\n"
        f"• Задать вопрос по участию в закупках\n"
        f"• Попросить проверить вашу заявку\n\n"
        f"⏳ Обычно мы отвечаем в течение 30 минут.\n\n"
        f"А пока можете посмотреть полезные материалы:\n"
        f"🧭 Основной канал: @TenderniyGid\n"
        f"🔥 Актуальные закупки: @TenderGidDeals\n"
        f"🔍 Бот-поисковик: @TenderSearch7bot"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    await update.message.reply_text(
        "🤖 Помощь по боту поддержки:\n\n"
        "/start — Запустить бота\n"
        "/help — Помощь\n\n"
        "Просто напишите мне свой вопрос, и я передам его экспертам."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка любого текстового сообщения"""
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"Сообщение от {user.first_name} (ID: {user.id}): {text[:100]}...")
    
    # Отправляем автоматический ответ
    await update.message.reply_text(
        f"✅ Ваше сообщение получено, {user.first_name}!\n\n"
        f"📩 Текст: «{text[:200]}»\n\n"
        f"Я передал его нашим экспертам. Обычно мы отвечаем в течение 30 минут.\n\n"
        f"А пока можете посмотреть:\n"
        f"🧭 Полезные материалы: @TenderniyGid\n"
        f"🔥 Свежие закупки: @TenderGidDeals\n\n"
        f"Если вопрос срочный — напишите ещё раз, я ускорю ответ! ⏰"
    )
    
    # Здесь можно добавить пересылку сообщения вам в личку
    # Например, если вы хотите получать уведомления о новых заявках:
    # await context.bot.send_message(
    #     chat_id=ВАШ_ID_В_ТЕЛЕГРАМ,
    #     text=f"Новое сообщение от @{user.username}:\n\n{text}"
    # )


# --- ЗАПУСК БОТА ---

async def main() -> None:
    """Запуск бота поддержки"""
    try:
        app = Application.builder().token(TOKEN).build()
        
        # Регистрируем команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        
        # Обработчик всех текстовых сообщений (кроме команд)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 Бот поддержки «Тендерный гид» успешно запущен!")
        logger.info("✅ Отправьте /start в Telegram: @tendersupportbot")
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Бесконечное ожидание
        while True:
            import asyncio
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("👋 Бот поддержки остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота поддержки: {e}")
    finally:
        if 'app' in locals():
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except:
                pass


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот поддержки остановлен")