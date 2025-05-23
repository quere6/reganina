import asyncio
import os from aiohttp 
import web from telegram.ext 
import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters from profiles.profiles_handlers 
import start, help_cmd, profile_cmd, daily_cmd, reply_handler from shop.shop_handlers
import shop_handler from duels.duels_handlers 
import duel_handler

TOKEN = "7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig" PORT = int(os.environ.get("PORT", 8000)) WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook/{TOKEN}"

async def handle_root(request): return web.Response(text="Bot is running")

async def main(): app = ApplicationBuilder().token(TOKEN).build()

# Команди
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("profile", profile_cmd))
app.add_handler(CommandHandler("daily", daily_cmd))
app.add_handler(shop_handler)
app.add_handler(duel_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_handler))

# Webhook-сервер
async def webhook_handler(request):
    data = await request.json()
    await app.update_queue.put(data)
    return web.Response()

web_app = web.Application()
web_app.router.add_get("/", handle_root)
web_app.router.add_post(f"/webhook/{TOKEN}", webhook_handler)

runner = web.AppRunner(web_app)
await runner.setup()
site = web.TCPSite(runner, "0.0.0.0", PORT)
await site.start()

await app.initialize()
await app.start()
await app.bot.set_webhook(url=WEBHOOK_URL)
print("Bot started with webhook")

await asyncio.Event().wait()

if name == "main": asyncio.run(main())

