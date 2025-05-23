import json
import os
import re
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher
from telegram import Update
from telegram.ext import ContextTypes

DATA_FILE = "users.json"
DAILY_FILE = "daily.json"

PHRASES = {
    "ржомба": "🤣",
    "ну ти там держись": "Ссикло",
    "а воно мені не нада": "Не мужик",
    "наш живчик": "Містер Біст",
    "сігма бой": "Богдан",
}

SPAM_LIMIT = 150
TIME_WINDOW = 300
energy_max = 100
energy_recover_period = 5  # хвилини
daily_base = 50

profiles = {}
daily = {}
user_messages = defaultdict(list)

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

async def save_data():
    save_json(DATA_FILE, profiles)
    save_json(DAILY_FILE, daily)

def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def similar(text):
    for phrase in PHRASES:
        if SequenceMatcher(None, text, phrase).ratio() > 0.7:
            return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global profiles, daily
    profiles = load_json(DATA_FILE, {})
    daily = load_json(DAILY_FILE, {})
    await update.message.reply_text("Привіт! Я Ржомба Бот 🤖")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Почати роботу з ботом",
        "/help - Список команд",
        "/profile - Показати профіль",
        "/daily - Отримати щоденний бонус",
        "/shop - Магазин (планується)",
        "/duel - Почати дуель (планується)",
        "/words - Показати улюблені слова (планується)"
    ]
    await update.message.reply_text("Команди:\n" + "\n".join(commands))

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    p = profiles.get(uid, {
        "username": update.effective_user.username or f"user{uid}",
        "rzhomb": 0,
        "coins": 0,
        "bans": 0,
        "favorite_phrase": "Ржомба",
        "energy": energy_max,
        "energy_last_update": datetime.now().timestamp()
    })
    text = (
        f"👤 Профіль @{p.get('username')}\n"
        f"💬 Улюблена фраза: {p.get('favorite_phrase')}\n"
        f"📊 Ржомбометр: {p.get('rzhomb')}\n"
        f"🪙 Монети: {p.get('coins')}\n"
        f"🚫 Забанений разів: {p.get('bans')}\n"
        f"⚡ Енергія: {p.get('energy')}/{energy_max}"
    )
    await update.message.reply_text(text)

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global daily, profiles
    uid = str(update.effective_user.id)
    now = int(datetime.now().timestamp())
    last = daily.get(uid, 0)
    if now - last < 86400:
        await update.message.reply_text("Сьогодні ти вже отримував.")
        return
    award = daily_base
    profiles.setdefault(uid, {}).setdefault("coins", 0)
    profiles[uid]["coins"] += award
    daily[uid] = now
    await save_data()
    await update.message.reply_text(f"Тримай {award} монет!")

async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global profiles, user_messages
    now = datetime.now()
    uid = update.effective_user.id
    uname = update.effective_user.username or f"user{uid}"
    text = update.message.text or ""
    profile = profiles.setdefault(str(uid), {
        "username": uname,
        "rzhomb": 0,
        "coins": 0,
        "energy": energy_max,
        "energy_last_update": now.timestamp(),
        "bans": 0,
        "favorite_phrase": "Ржомба"
    })

    # Відновлення енергії
    last = datetime.fromtimestamp(profile['energy_last_update'])
    recovered = (now - last).seconds // energy_recover_period
    if recovered > 0:
        profile['energy'] = min(energy_max, profile['energy'] + recovered)
        profile['energy_last_update'] = now.timestamp()

    # Спам-фільтр
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if (now - t).seconds < TIME_WINDOW]
    if len(user_messages[uid]) > SPAM_LIMIT:
        return

    # Обробка повідомлень
    norm = normalize(text)
    cnt = text.lower().count("ржомба")
    if cnt > 0 and profile["energy"] >= cnt:
        profile["rzhomb"] += cnt
        profile["coins"] += cnt * 2
        profile["energy"] -= cnt
        await update.message.reply_text(f"Ржомба! +{cnt*2} монет")
    elif norm in PHRASES:
        await update.message.reply_text(PHRASES[norm])
    elif similar(norm):
        await update.message.reply_text("Ти мазила")
    else:
        await update.message.reply_text("Ржомба")

    await save_data()
