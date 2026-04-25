import random
import json
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

TOKEN = os.getenv("TOKEN")

DATA_FILE = "data.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

def get_user(user_id):
    if str(user_id) not in users:
        users[str(user_id)] = {"keys": 0}
    return users[str(user_id)]

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔥 Welcome to MysticDropZone!\n\n"
        "🎁 Invite → Earn Keys → Open Boxes\n\n"
        "/daily - Get key\n"
        "/keys - Check keys\n"
        "/open - Open box"
    )

def daily(update: Update, context: CallbackContext):
    user = get_user(update.message.from_user.id)
    user["keys"] += 1
    save_data()
    update.message.reply_text("🎁 +1 Key added!")

def keys(update: Update, context: CallbackContext):
    user = get_user(update.message.from_user.id)
    update.message.reply_text(f"🔑 Keys: {user['keys']}")

def open_box(update: Update, context: CallbackContext):
    user = get_user(update.message.from_user.id)

    if user["keys"] <= 0:
        update.message.reply_text("❌ No keys! Use /daily")
        return

    user["keys"] -= 1

    roll = random.randint(1, 100)

    if roll <= 50:
        reward = "🔥 Smooth Config"
    elif roll <= 80:
        reward = "⚙️ No Lag Config"
    elif roll <= 95:
        reward = "❌ Bad Luck"
    else:
        reward = "💎 VIP ACCESS!\nJoin: https://t.me/YOUR_PRIVATE_LINK"

    save_data()

    update.message.reply_text(f"🎁 Opening...\n\n{reward}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("daily", daily))
    dp.add_handler(CommandHandler("keys", keys))
    dp.add_handler(CommandHandler("open", open_box))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
