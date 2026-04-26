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

# ================= LOAD =================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "cooldowns": {},
        "rewards": [
            {"name": "🔥 Smooth Config", "weight": 60, "limit": 999, "won": 0},
            {"name": "💎 Paid File", "weight": 30, "limit": 50, "won": 0},
            {"name": "👑 VIP Access", "weight": 10, "limit": 10, "won": 0}
        ],
        "giveaway": {"active": False, "limit": 0, "users": []},
        "admin_messages": {}
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

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 My Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("💬 Message Admin", callback_data="msg")]
    ])

# ================= REWARD ENGINE =================
def pick_reward():
    available = [r for r in data["rewards"] if r["won"] < r["limit"]]
    if not available:
        return None

    total = sum(r["weight"] for r in available)
    r = random.randint(1, total)

    upto = 0
    for reward in available:
        upto += reward["weight"]
        if upto >= r:
            return reward

# ================= SPAM =================
def is_spam(uid):
    now = time.time()
    if uid in data["cooldowns"] and now - data["cooldowns"][uid] < 3:
        return True
    data["cooldowns"][uid] = now
    return False

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    get_user(uid)

    update.message.reply_text("🔥 Welcome", reply_markup=menu())

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

        reward = pick_reward()

        if not reward:
            q.edit_message_text("❌ All rewards exhausted")
            return

        reward["won"] += 1
        save()

        # CHANNEL ANNOUNCE
        if CHANNEL_ID:
            context.bot.send_message(
                CHANNEL_ID,
                f"🎉 WINNER\nUser: {uid}\nPrize: {reward['name']}"
            )

        context.bot.send_message(
            ADMIN_ID,
            f"🎁 WIN ALERT\nUser: {uid}\nPrize: {reward['name']}"
        )

        context.bot.send_message(uid, f"🎉 You got: {reward['name']}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 Invite:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        txt = "\n".join(
            [f"{r['name']} ({r['won']}/{r['limit']})" for r in data["rewards"]]
        )
        q.edit_message_text(txt, reply_markup=menu())

    # ================= MESSAGE ADMIN =================
    elif q.data == "msg":
        admin_state[uid] = "msg"
        q.edit_message_text("💬 Send message to admin:")
        return

    # ================= ADMIN PANEL =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "admin":
            q.edit_message_text(
                "🛠 ADMIN PANEL",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                    [InlineKeyboardButton("🎁 Rewards", callback_data="a_rewards")],
                    [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                    [InlineKeyboardButton("🎁 Giveaway", callback_data="a_give")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ])
            )

        elif q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")

        elif q.data == "a_rewards":
            txt = "\n".join([f"{r['name']} ({r['won']}/{r['limit']})" for r in data["rewards"]])
            q.edit_message_text(txt)

        elif q.data == "a_keys":
            admin_state[ADMIN_ID] = "keys"
            q.edit_message_text("Send: user_id amount")

        elif q.data == "a_give":
            admin_state[ADMIN_ID] = "give"
            q.edit_message_text("Send giveaway limit")

        elif q.data == "back":
            q.edit_message_text("🏠 Menu", reply_markup=menu())

# ================= TEXT HANDLER =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    # USER → ADMIN MESSAGE
    if admin_state.get(uid) == "msg":
        context.bot.send_message(ADMIN_ID, f"💬 USER {uid}:\n{msg}")
        update.message.reply_text("✅ Sent to admin")
        admin_state.pop(uid)
        return

    if uid != str(ADMIN_ID):
        return

    state = admin_state.get(uid)

    if state == "keys":
        u, a = msg.split()
        get_user(u)["keys"] += int(a)
        save()
        update.message.reply_text("🔑 Added")

    elif state == "give":
        data["giveaway"]["active"] = True
        data["giveaway"]["limit"] = int(msg)
        data["giveaway"]["users"] = []
        save()
        update.message.reply_text("🎁 Giveaway started")

    admin_state.pop(uid, None)

# ================= ADMIN COMMAND =================
def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Dashboard", callback_data="admin")]
        ])
    )

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("admin", "Admin panel")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
