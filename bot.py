import random
import json
import os
import time
from telegram import Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

TOKEN = os.getenv("TOKEN")

CHANNEL = "@RITIK_GAMING_OG"
PAID_CHANNEL_LINK = "https://t.me/+ZxkSDF8BQVIxOTNl"
ADMIN_ID = 7050657650  # 🔥 replace with your ID

DATA_FILE = "data.json"

# ---------------- DATA ----------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "vip_claimed": False,
        "vip_queue": [],
        "config_queue": [],
        "referrals": {}
    }

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(user_id):
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"keys": 0}
    return data["users"][str(user_id)]

# ---------------- FORCE JOIN ----------------
def is_joined(update, context):
    try:
        member = context.bot.get_chat_member(CHANNEL, update.message.from_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------------- START ----------------
def start(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    # referral system
    if context.args:
        ref = context.args[0]
        if ref != user_id and user_id not in data["referrals"]:
            data["referrals"][user_id] = ref
            ref_user = get_user(ref)
            ref_user["keys"] += 1
            context.bot.send_message(ref, "🎉 +1 Key from referral!")

    save_data()

    update.message.reply_text(
        "🔥 Welcome to MysticDropZone Bot!\n\n"
        "🎁 Invite → Earn Keys → Open Boxes\n\n"
        "Commands:\n"
        "/daily - Get reward\n"
        "/open - Open box\n"
        "/keys - Check keys\n"
        "/refer - Invite friends"
    )

# ---------------- DAILY ----------------
def daily(update: Update, context: CallbackContext):
    if not is_joined(update, context):
        update.message.reply_text(f"❌ Join first: {CHANNEL}")
        return

    user = get_user(update.message.from_user.id)
    user["keys"] += 1
    save_data()

    update.message.reply_text("🎁 +1 Key added!")

# ---------------- KEYS ----------------
def keys(update: Update, context: CallbackContext):
    user = get_user(update.message.from_user.id)
    update.message.reply_text(f"🔑 Keys: {user['keys']}")

# ---------------- REFER ----------------
def refer(update: Update, context: CallbackContext):
    uid = update.message.from_user.id
    botname = context.bot.username
    link = f"https://t.me/{botname}?start={uid}"

    update.message.reply_text(f"🔗 Invite link:\n{link}")

# ---------------- OPEN BOX ----------------
def open_box(update: Update, context: CallbackContext):
    if not is_joined(update, context):
        update.message.reply_text(f"❌ Join first: {CHANNEL}")
        return

    user = get_user(update.message.from_user.id)

    if user["keys"] <= 0:
        update.message.reply_text("❌ No keys!")
        return

    user["keys"] -= 1

    msg = update.message.reply_text("🎁 Opening box...")
    time.sleep(1.5)

    context.bot.edit_message_text("🔄 Unlocking reward...", msg.chat_id, msg.message_id)
    time.sleep(1.5)

    roll = random.randint(1, 100)

    # 💎 PAID FILE (PRIVATE CHANNEL)
    if roll <= 60:
        reward = (
            "💎 PAID FILE UNLOCKED!\n\n"
            "🔐 Access private content below:\n"
            f"{PAID_CHANNEL_LINK}\n\n"
            "⚠️ Do not share"
        )

    # 🎁 CONFIG (QUEUE)
    elif roll <= 90:
        reward = "🎁 CONFIG WON! Admin will send soon."
        data["config_queue"].append(update.message.from_user.id)

        context.bot.send_message(
            ADMIN_ID,
            f"📤 CONFIG WINNER @{update.message.from_user.username}"
        )

    # 👑 VIP
    else:
        if not data["vip_claimed"]:
            reward = "👑 VIP WON! Admin will contact you."
            data["vip_claimed"] = True
            data["vip_queue"].append(update.message.from_user.id)

            context.bot.send_message(
                ADMIN_ID,
                f"💎 VIP WINNER @{update.message.from_user.username}"
            )

            context.bot.send_message(
                CHANNEL,
                f"🎉 VIP WINNER @{update.message.from_user.username}"
            )
        else:
            reward = "🎁 Try again!"

    save_data()

    context.bot.edit_message_text(
        reward,
        msg.chat_id,
        msg.message_id
    )

# ---------------- ADMIN ADD KEYS ----------------
def addkey(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        uid = context.args[0]
        amount = int(context.args[1])

        user = get_user(uid)
        user["keys"] += amount
        save_data()

        update.message.reply_text(f"✅ Added {amount} keys")

        context.bot.send_message(uid, f"🎁 You got {amount} keys!")
    except:
        update.message.reply_text("Usage: /addkey user_id amount")

# ---------------- HANDLE QUEUE ----------------
def handle_file(update: Update, context: CallbackContext):
    if not update.message:
        return

    if update.message.from_user.id != ADMIN_ID:
        return

    if data["config_queue"]:
        uid = data["config_queue"].pop(0)

        context.bot.copy_message(uid, update.message.chat_id, update.message.message_id)

        update.message.reply_text("✅ Config sent")
        save_data()
        return

    if data["vip_queue"]:
        uid = data["vip_queue"].pop(0)

        context.bot.copy_message(uid, update.message.chat_id, update.message.message_id)

        update.message.reply_text("✅ VIP sent")
        save_data()
        return

    update.message.reply_text("❌ No queue")

# ---------------- MAIN ----------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("daily", daily))
    dp.add_handler(CommandHandler("keys", keys))
    dp.add_handler(CommandHandler("open", open_box))
    dp.add_handler(CommandHandler("refer", refer))
    dp.add_handler(CommandHandler("addkey", addkey))

    dp.add_handler(MessageHandler(Filters.all, handle_file))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("daily", "Daily reward"),
        BotCommand("open", "Open box"),
        BotCommand("keys", "Check keys"),
        BotCommand("refer", "Invite"),
        BotCommand("addkey", "Admin add keys")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
