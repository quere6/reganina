from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

# Проста команда магазину, можна розширювати

async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Магазин відкрито! Тут можна купувати різні штуки. (Ще в розробці)")

shop_handler = CommandHandler("shop", shop_cmd)
