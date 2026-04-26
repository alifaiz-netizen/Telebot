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
        "support": {},
        "giveaway": {"active": False, "limit": 0, "users": []},
        "rewards": [
            {"name": "🔥 Smooth Config", "weight": 60, "limit": 999, "won": 0},
            {"name": "💎 Paid File", "weight": 30, "limit": 50, "won": 0},
            {"name": "👑 VIP Access", "weight": 10, "limit": 10, "won": 0}
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

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("💬 Support", callback_data="support")]
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

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    get_user(uid)
    update.message.reply_text("🔥 Welcome to Reward Bot", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # ================= OPEN BOX =================
    if q.data == "open":

        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys")
            return

        user["keys"] -= 1
        save()

        reward = pick_reward()

        if not reward:
            q.edit_message_text("❌ Rewards finished")
            return

        reward["won"] += 1
        save()

        # CHANNEL WINNER POST
        if CHANNEL_ID:
            context.bot.send_message(
                CHANNEL_ID,
                f"🎉 WINNER\nUser: {uid}\nPrize: {reward['name']}"
            )

        context.bot.send_message(uid, f"🎁 You got: {reward['name']}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 Invite Link:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        txt = "\n".join([
            f"{r['name']} ({r['won']}/{r['limit']})"
            for r in data["rewards"]
        ])
        q.edit_message_text(txt, reply_markup=menu())

    elif q.data == "support":
        admin_state[uid] = "support"
        q.edit_message_text("💬 Send your message to admin:")
        return

    # ================= ADMIN PANEL =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "admin":
            q.edit_message_text(
                "🛠 ADMIN PANEL",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                    [InlineKeyboardButton("🎁 Rewards", callback_data="a_rewards")],
                    [InlineKeyboardButton("➕ Add Reward", callback_data="a_add")],
                    [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                    [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                    [InlineKeyboardButton("🎁 Giveaway", callback_data="a_give")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ])
            )

        elif q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")

        elif q.data == "a_rewards":
            txt = "\n".join([
                f"{r['name']} ({r['won']}/{r['limit']})"
                for r in data["rewards"]
            ])
            q.edit_message_text(txt)

        elif q.data == "a_add":
            admin_state[ADMIN_ID] = "add"
            q.edit_message_text("Send: name weight limit")

        elif q.data == "a_remove":
            admin_state[ADMIN_ID] = "remove"
            q.edit_message_text("Send reward name")

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

    # ================= USER SUPPORT =================
    if admin_state.get(uid) == "support":
        data["support"][uid] = msg
        save()

        context.bot.send_message(
            ADMIN_ID,
            f"💬 SUPPORT\nUser: {uid}\nMessage: {msg}\n\nReply:\n/reply {uid} message"
        )

        update.message.reply_text("✅ Sent to admin")
        admin_state.pop(uid)
        return

    # ================= ADMIN ONLY =================
    if uid != str(ADMIN_ID):
        return

    state = admin_state.get(uid)

    if state == "add":
        name, weight, limit = msg.split()
        data["rewards"].append({
            "name": name,
            "weight": int(weight),
            "limit": int(limit),
            "won": 0
        })
        save()
        update.message.reply_text("✅ Added")

    elif state == "remove":
        data["rewards"] = [r for r in data["rewards"] if r["name"] != msg]
        save()
        update.message.reply_text("❌ Removed")

    elif state == "keys":
        u, a = msg.split()
        get_user(u)["keys"] += int(a)
        save()
        update.message.reply_text("🔑 Added")

    elif state == "give":
        data["giveaway"] = {"active": True, "limit": int(msg), "users": []}
        save()
        update.message.reply_text("🎁 Giveaway started")

    admin_state.pop(uid, None)

# ================= ADMIN REPLY =================
def reply(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = context.args[0]
        message = " ".join(context.args[1:])

        context.bot.send_message(user_id, f"📩 Admin Reply:\n{message}")
        update.message.reply_text("✅ Sent")

    except:
        update.message.reply_text("❌ /reply user_id message")

# ================= ADMIN ENTRY =================
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
    dp.add_handler(CommandHandler("reply", reply))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("admin", "Admin panel"),
        BotCommand("reply", "Reply to user")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
