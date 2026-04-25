import random
import json
import os
import time
from telegram import Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

TOKEN = os.getenv("TOKEN")

CHANNEL = "@RITIK_GAMING_OG"
ADMIN_ID = 7050657650# 🔥 replace with your ID

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

# ✅ Force join
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
            context.bot.send_message(ref, "🎉 You earned +1 key from referral!")
            save_data()

    update.message.reply_text(
        f"🔥 *Welcome to MysticDropZone!*\n\n"
        f"🎁 Invite → Earn Keys → Open Mystery Boxes\n\n"
        f"⚠️ Join channel first:\n{CHANNEL}\n\n"
        f"🎮 Commands:\n"
        f"/daily 🎁 Daily reward\n"
        f"/open 🎲 Open mystery box\n"
        f"/keys 🔑 Check keys\n"
        f"/refer 🔗 Invite friends",
        parse_mode="Markdown"
    )

# 🔑 DAILY
def daily(update: Update, context: CallbackContext):
    if not is_joined(update, context):
        update.message.reply_text(f"❌ Join channel first:\n{CHANNEL}")
        return

    user = get_user(update.message.from_user.id)
    user["keys"] += 1
    save_data()

    update.message.reply_text("🎁 *Daily Reward*\n\n🔑 +1 Key added!", parse_mode="Markdown")

# 🔑 KEYS
def keys(update: Update, context: CallbackContext):
    user = get_user(update.message.from_user.id)
    update.message.reply_text(f"🔑 *Your Keys:* {user['keys']}", parse_mode="Markdown")

# 🔗 REFER
def refer(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start={user_id}"

    update.message.reply_text(
        f"🔗 *Your Invite Link:*\n{link}\n\n🎁 Earn keys when friends join!",
        parse_mode="Markdown"
    )

# 🎁 OPEN BOX (WITH LOADING EFFECT)
def open_box(update: Update, context: CallbackContext):
    if not is_joined(update, context):
        update.message.reply_text(f"❌ Join channel first:\n{CHANNEL}")
        return

    user = get_user(update.message.from_user.id)

    if user["keys"] <= 0:
        update.message.reply_text("❌ No keys! Use /daily")
        return

    user["keys"] -= 1

    msg = update.message.reply_text("🎁 Opening your mystery box...")
    time.sleep(1.5)

    context.bot.edit_message_text(
        chat_id=msg.chat_id,
        message_id=msg.message_id,
        text="🔄 Unlocking reward..."
    )
    time.sleep(1.5)

    roll = random.randint(1, 100)

    if roll <= 60:
        reward = "🔥 *Smooth Config Unlocked!*"

    elif roll <= 90:
        reward = (
            "🎁 *CONFIG FILE WON!*\n\n"
            "⏳ Admin is busy right now.\n"
            "📦 Reward will be sent soon!"
        )
        data["config_queue"].append(update.message.from_user.id)

        context.bot.send_message(
            ADMIN_ID,
            f"📤 CONFIG WINNER!\nUser: @{update.message.from_user.username}\nQueue: {len(data['config_queue'])}"
        )

    else:
        if not data["vip_claimed"]:
            reward = (
                "💎 *VIP ACCESS WON!*\n\n"
                "⏳ Admin will send access soon!"
            )

            data["vip_claimed"] = True
            data["vip_queue"].append(update.message.from_user.id)

            context.bot.send_message(
                ADMIN_ID,
                f"💎 VIP WINNER!\nUser: @{update.message.from_user.username}"
            )

            context.bot.send_message(
                CHANNEL,
                f"🎉 NEW VIP WINNER!\n👤 @{update.message.from_user.username}\n💎 VIP ACCESS"
            )
        else:
            reward = "🎁 *Rare Config Reward!*"

    save_data()

    context.bot.edit_message_text(
        chat_id=msg.chat_id,
        message_id=msg.message_id,
        text=f"🎉 {reward}",
        parse_mode="Markdown"
    )

# 📤 ADMIN HANDLER
def handle_file(update: Update, context: CallbackContext):
    if not update.message:
        return

    if update.message.from_user.id != ADMIN_ID:
        return

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

# 🛠 ADMIN COMMANDS
def queue(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return
    update.message.reply_text(f"📊 Config: {len(data['config_queue'])}\nVIP: {len(data['vip_queue'])}")

def clear(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return
    data["config_queue"] = []
    data["vip_queue"] = []
    save_data()
    update.message.reply_text("🧹 Queues cleared!")

def addkey(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = context.args[0]
        amount = int(context.args[1])
        user = get_user(user_id)
        user["keys"] += amount
        save_data()

        update.message.reply_text(f"✅ Added {amount} keys")

        context.bot.send_message(user_id, f"🎁 You received {amount} keys!")
    except:
        update.message.reply_text("Usage: /addkey user_id amount")

# 🚀 MAIN
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("daily", daily))
    dp.add_handler(CommandHandler("keys", keys))
    dp.add_handler(CommandHandler("open", open_box))
    dp.add_handler(CommandHandler("refer", refer))
    dp.add_handler(CommandHandler("queue", queue))
    dp.add_handler(CommandHandler("clear", clear))
    dp.add_handler(CommandHandler("addkey", addkey))

    dp.add_handler(MessageHandler(Filters.all, handle_file))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("daily", "Daily reward"),
        BotCommand("open", "Open mystery box"),
        BotCommand("keys", "Check keys"),
        BotCommand("refer", "Invite friends"),
        BotCommand("queue", "Admin queue"),
        BotCommand("clear", "Admin clear"),
        BotCommand("addkey", "Admin add keys")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
