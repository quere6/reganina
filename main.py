from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import json
import time

USERS_FILE = 'users.json'
GUILDS_FILE = 'guilds.json'

MAX_ENERGY = 100
FEED_COINS_BASE = 25
XP_PER_FEED = 10
GUILD_CREATION_COST = 1000
MAX_GUILD_MEMBERS = 20

# Функції для роботи з файлами (завантаження/збереження)
def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Оновлення енергії користувача
def update_energy(user):
    now = time.time()
    elapsed = now - user.get('energy_last_update', now)
    energy_gain = int(elapsed // 60)  # 1 енергія за 1 хвилину
    if energy_gain > 0:
        user['energy'] = min(MAX_ENERGY, user.get('energy', MAX_ENERGY) + energy_gain)
        user['energy_last_update'] = now

# Ініціалізація користувача
def init_user(users, user_id, username):
    if user_id not in users:
        users[user_id] = {
            'username': username,
            'coins': 100,
            'xp': 0,
            'energy': MAX_ENERGY,
            'energy_last_update': time.time(),
            'guild': None,
            'rzhomb': 1,
            'bans': 0,
            'last_feed': 0,
            'active_quest': None,
            'last_daily': 0
        }

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or update.effective_user.username or "Гравець"
    init_user(users, user_id, username)
    save_data(USERS_FILE, users)
    await update.message.reply_text(f"Привіт, {username}! Ласкаво просимо в бота. Використовуй /help для списку команд.")

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📜 *Список команд:*\n"
        "/start - Запуск бота\n"
        "/help - Список команд\n"
        "/profile - 👤 Показати профіль\n"
        "/daily - 🎁 Отримати щоденний бонус\n"
        "/feed - 🍖 Погодувати Ржомбу (отримати монети, енергію, XP)\n"
        "/createguild [назва] - 🏰 Створити гільдію (1000 монет)\n"
        "/joinguild [назва] - 🤝 Вступити до гільдії\n"
        "/leaveguild - 🚪 Вийти з гільдії\n"
        "/guild - 🛡️ Показати інформацію про гільдію\n"
        "/guildtop - 🏆 Топ гільдій\n"
        "/quests - 📜 Показати квести\n"
        "/completequest - ✅ Виконати активний квест\n"
        "/duel - ⚔️ Почати дуель (планується)\n"
        "/shop - 🛒 Магазин (планується)\n"
        "/achievements - 🏅 Досягнення (скоро)"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# Команда /profile
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return
    user = users[user_id]
    text = (
        f"👤 *Профіль {user['username']}:*\n"
        f"💰 Монети: {user['coins']}\n"
        f"⭐ XP: {user['xp']}\n"
        f"⚡ Енергія: {user['energy']}/{MAX_ENERGY}\n"
        f"🏰 Гільдія: {user['guild'] or 'немає'}\n"
        f"🐉 Ржомба рівень: {user['rzhomb']}"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# Команда /daily
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return
    user = users[user_id]
    now = time.time()
    last_daily = user.get('last_daily', 0)
    if now - last_daily < 86400:
        await update.message.reply_text("⌛ Щоденний бонус уже отримано. Спробуй пізніше.")
        return

    bonus_coins = 100
    user['coins'] += bonus_coins
    user['last_daily'] = now
    save_data(USERS_FILE, users)
    await update.message.reply_text(f"🎉 Ти отримав щоденний бонус: +{bonus_coins} монет!")

# Команда /feed
async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return

    user = users[user_id]
    update_energy(user)
    now = time.time()

    feed_amount = FEED_COINS_BASE + (user['rzhomb'] * 5)

    user['coins'] += feed_amount
    user['energy'] = min(MAX_ENERGY, user.get('energy', 0) + 10)  # +10 енергії
    user['xp'] += XP_PER_FEED
    user['last_feed'] = now

    save_data(USERS_FILE, users)

    await update.message.reply_text(
        f"🍖 Ти погодував Ржомбу і отримав {feed_amount} монет! +{XP_PER_FEED} XP, +10 енергії.\n"
        f"💰 Монет зараз: {user['coins']}, ⚡ Енергія: {user['energy']}/{MAX_ENERGY}."
    )

# Команда /createguild
async def create_guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    guilds = load_data(GUILDS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return

    user = users[user_id]

    if user['guild'] is not None:
        await update.message.reply_text("❌ Ти вже в гільдії.")
        return

    if user['coins'] < GUILD_CREATION_COST:
        await update.message.reply_text(f"❌ Для створення гільдії потрібно {GUILD_CREATION_COST} монет.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Вкажи назву гільдії: /createguild Назва")
        return

    guild_name = " ".join(args).strip()

    if guild_name in guilds:
        await update.message.reply_text("❌ Гільдія з такою назвою вже існує.")
        return

    guilds[guild_name] = {
        'owner': user_id,
        'members': [user_id],
        'level': 1,
        'xp': 0,
        'closed': False,
        'join_requests': []
    }

    user['guild'] = guild_name
    user['coins'] -= GUILD_CREATION_COST

    save_data(USERS_FILE, users)
    save_data(GUILDS_FILE, guilds)

    await update.message.reply_text(f"🏰 Гільдія '{guild_name}' створена! Віднято {GUILD_CREATION_COST} монет.")

# Тут додай інші команди, наприклад /joinguild, /leaveguild, /guild, /guildtop, /quests, /completequest, /duel, /shop, /achievements...

async def joinguild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Реалізація при потребі
    await update.message.reply_text("🤝 Функція приєднання до гільдії ще в розробці.")

async def leaveguild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Реалізація при потребі
    await update.message.reply_text("🚪 Функція виходу з гільдії ще в розробці.")

async def guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Реалізація при потребі
    await update.message.reply_text("🛡️ Інформація про гільдію буде тут пізніше.")

async def guildtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 Топ гільдій скоро з'явиться!")

async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 Список квестів скоро буде.")

async def completequest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Виконання квесту в розробці.")

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚔️ Дуелі скоро будуть доступні.")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛒 Магазин скоро відкриється.")

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏅 Досягнення в розробці.")

# Головна функція запуску бота
def main():
    app = ApplicationBuilder().token("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("feed", feed))
    app.add_handler(CommandHandler("createguild", create_guild))
    app.add_handler(CommandHandler("joinguild", joinguild))
    app.add_handler(CommandHandler("leaveguild", leaveguild))
    app.add_handler(CommandHandler("guild", guild))
    app.add_handler(CommandHandler("guildtop", guildtop))
    app.add_handler(CommandHandler("quests", quests))
    app.add_handler(CommandHandler("completequest", completequest))
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("achievements", achievements))

    print("Бот запущено...")
    app.run_polling()

if __name__ == '__main__':
    main()
