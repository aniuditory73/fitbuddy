

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties # New import
from aiogram.fsm.context import FSMContext
from handlers import router as user_router
from config import BOT_TOKEN, ADMIN_ID
from database import create_tables_if_not_exists
from utils import load_exercises_from_json # Re-add this import

logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    create_tables_if_not_exists()
    await load_exercises_from_json()
    await bot.send_message(ADMIN_ID, "Бот запущен!")

async def main() -> None:
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.startup.register(on_startup)

    from web_server import start_web_server
    start_web_server() # Запускаем веб-сервер в отдельном потоке
    await dp.start_polling(bot) # Запускаем бота


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
