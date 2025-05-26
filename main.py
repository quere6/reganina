import json
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

USERS_FILE = 'users.json'
GUILDS_FILE = 'guilds.json'

MAX_ENERGY = 100
FEED_COINS_BASE = 25
XP_PER_FEED = 10
GUILD_CREATION_COST = 1000
MAX_GUILD_MEMBERS = 20  # Максимальна кількість учасників гільдії

# Завантаження даних
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Оновлення енергії користувача
def update_energy(user):
    now = time.time()
    elapsed = now - user.get('energy_last_update', now)
    energy_gain = int(elapsed // 60)  # 1 енергія за 1 хвилину
    if energy_gain > 0:
        user['energy'] = min(MAX_ENERGY, user.get('energy', MAX_ENERGY) + energy_gain)
        user['energy_last_update'] = now

# Ініціалізація користувача при першому зверненні
def init_user(users, user_id, first_name):
    if user_id not in users:
        users[user_id] = {
            'username': first_name,  # Зберігаємо основний нік (ім'я), не @username
            'coins': 100,
            'xp': 0,
            'energy': MAX_ENERGY,
            'energy_last_update': time.time(),
            'guild': None,
            'rzhomb': 1,
            'bans': 0,
            'last_feed': 0,
            'active_quest': None
        }

# --- КОМАНДИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    first_name = update.effective_user.first_name or "Гравець"
    init_user(users, user_id, first_name)
    save_data(USERS_FILE, users)
    await update.message.reply_text(f"👋 Вітаю, {first_name}! Твій профіль створено. Використовуй /help для списку команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("⚠️ Спершу використай /start")
        return
    text = (
        "📜 Список команд:\n"
        "/help - Список команд\n"
        "/profile - 👤 Показати профіль\n"
        "/daily - 🎁 Отримати щоденний бонус\n"
        "/feed - 🍖 Погодувати Ржомбу (отримати монети, енергію, XP)\n"
        "/createguild [назва] - 🛡 Створити гільдію (1000 монет)\n"
        "/joinguild [назва] - 🚪 Вступити до гільдії\n"
        "/leaveguild - 🚪 Вийти з гільдії\n"
        "/guild - 🏰 Показати інформацію про гільдію\n"
        "/guildtop - 🏆 Топ гільдій\n"
        "/quests - 📖 Показати квести\n"
        "/completequest - ✅ Виконати активний квест\n"
        "/duel - ⚔️ Почати дуель (планується)\n"
        "/shop - 🛒 Магазин (планується)\n"
        "/achievements - 🏅 Досягнення (скоро)"
    )
    await update.message.reply_text(text)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("⚠️ Спершу використай /start")
        return
    user = users[user_id]
    text = (
        f"👤 Профіль {user['username']}:\n"
        f"💰 Монети: {user['coins']}\n"
        f"⭐ XP: {user['xp']}\n"
        f"🔋 Енергія: {user['energy']}/{MAX_ENERGY}\n"
        f"🏰 Гільдія: {user['guild'] or 'немає'}\n"
        f"🐾 Ржомба рівень: {user['rzhomb']}"
    )
    await update.message.reply_text(text)

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("⚠️ Спершу використай /start")
        return
    user = users[user_id]
    now = time.time()

    last_daily = user.get('last_daily', 0)
    if now - last_daily < 86400:  # 24 години
        await update.message.reply_text("⏳ Щоденний бонус уже отримано. Спробуй пізніше.")
        return

    bonus_coins = 100
    user['coins'] += bonus_coins
    user['last_daily'] = now

    save_data(USERS_FILE, users)
    await update.message.reply_text(f"🎉 Ти отримав щоденний бонус: {bonus_coins} монет!")

async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("⚠️ Спершу використай /start")
        return

    user = users[user_id]
    update_energy(user)
    now = time.time()

    feed_amount = FEED_COINS_BASE + (user['rzhomb'] * 5)

    # Замість знімання монет — додаємо монети
    user['coins'] += feed_amount
    user['energy'] = min(MAX_ENERGY, user.get('energy', 0) + 10)  # +10 енергії
    user['xp'] += XP_PER_FEED
    user['last_feed'] = now

    save_data(USERS_FILE, users)

    await update.message.reply_text(
        f"🍖 Ти погодував ржомбу та отримав {feed_amount} монет! +{XP_PER_FEED} XP, +10 енергії.\n"
        f"💰 Монет зараз: {user['coins']}, енергія: {user['energy']}/{MAX_ENERGY}."
    )

async def create_guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    guilds = load_data(GUILDS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("⚠️ Спершу використай /start")
        return

    user = users[user_id]

    if user['guild'] is not None:
        await update.message.reply_text("⚠️ Ти вже в гільдії.")
        return

    if user['coins'] < GUILD_CREATION_COST:
        await update.message.reply_text(f"⚠️ Для створення гільдії потрібно {GUILD_CREATION_COST} монет.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Вкажи назву гільдії і тип (відкрита або закрита): /createguild Назва [відкрита|закрита]")
        return

    guild_name = args[0].strip()
    guild_type = "відкрита"
    if len(args) > 1:
        if args[1].lower() in ("відкрита", "закрита"):
            guild_type = args[1].lower()

    if guild_name in guilds:
        await update.message.reply_text("⚠️ Гільдія з такою назвою вже існує.")
        return

    guilds[guild_name] = {
        'owner': user_id,
        'members': [user_id],
        'level': 1,
        'xp': 0,
        'type
