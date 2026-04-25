import random
import json
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

TOKEN = os.getenv("TOKEN")

CHANNEL = "@RITIK_GAMING_OG"   # ✅ your channel username
ADMIN_ID = 7050657650           # ❗ replace with your Telegram ID

DATA_FILE = "data.json"

# Load data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "vip_claimed": False,
        "config_queue": [],
        "vip_queue": [],
        "referrals": {}
    }

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(user_id):
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"keys": 0}
    return data["users"][str(user_id)]

# ✅ Force join check
def is_joined(update, context):
    try:
        member = context.bot.get_chat_member(CHANNEL, update.message.from_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# 🚀 START + REFERRAL
def start(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    if context.args:
        ref = context.args[0]
        if ref != user_id and user_id not in data["referrals"]:
            data["referrals"][user_id] = ref
            ref_user = get_user(ref)
            ref_user["keys"] += 1
            context.bot.send_message(ref, "🎉 +1 Key from referral!")
            save_data()

    update.message.reply_text(
        f"🔥 Welcome to MysticDropZone!\n\n"
        f"⚠️ Join channel first:\n{CHANNEL}\n\n"
        "/daily - Get key\n"
        "/keys - Check keys\n"
        "/open - Open box\n"
        "/refer - Invite friends"
    )

# 🔑 DAILY
def daily(update: Update, context: CallbackContext):
    if not is_joined(update, context):
        update.message.reply_text(f"❌ Join channel first:\n{CHANNEL}")
        return

    user = get_user(update.message.from_user.id)
    user["keys"] += 1
    save_data()

    update.message.reply_text("🎁 +1 Key added!")

# 🔑 KEYS
def keys(update: Update, context: CallbackContext):
    user = get_user(update.message.from_user.id)
    update.message.reply_text(f"🔑 Keys: {user['keys']}")

# 🔗 REFER
def refer(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start={user_id}"

    update.message.reply_text(f"🔗 Your invite link:\n{link}")

# 🎁 OPEN BOX
def open_box(update: Update, context: CallbackContext):
    if not is_joined(update, context):
        update.message.reply_text(f"❌ Join channel first:\n{CHANNEL}")
        return

    user = get_user(update.message.from_user.id)

    if user["keys"] <= 0:
        update.message.reply_text("❌ No keys! Use /daily")
        return

    user["keys"] -= 1
    roll = random.randint(1, 100)

    if roll <= 60:
        reward = "🔥 Smooth Config"

    elif roll <= 90:
        reward = (
            "🎁 You won CONFIG FILE!\n\n"
            "⏳ Admin is busy right now.\n"
            "📦 Your reward will be sent soon."
        )

        data["config_queue"].append(update.message.from_user.id)

        context.bot.send_message(
            ADMIN_ID,
            f"📤 CONFIG WINNER!\nUser: @{update.message.from_user.username}\nQueue: {len(data['config_queue'])}"
        )

    else:
        if not data["vip_claimed"]:
            reward = (
                "💎 You won VIP ACCESS!\n\n"
                "⏳ Admin is busy right now.\n"
                "🎁 VIP will be given soon."
            )

            data["vip_claimed"] = True
            data["vip_queue"].append(update.message.from_user.id)

            context.bot.send_message(
                ADMIN_ID,
                f"💎 VIP WINNER!\nUser: @{update.message.from_user.username}"
            )

            # Announcement
            context.bot.send_message(
                CHANNEL,
                f"🎉 NEW VIP WINNER!\n👤 @{update.message.from_user.username}\n💎 VIP ACCESS"
            )

        else:
            reward = "🎁 Rare Config (VIP already claimed)"

    save_data()
    update.message.reply_text(f"🎁 Opening...\n\n{reward}")

# 📤 ADMIN SEND (QUEUE SYSTEM)
def handle_file(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    # CONFIG QUEUE
    if data["config_queue"]:
        user_id = data["config_queue"].pop(0)

        context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )

        update.message.reply_text(f"✅ Config sent! Remaining: {len(data['config_queue'])}")
        save_data()
        return

    # VIP QUEUE
    if data["vip_queue"]:
        user_id = data["vip_queue"].pop(0)

        context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )

        update.message.reply_text("✅ VIP sent!")
        save_data()
        return

    update.message.reply_text("❌ No pending users")

# 🚀 MAIN
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("daily", daily))
    dp.add_handler(CommandHandler("keys", keys))
    dp.add_handler(CommandHandler("open", open_box))
    dp.add_handler(CommandHandler("refer", refer))

    dp.add_handler(MessageHandler(Filters.all, handle_file))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
