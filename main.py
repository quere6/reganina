import json
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

users = {}
guilds = {}

def load_data():
    global users, guilds
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = {}

    try:
        with open("guilds.json", "r") as f:
            guilds = json.load(f)
    except FileNotFoundError:
        guilds = {}

def save_data():
    with open("users.json", "w") as f:
        json.dump(users, f)
    with open("guilds.json", "w") as f:
        json.dump(guilds, f)

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            "name": "",
            "guild": None,
            "balance": 100,
            "inventory": [],
            "energy": 100,
            "quests": [],
            "achievements": [],
            "attack": 10,
        }
    return users[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    user["name"] = update.effective_user.first_name
    save_data()
    await update.message.reply_text(f"Привіт, {user['name']}! Твоя ржомба створена.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/profile - Показати профіль",
        "/daily - Отримати щоденну нагороду",
        "/feed - Погодувати ржомбу",
        "/createguild [назва] - Створити гільдію",
        "/joinguild [назва] - Приєднатись до гільдії",
        "/leaveguild - Покинути гільдію",
        "/guild - Інформація про гільдію",
        "/guildtop - Топ гільдій",
        "/quests - Поточні квести",
        "/completequest - Завершити квест",
        "/duel [@юзернейм] - Викликати на дуель",
        "/shop - Магазин",
        "/achievements - Досягнення",
    ]
    await update.message.reply_text("\n".join(commands))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    msg = f"""Профіль {user['name']}:
Баланс: {user['balance']}
Гільдія: {user['guild']}
Інвентар: {', '.join(user['inventory']) or 'порожньо'}
Енергія: {user['energy']}
Атака: {user['attack']}
"""
    await update.message.reply_text(msg)

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    reward = 50
    user["balance"] += reward
    save_data()
    await update.message.reply_text(f"Ти отримав {reward} монет!")

async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["energy"] < 100:
        user["energy"] = 100
        save_data()
        await update.message.reply_text("Твоя ржомба наїлась і повна енергії!")
    else:
        await update.message.reply_text("Ржомба вже сита!")

async def create_guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["guild"]:
        await update.message.reply_text("Ти вже в гільдії.")
        return
    name = " ".join(context.args)
    if not name:
        await update.message.reply_text("Вкажи назву гільдії.")
        return
    if name in guilds:
        await update.message.reply_text("Така гільдія вже існує.")
        return
    guilds[name] = {"members": [update.effective_user.id], "level": 1}
    user["guild"] = name
    save_data()
    await update.message.reply_text(f"Гільдія '{name}' створена!")

async def joinguild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["guild"]:
        await update.message.reply_text("Ти вже в гільдії.")
        return
    name = " ".join(context.args)
    if name not in guilds:
        await update.message.reply_text("Такої гільдії не існує.")
        return
    guilds[name]["members"].append(update.effective_user.id)
    user["guild"] = name
    save_data()
    await update.message.reply_text(f"Ти приєднався до '{name}'.")

async def leaveguild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user["guild"]:
        await update.message.reply_text("Ти не в гільдії.")
        return
    name = user["guild"]
    guilds[name]["members"].remove(update.effective_user.id)
    if not guilds[name]["members"]:
        del guilds[name]
    user["guild"] = None
    save_data()
    await update.message.reply_text(f"Ти покинув '{name}'.")

async def guild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user["guild"]:
        await update.message.reply_text("Ти не в гільдії.")
        return
    g = guilds[user["guild"]]
    await update.message.reply_text(f"Гільдія '{user['guild']}'\nРівень: {g['level']}\nУчасники: {len(g['members'])}")

async def guildtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_guilds = sorted(guilds.items(), key=lambda x: x[1]["level"], reverse=True)
    msg = "Топ гільдій:\n"
    for i, (name, data) in enumerate(sorted_guilds[:5], start=1):
        msg += f"{i}. {name} (Рівень {data['level']})\n"
    await update.message.reply_text(msg)

async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user["quests"]:
        quest = {"name": "Переможи жабу", "reward": 30}
        user["quests"].append(quest)
        save_data()
    q = user["quests"][0]
    await update.message.reply_text(f"Твій квест: {q['name']} (+{q['reward']} монет)")

async def completequest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user["quests"]:
        await update.message.reply_text("У тебе немає активного квесту.")
        return
    reward = user["quests"][0]["reward"]
    user["balance"] += reward
    user["quests"] = []
    save_data()
    await update.message.reply_text(f"Квест виконано! +{reward} монет.")

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not context.args or not context.args[0].startswith("@"):
        await update.message.reply_text("Вкажи @юзернейм противника.")
        return
    opponent_username = context.args[0][1:]
    # Проста заглушка — у реальності треба мапити username на user_id
    await update.message.reply_text(f"Ти викликав @{opponent_username} на дуель. Але поки що це лише декоративно.")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = {
        "меч": {"cost": 50, "attack": 5},
        "щит": {"cost": 40, "attack": 2},
    }
    msg = "Магазин:\n"
    for name, data in items.items():
        msg += f"{name.title()} - {data['cost']} монет (атака +{data['attack']})\n"
    await update.message.reply_text(msg)

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user["achievements"]:
        user["achievements"].append("Перший запуск!")
        save_data()
    await update.message.reply_text(f"Твої досягнення: {', '.join(user['achievements'])}")

def main():
    load_data()
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
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("achievements", achievements))

    print("Бот запущено...")
    app.run_polling()

if __name__ == '__main__':
    main()
