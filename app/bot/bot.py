import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from app.bot.handlers.start import router as start_router
from app.bot.handlers.fields import router as fields_router
from app.bot.handlers.weather import router as weather_router
from app.bot.handlers.satellite import router as satellite_router
from app.bot.handlers.summary import router as summary_router

from database.db import create_database, update_database


# =========================================================
# Загрузка настроек
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("ОШИБКА: BOT_TOKEN не найден в .env")
    exit()


# =========================================================
# Bot и Dispatcher
# =========================================================

bot = Bot(
    token=TOKEN
)

dp = Dispatcher(
    storage=MemoryStorage()
)


# =========================================================
# База данных
# =========================================================

create_database()
update_database()


# =========================================================
# Подключение обработчиков
# =========================================================

dp.include_router(start_router)
dp.include_router(fields_router)
dp.include_router(weather_router)
dp.include_router(satellite_router)
dp.include_router(summary_router)


# =========================================================
# Запуск
# =========================================================

async def main():

    print("AgroAI запускается...")
    print("Бот запущен. Ожидание сообщений...")

    await dp.start_polling(bot)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())