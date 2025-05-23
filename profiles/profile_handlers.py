import json
import os
import re
import random
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes

DATA_FILE = "users.json"
DAILY_FILE = "daily.json"
GUILDS_FILE = "guilds.json"
QUESTS_FILE = "quests.json"

energy_max = 100
feed_energy_gain = 30  # скільки енергії дає годування
feed_base_coins = 25
feed_xp_gain = 10
guild_creation_cost = 1000
quest_cooldown = 4 * 3600  # 4 години у секундах

# Військові назви рівнів — придумав у стилі воїнів
LEVEL_NAMES = [
    "Новобранець", "Рекрут", "Бійць", "Воїн", "Капітан", "Командир",
    "Полководець", "Генерал", "Легенда", "Міф"
]

profiles = {}
daily = {}
guilds = {}
quests = {}
user_messages = defaultdict(list)

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_all():
    save_json(DATA_FILE, profiles)
    save_json(DAILY_FILE, daily)
    save_json(GUILDS_FILE, guilds)
    save_json(QUESTS_FILE, quests)

def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def get_level(xp):
    # Залежність рівня від XP — приблизна логарифмічна шкала
    level = 0
    threshold = 50
    while xp >= threshold and level < len(LEVEL_NAMES) - 1:
        xp -= threshold
        threshold = int(threshold * 1.5)
        level += 1
    return level

def get_level_name(level):
    return LEVEL_NAMES[level] if level < len(LEVEL_NAMES) else LEVEL_NAMES[-1]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global profiles, daily, guilds, quests
    profiles = load_json(DATA_FILE, {})
    daily = load_json(DAILY_FILE, {})
    guilds = load_json(GUILDS_FILE, {})
    quests = load_json(QUESTS_FILE, {})
    await update.message.reply_text("Привіт! Я Ржомба Бот — тепер із гільдіями, квестами і воєнною тематикою!")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Почати роботу з ботом",
        "/help - Список команд",
        "/profile - Показати профіль",
        "/daily - Отримати щоденний бонус",
        "/feed - Погодувати Ржомбу (відновлення енергії, монети, XP)",
        "/createguild [назва] - Створити гільдію (1000 монет)",
        "/joinguild [назва] - Вступити до гільдії",
        "/leaveguild - Вийти з гільдії",
        "/guild - Показати інформацію про гільдію",
        "/guildtop - Топ гільдій",
        "/quests - Показати квести",
        "/completequest - Виконати активний квест",
        "/duel - Почати дуель (планується)",
        "/shop - Магазин (планується)",
        "/achievements - Досягнення (скоро)"
    ]
    await update.message.reply_text("Команди:\n" + "\n".join(commands))

def get_profile(uid, username):
    # Повертає профіль, створює якщо нема
    if uid not in profiles:
        profiles[uid] = {
            "username": username,
            "coins": 0,
            "xp": 0,
            "energy": energy_max,
            "energy_last_update": datetime.now().timestamp(),
            "guild": None,
            "rzhomb": 0,
            "bans": 0,
            "last_feed": 0,
            "active_quest": None
        }
    return profiles[uid]

def get_guild(guild_name):
    for gid, g in guilds.items():
        if g["guild_name"].lower() == guild_name.lower():
            return gid, g
    return None, None

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    uname = update.effective_user.username or update.effective_user.first_name or f"user{uid}"
    p = get_profile(uid, uname)

    level = get_level(p["xp"])
    level_name = get_level_name(level)

    guild_text = "Відсутня"
    if p["guild"]:
        g = guilds.get(p["guild"])
        if g:
            guild_text = f"{g['guild_name']} (Рівень: {g['level']}, Баланс: {g['balance']})"

    text = (
        f"👤 Профіль @{p.get('username')}\n"
        f"⚔️ Рівень: {level} — {level_name}\n"
        f"🪙 Монети: {p.get('coins')}\n"
        f"⚡ Енергія: {p.get('energy')}/{energy_max}\n"
        f"🏰 Гільдія: {guild_text}\n"
        f"📊 Ржомбометр: {p.get('rzhomb')}\n"
        f"🚫 Забанений разів: {p.get('bans')}\n"
    )
    await update.message.reply_text(text)

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global daily, profiles
    uid = str(update.effective_user.id)
    now = int(datetime.now().timestamp())
    last = daily.get(uid, 0)
    if now - last < 86400:
        await update.message.reply_text("Сьогодні ти вже отримував щоденний бонус.")
        return
    award = 50
    p = get_profile(uid, update.effective_user.username or f"user{uid}")
    p["coins"] += award
    daily[uid] = now
    save_all()
    await update.message.reply_text(f"Тримай {award} монет!")

async def feed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    now_ts = int(datetime.now().timestamp())
    p = get_profile(uid, update.effective_user.username or f"user{uid}")

    # Перевірка часу останнього годування (раз на 6 годин)
    if now_ts - p["last_feed"] < 6 * 3600:
        await update.message.reply_text("Ржомба ще не голодний! Спробуй пізніше.")
        return

    # Відновлення енергії
    p["energy"] = min(energy_max, p["energy"] + feed_energy_gain)

    # Монети за годування - базова + 1 монета за кожен рівень
    level = get_level(p["xp"])
    coins_gain = feed_base_coins + level
    p["coins"] += coins_gain

    # XP за годування
    p["xp"] += feed_xp_gain

    p["last_feed"] = now_ts

    save_all()
    await update.message.reply_text(
        f"Дякую, що погодував Ржомбу! Ти отримав {coins_gain} монет і {feed_xp_gain} XP."
    )

async def createguild_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    uname = update.effective_user.username or update.effective_user.first_name or f"user{uid}"
    p = get_profile(uid, uname)
    args = context.args
    if p["coins"] < guild_creation_cost:
        await update.message.reply_text(f"Для створення гільдії потрібно {guild_creation_cost} монет.")
        return
    if p["guild"]:
        await update.message.reply_text("Ти вже в гільдії, щоб створити нову — вийди з поточної.")
        return
    if not args:
        await update.message.reply_text("Вкажи назву гільдії: /createguild [назва]")
        return

    guild_name = " ".join(args).strip()
    _, existing = get_guild(guild_name)
    if existing:
        await update.message.reply_text("Гільдія з такою назвою вже існує.")
        return

    guild_id = str(len(guilds) + 1)
    guilds[guild_id] = {
        "guild_name": guild_name,
        "leader_id": uid,
        "members": [uid],
        "level": 1,
        "balance": 0,
        "attack_bonus": 0,
        "drop_bonus": 0,
