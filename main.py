from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import json
import time
import random

USERS_FILE = 'users.json'
GUILDS_FILE = 'guilds.json'

MAX_ENERGY = 100
FEED_COINS_BASE = 25
XP_PER_FEED = 10
GUILD_CREATION_COST = 1000
MAX_GUILD_MEMBERS = 20

# Магазин (назва предмета : {ціна, атака})
SHOP_ITEMS = {
    "меч": {"price": 500, "attack": 5},
    "сабля": {"price": 800, "attack": 8},
    "арбалет": {"price": 1200, "attack": 12},
    "щит": {"price": 700, "attack": 0},  # для майбутнього захисту
}

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
            'last_daily': 0,
            'inventory': {},  # предмети гравця
            'attack': 1  # базова атака
        }

# --- твої існуючі команди (start, help, profile, daily, feed, create_guild) ---

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return

    user = users[user_id]
    text = "🛒 *Магазин зброї:*\n"
    for item, info in SHOP_ITEMS.items():
        text += f"{item.capitalize()}: {info['price']} монет, атака +{info['attack']}\n"
    text += "\nЩоб купити: /buy [назва предмета]"
    await update.message.reply_text(text, parse_mode='Markdown')

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)
    if user_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return

    user = users[user_id]
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Вкажи назву предмета для покупки: /buy [назва]")
        return

    item_name = args[0].lower()
    if item_name not in SHOP_ITEMS:
        await update.message.reply_text("❌ Такого предмета немає в магазині.")
        return

    item = SHOP_ITEMS[item_name]
    if user['coins'] < item['price']:
        await update.message.reply_text("❌ У тебе недостатньо монет.")
        return

    # Купівля предмета
    user['coins'] -= item['price']
    user['inventory'][item_name] = user['inventory'].get(item_name, 0) + 1
    user['attack'] += item['attack']

    save_data(USERS_FILE, users)
    await update.message.reply_text(f"✅ Ти купив {item_name}! Твоя атака тепер {user['attack']}.")

# Дуельна команда (покликання на дуель, підтвердження, і бій)
duel_requests = {}  # user_id: opponent_id

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    challenger_id = str(update.effective_user.id)
    if challenger_id not in users:
        await update.message.reply_text("❗ Спершу використай /start")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Вкажи ID опонента: /duel [ID гравця]")
        return

    opponent_id = args[0]
    if opponent_id == challenger_id:
        await update.message.reply_text("❌ Не можна викликати себе на дуель.")
        return

    if opponent_id not in users:
        await update.message.reply_text("❌ Опонент не знайдений.")
        return

    if challenger_id in duel_requests or opponent_id in duel_requests.values():
        await update.message.reply_text("⌛ Хтось із вас вже у процесі дуелі.")
        return

    duel_requests[challenger_id] = opponent_id
    await update.message.reply_text(f"⚔️ Ти викликав {users[opponent_id]['username']} на дуель! Чекаємо підтвердження...")

    # Відправляємо повідомлення опоненту з кнопкою прийняття дуелі (спрощено)
    # Для телеграму з кнопками потрібен CallbackQueryHandler, але для спрощення тут просто текст
    # Користувач опонент має написати /acceptduel [challenger_id] для підтвердження

async def acceptduel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    opponent_id = str(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Вкажи ID того, хто тебе викликав: /acceptduel [ID]")
        return

    challenger_id = args[0]
    if challenger_id not in duel_requests or duel_requests[challenger_id] != opponent_id:
        await update.message.reply_text("❌ Немає запрошення на дуель від цього гравця.")
        return

    # Проведення дуелі
    challenger = users[challenger_id]
    opponent = users[opponent_id]

    # Просто порівнюємо атаку + випадковий фактор
    challenger_power = challenger.get('attack', 1) + random.randint(0, 5)
    opponent_power = opponent.get('attack', 1) + random.randint(0, 5)

    if challenger_power > opponent_power:
        winner_id, loser_id = challenger_id, opponent_id
    elif opponent_power > challenger_power:
        winner_id, loser_id = opponent_id, challenger_id
    else:
        winner_id = loser_id = None  # нічиї

    if winner_id:
        users[winner_id]['coins'] += 100
        users[loser_id]['coins'] = max(0, users[loser_id]['coins'] - 50)
        result_text = (f"🏆 Виграв {users[winner_id]['username']}!\n"
                       f"Виграш: +100 монет\n"
                       f"Програш: -50 монет")
    else:
        result_text = "🤝 Дуель закінчилась нічиєю!"

    # Видаляємо запит
    duel_requests.pop(challenger_id, None)

    save_data(USERS_FILE, users)
    await update.message.reply_text(result_text)

# --- реєстрація хендлерів ---

def main():
    app = ApplicationBuilder().token("ТВОЙ_ТОКЕН").build()

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
    app.add_handler(CommandHandler("acceptduel", acceptduel))  # підтвердження дуелі
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("achievements", achievements))

    print("Бот запущено...")
    app.run_polling()

if __name__ == '__main__':
    main()
