import os
import json
import random
import time
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL = "@RITIK_GAMING_OG"

DATA_FILE = "data.json"

# ---------------- DATA ----------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "rewards": ["🔥 Smooth Config", "💎 Paid File", "👑 VIP Access"],
        "referrals": {},
        "vip_tokens": {},
        "config_queue": [],
        "vip_queue": []
    }

admin_state = {}
cooldown = {}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}
    return data["users"][uid]

# ---------------- SPAM PROTECTION ----------------
def is_spam(uid):
    now = time.time()
    if uid in cooldown and now - cooldown[uid] < 2:
        return True
    cooldown[uid] = now
    return False

# ---------------- LOADING ----------------
def loading(context, chat_id, msg_id, text):
    steps = ["🟦░░░░ 20%", "🟦🟦🟦░ 50%", "🟦🟦🟦🟦🟦 80%", "🟦🟦🟦🟦🟦🟦 100%"]
    for s in steps:
        context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"⏳ Loading...\n{s}")
        time.sleep(0.3)
    context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text)

# ---------------- START ----------------
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)

    try:
        update.message.delete()
    except:
        pass

    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}

    # referral
    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            data["referrals"][uid] = ref
            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
            save()

    keyboard = [
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Refer", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("💰 Discounts", callback_data="discounts")],
        [InlineKeyboardButton("⏳ Daily", callback_data="daily")]
    ]

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="🔥 MysticDropZone Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- BUTTONS ----------------
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)

    if is_spam(uid):
        q.answer("⏳ Slow down!", show_alert=True)
        return

    user = get_user(uid)

    # OPEN BOX
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys")
            return

        user["keys"] -= 1
        save()

        msg = q.message
        loading(context, msg.chat_id, msg.message_id, "🎉 Opened!")

        reward = random.choice(data["rewards"])

        # VIP token system
        if "VIP" in reward:
            token = str(uuid.uuid4())[:8]
            data["vip_tokens"][token] = {"user": uid, "used": False}
            save()

            link = f"https://t.me/{context.bot.username}?start=vip_{token}"

            context.bot.send_message(uid, f"👑 VIP LINK:\n{link}")

        if "VIP" in reward:
            data["vip_queue"].append(uid)
        if "Config" in reward:
            data["config_queue"].append(uid)

        save()

        context.bot.send_message(uid, f"🎁 {reward}")
        context.bot.send_message(ADMIN_ID, f"🏆 WINNER: {uid} → {reward}")

    # KEYS
    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}")

    # REFER
    elif q.data == "refer":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        q.edit_message_text(f"🔗 {link}")

    # REWARDS
    elif q.data == "rewards":
        q.edit_message_text("\n".join(data["rewards"]))

    # DAILY
    elif q.data == "daily":
        q.edit_message_text("⏳ Coming Soon")

    # LEADERBOARD
    elif q.data == "leaderboard":
        top = sorted(data["users"].items(), key=lambda x: x[1]["keys"], reverse=True)[:10]
        text = "🏆 Leaderboard\n\n"
        for i, (u, v) in enumerate(top, 1):
            text += f"{i}. {u} - {v['keys']} 🔑\n"
        q.edit_message_text(text)

    # DISCOUNTS
    elif q.data == "discounts":
        q.edit_message_text("💰 No active discounts")

# ---------------- VIP TOKEN CHECK ----------------
def vip_start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)

    if context.args and context.args[0].startswith("vip_"):
        token = context.args[0].replace("vip_", "")

        if token not in data["vip_tokens"]:
            update.message.reply_text("❌ Invalid link")
            return

        entry = data["vip_tokens"][token]

        if entry["used"]:
            update.message.reply_text("❌ Expired")
            return

        if str(entry["user"]) != uid:
            update.message.reply_text("❌ Not your link")
            return

        entry["used"] = True
        save()

        update.message.reply_text("👑 VIP ACCESS GRANTED")

# ---------------- ADMIN ----------------
def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("👥 Users", callback_data="a_users")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="a_rewards")]
    ]

    update.message.reply_text("🛠 Admin", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- MAIN ----------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))

    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(CommandHandler("start", vip_start))

    updater.bot.set_my_commands([
        BotCommand("start", "Open bot"),
        BotCommand("admin", "Admin panel")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
