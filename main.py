import json
import time
from telegram import Update, BotCommand
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
    energy_gain = int(elapsed // 60)  # 1 енергія за 1 хвилину, наприклад
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

# Команда старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    init_user(users, user_id, username)
    save_data(USERS_FILE, users)

    await update.message.reply_text(
        f"Привіт, {username}! Ти почав гру. У тебе {users[user_id]['coins']} монет та {users[user_id]['xp']} XP."
    )

# Команда годування
async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("Спершу використай /start")
        return

    user = users[user_id]
    update_energy(user)
    now = time.time()

    # Перевірка на енергію
    if user['energy'] < 10:
        await update.message.reply_text("У тебе замало енергії, щоб погодувати ржомбу.")
        return

    # Вартість годування залежить від рівня ржомби
    feed_cost = FEED_COINS_BASE + (user['rzhomb'] * 5)

    if user['coins'] < feed_cost:
        await update.message.reply_text(f"У тебе недостатньо монет. Потрібно {feed_cost}.")
        return

    # Зарахування годування
    user['coins'] -= feed_cost
    user['energy'] -= 10
    user['xp'] += XP_PER_FEED
    user['last_feed'] = now

    save_data(USERS_FILE, users)

    await update.message.reply_text(
        f"Ти погодував ржомбу за {feed_cost} монет. Отримано +{XP_PER_FEED} XP. Монет залишилось: {user['coins']}."
    )

# Команда створення гільдії
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

    # Назва гільдії береться з аргументів команди
    args = context.args
    if not args:
        await update.message.reply_text("Вкажи назву гільдії: /createguild Назва")
        return

    guild_name = " ".join(args).strip()

    if guild_name in guilds:
        await update.message.reply_text("Гільдія з такою назвою вже існує.")
        return

    # Створення гільдії
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

# Запуск бота
if __name__ == '__main__':
    import os
    from telegram.ext import Application

    TOKEN = os.getenv('7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig')
    if not TOKEN:
        print("Встанови змінну середовища BOT_TOKEN з токеном бота")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("feed", feed))
    app.add_handler(CommandHandler("createguild", create_guild))

    print("Бот запущено")
    app.run_polling()
