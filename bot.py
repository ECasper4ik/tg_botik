# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config

# Импорт роутеров
from handlers.start import router as start_router
from handlers.search import router as search_router
from handlers.callback import router as callback_router
from handlers.consent import router as consent_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Создаём бота
    bot = Bot(token=config.BOT_TOKEN)
    
    # Создаём диспетчер
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем роутеры
    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(consent_router)
    dp.include_router(callback_router)
    
    logger.info("🚀 Бот запущен!")
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")