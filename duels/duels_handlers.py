from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

# Дуелі — заглушка для прикладу

async def duel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Дуелі поки що в розробці!")

duel_handler = CommandHandler("duel", duel_cmd)
