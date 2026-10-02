import asyncio
import logging
import os
from typing import Callable, Dict, Any, Awaitable
from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import Message

from database import init_db, add_user, update_user_info, log_message
from handlers import welcome, faq, stats, games, seabattle

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


class StatsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user and not event.from_user.is_bot:
            await add_user(event.from_user.id, event.from_user.username, event.from_user.first_name)
            await update_user_info(event.from_user.id, event.from_user.username, event.from_user.first_name)
            await log_message(event.from_user.id, event.chat.id)
        return await handler(event, data)


# Фоновый веб-сервер для поддержки работы 24/7 на Render
async def handle_ping(request):
    return web.Response(text="Bot Sib.Bear is running 24/7!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Middleware для подсчёта сообщений
    dp.message.middleware(StatsMiddleware())

    # Роутеры (seabattle перед games, чтобы не перехватывались ходы)
    dp.include_router(welcome.router)
    dp.include_router(faq.router)
    dp.include_router(stats.router)
    dp.include_router(seabattle.router)
    dp.include_router(games.router)

    print("🤖 Бот Sib.Bear запущен!")

    # Запускаем одновременно веб-сервер и бота
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
