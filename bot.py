import os
import json
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

DATA_FILE = "data.json"

# ================= DATA =================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "referrals": {},
        "cooldowns": {},
        "vip_queue": [],
        "config_queue": [],
        "vip_limit": 5,
        "rewards": [
            {"name": "🔥 Smooth Config", "weight": 60},
            {"name": "💎 Paid File", "weight": 30},
            {"name": "👑 VIP Access", "weight": 10}
        ]
    }

admin_state = {}

# ================= SAVE =================
def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ================= USER =================
def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}
    return data["users"][uid]

# ================= SPAM =================
def is_spam(uid):
    now = time.time()
    last = data["cooldowns"].get(uid, 0)
    if now - last < 3:
        return True
    data["cooldowns"][uid] = now
    return False

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")]
    ])

# ================= REWARD =================
def pick_reward():
    total = sum(r["weight"] for r in data["rewards"])
    r = random.randint(1, total)

    upto = 0
    for reward in data["rewards"]:
        upto += reward["weight"]
        if upto >= r:
            return reward["name"]

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    get_user(uid)

    # referral system
    if context.args:
        ref = context.args[0]

        if ref != uid and uid not in data["referrals"]:
            data["referrals"][uid] = ref

            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
                context.bot.send_message(ref, "🎉 Someone used your link +1 key!")

            update.message.reply_text("🎉 You got +1 key!")

            save()

    update.message.reply_text("🔥 Welcome Bot", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    if is_spam(uid):
        q.edit_message_text("⚠️ Slow down")
        return

    # ================= OPEN BOX =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys")
            return

        user["keys"] -= 1
        save()

        reward = pick_reward()

        if not reward:
            q.edit_message_text("❌ No rewards")
            return

        # VIP SYSTEM
        if "VIP" in reward:
            if len(data["vip_queue"]) < data["vip_limit"]:
                data["vip_queue"].append(uid)

                if CHANNEL_ID:
                    context.bot.send_message(
                        CHANNEL_ID,
                        f"👑 VIP WINNER\nUser: {uid}"
                    )

        if "Config" in reward:
            data["config_queue"].append(uid)

        save()

        # ADMIN NOTIFY
        context.bot.send_message(
            ADMIN_ID,
            f"🎁 WIN ALERT\nUser: {uid}\nReward: {reward}"
        )

        context.bot.send_message(uid, f"🎉 You got: {reward}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 Share link:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        text = "\n".join([r["name"] for r in data["rewards"]])
        q.edit_message_text(text, reply_markup=menu())

# ================= ADMIN PANEL =================
def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Panel", callback_data="admin")]
        ])
    )

def admin_buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    if q.data == "admin":
        q.edit_message_text(
            "🛠 Admin Active"
        )

# ================= SEND PRIZE =================
def send_prize(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = context.args[0]
        prize = " ".join(context.args[1:])

        context.bot.send_message(user_id, f"🎉 PRIZE\n{prize}")

        update.message.reply_text("✅ Sent")

    except:
        update.message.reply_text("❌ /sendprize user_id prize")

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CommandHandler("sendprize", send_prize))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(CallbackQueryHandler(admin_buttons))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("admin", "Admin panel"),
        BotCommand("sendprize", "Send prize")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
