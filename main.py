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
            'active_quest': None
        }

# Команди

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Список команд:\n"
        "/help - Список команд\n"
        "/profile - Показати профіль\n"
        "/daily - Отримати щоденний бонус\n"
        "/feed - Погодувати Ржомбу (відновлення енергії, монети, XP)\n"
        "/createguild [назва] - Створити гільдію (1000 монет)\n"
        "/joinguild [назва] - Вступити до гільдії\n"
        "/leaveguild - Вийти з гільдії\n"
        "/guild - Показати інформацію про гільдію\n"
        "/guildtop - Топ гільдій\n"
        "/quests - Показати квести\n"
        "/completequest - Виконати активний квест\n"
        "/duel - Почати дуель (планується)\n"
        "/shop - Магазин (планується)\n"
        "/achievements - Досягнення (скоро)"
    )
    await update.message.reply_text(text)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return
    user = users[user_id]
    text = (
        f"Профіль {user['username']}:\n"
        f"Монети: {user['coins']}\n"
        f"XP: {user['xp']}\n"
        f"Енергія: {user['energy']}/{MAX_ENERGY}\n"
        f"Гільдія: {user['guild'] or 'немає'}\n"
        f"Ржомба рівень: {user['rzhomb']}"
    )
    await update.message.reply_text(text)

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Приклад простої реалізації щоденного бонусу
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    now = time.time()
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return
    user = users[user_id]

    last_daily = user.get('last_daily', 0)
    if now - last_daily < 86400:  # 24 години
        await update.message.reply_text("Щоденний бонус уже отримано. Спробуй пізніше.")
        return

    bonus_coins = 100
    user['coins'] += bonus_coins
    user['last_daily'] = now

    save_data(USERS_FILE, users)
    await update.message.reply_text(f"Ти отримав щоденний бонус: {bonus_coins} монет!")

async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return

    user = users[user_id]
    update_energy(user)
    now = time.time()

    feed_cost = FEED_COINS_BASE + (user['rzhomb'] * 5)

    if user['coins'] < feed_cost:
        await update.message.reply_text(f"У тебе недостатньо монет. Потрібно {feed_cost}.")
        return

    # Тепер енергія додається, а не зменшується
    user['coins'] -= feed_cost
    user['energy'] = min(MAX_ENERGY, user.get('energy', 0) + 10)  # +10 енергії
    user['xp'] += XP_PER_FEED
    user['last_feed'] = now

    save_data(USERS_FILE, users)

    await update.message.reply_text(
        f"Ти погодував ржомбу за {feed_cost} монет. Отримано +{XP_PER_FEED} XP, +10 енергії. "
        f"Монет залишилось: {user['coins']}, енергія: {user['energy']}/{MAX_ENERGY}."
    )

async def create_guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    guilds = load_data(GUILDS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return

    user = users[user_id]

    if user['guild'] is not None:
        await update.message.reply_text("Ти вже в гільдії.")
        return

    if user['coins'] < GUILD_CREATION_COST:
        await update.message.reply_text(f"Для створення гільдії потрібно {GUILD_CREATION_COST} монет.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Вкажи назву гільдії: /createguild Назва")
        return

    guild_name = " ".join(args).strip()

    if guild_name in guilds:
        await update.message.reply_text("Гільдія з такою назвою вже існує.")
        return

    guilds[guild_name] = {
        'owner': user_id,
        'members': [user_id],
        'level': 1,
        'xp': 0
    }

    user['guild'] = guild_name
    user['coins'] -= GUILD_CREATION_COST

    save_data(USERS_FILE, users)
    save_data(GUILDS_FILE, guilds)

    await update.message.reply_text(f"Гільдія '{guild_name}' створена! Віднято {GUILD_CREATION_COST} монет.")

async def join_guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    guilds = load_data(GUILDS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return
    user = users[user_id]
    if user['guild'] is not None:
        await update.message.reply_text("Ти вже в гільдії.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Вкажи назву гільдії: /joinguild Назва")
        return
    guild_name = " ".join(args).strip()
    if guild_name not in guilds:
        await update.message.reply_text("Такої гільдії не існує.")
        return
    guilds[guild_name]['members'].append(user_id)
    user['guild'] = guild_name
    save_data(USERS_FILE, users)
    save_data(GUILDS_FILE, guilds)
    await update.message.reply_text(f"Ти вступив до гільдії '{guild_name}'.")

async def leave_guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    guilds = load_data(GUILDS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return
    user = users[user_id]
    guild_name = user.get('guild')
    if not guild_name:
        await update.message.reply_text("Ти не в гільдії.")
        return
    if guild_name in guilds:
        guild = guilds[guild_name]
        if user_id in guild['members']:
            guild['members'].remove(user_id)
            # Якщо це був власник, можна додати логіку передачі власності або видалення гільдії
            if guild['owner'] == user_id:
                if guild['members']:
                    guild['owner'] = guild['members'][0]
                    await update.message.reply_text(f"Ти вийшов з гільдії. Власність передана іншому учаснику.")
                else:
                    del guilds[guild_name]
                    await update.message.reply_text(f"Ти вийшов, гільдія розпущена через відсутність учасників.")
            else:
                await update.message.reply_text("Ти вийшов з гільдії.")
        else:
            await update.message.reply_text("Тебе немає в списку учасників гільдії.")
    else:
        await update.message.reply_text("Гільдія не знайдена.")
    user['guild'] = None
    save_data(USERS_FILE, users)
    save_data(GUILDS_FILE, guilds)

async def guild_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    guilds = load_data(GUILDS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return
    user = users[user_id]
    guild_name = user.get('guild')
    if not guild_name:
        await update.message.reply_text("Ти не в гільдії.")
        return
    guild = guilds.get(guild_name)
    if not guild:
        await update.message.reply_text("Гільдія не знайдена.")
        return
    text = (
        f"Гільдія: {guild_name}\n"
        f"Власник: {guild['owner']}\n"
        f"Рівень: {guild['level']}\n"
        f"XP: {guild['xp']}\n"
        f"Кількість учасників: {len(guild['members'])}"
    )
    await update.message.reply_text(text)

async def guild_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guilds = load_data(GUILDS_FILE)
    if not guilds:
        await update.message.reply_text("Гільдії відсутні.")
        return
    sorted_guilds = sorted(guilds.items(), key=lambda x: x[1].get('xp', 0), reverse=True)[:10]
    text = "Топ гільдій за XP:\n"
    for i, (name, data) in enumerate(sorted_guilds, start=1):
        text += f"{i}. {name} - Рівень: {data.get('level', 1)}, XP: {data.get('xp', 0)}\n"
    await update.message.reply_text(text)

async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Заглушка
    await update.message.reply_text("Показати квести - скоро реалізуємо.")

async def complete_quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Заглушка
    await update.message.reply_text("Виконати активний квест - скоро реалізуємо.")

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Почати дуель - планується.")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Магазин - планується.")

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Досягнення - скоро.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    init_user(users, user_id, username)
    save_data(USERS_FILE, users)

    await update.message.reply_text(
        f"Привіт, {username}! Ти почав гру. У тебе {users[user_id]['coins']} монет та {users[user_id]['xp']} XP."
    )

if __name__ == '__main__':
    TOKEN = '7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig'

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("feed", feed))
    app.add_handler(CommandHandler("createguild", create_guild))
    app.add_handler(CommandHandler("joinguild", join_guild))
    app.add_handler(CommandHandler("leaveguild", leave_guild))
    app.add_handler(CommandHandler("guild", guild_info))
    app.add_handler(CommandHandler("guildtop", guild_top))
    app.add_handler(CommandHandler("quests", quests))
    app.add_handler(CommandHandler("completequest", complete_quest))
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("achievements", achievements))

    print("Бот запущено")
    app.run_polling()
