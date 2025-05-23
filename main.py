import asyncio
from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from profiles.profile_handlers import start, help_cmd, profile_cmd, daily_cmd, reply_handler
from shop.shop_handlers import shop_handler
from duels.duels_handlers import duel_handler
import os

TOKEN = "7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig"
PORT = int(os.environ.get("PORT", 8000))  # Render задасть PORT у змінних оточення

async def handle(request):
    return web.Response(text="Bot is running")

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    # Запускаємо одночасно і веб-сервер, і телеграм-бота
    await run_web_server()

    app = ApplicationBuilder().token(TOKEN).build()

    # Основні команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))

    # Інші хендлери
    app.add_handler(shop_handler)
    app.add_handler(duel_handler)

    # Обробка текстових повідомлень
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_handler))

    await app.initialize()
    await app.start()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
