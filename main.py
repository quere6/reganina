import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from profiles.profile_handlers import start, help_cmd, profile_cmd, daily_cmd, reply_handler
from shop.shop_handlers import shop_handler
from duels.duels_handlers import duel_handler

TOKEN = "7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig"

async def main():
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
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())
