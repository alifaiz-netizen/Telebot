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
        "referrals": {},
        "cooldowns": {},
        "rewards": [
            {"name": "🔥 Smooth Config", "weight": 60},
            {"name": "💎 Paid File", "weight": 30},
            {"name": "👑 VIP Access", "weight": 10}
        ],
        "vip_queue": [],
        "config_queue": [],
        "giveaway": {"active": False, "limit": 0, "users": []}
    }

admin_state = {}
pending_send = {}

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

# ================= REWARD =================
def pick_reward():
    total = sum(r["weight"] for r in data["rewards"])
    r = random.randint(1, total)

    upto = 0
    for reward in data["rewards"]:
        upto += reward["weight"]
        if upto >= r:
            return reward["name"]

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 My Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("💬 Message Admin", callback_data="msg_admin")]
    ])

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    user = get_user(uid)

    # referral
    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            data["referrals"][uid] = ref

            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
                context.bot.send_message(ref, "🎉 +1 Key from referral!")

            update.message.reply_text("🎉 You got +1 key!")

    save()
    update.message.reply_text("🔥 Welcome Bot", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    if q.from_user.id != ADMIN_ID:
        if is_spam(uid):
            q.edit_message_text("⚠️ Slow down bro")
            return

    # ================= OPEN BOX =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys")
            return

        user["keys"] -= 1
        save()

        reward = pick_reward()

        if "VIP" in reward:
            data["vip_queue"].append(uid)

        if "Config" in reward:
            data["config_queue"].append(uid)

        save()

        context.bot.send_message(uid, f"🎁 You got: {reward}")
        context.bot.send_message(ADMIN_ID, f"🎉 WINNER: {uid} → {reward}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 Invite:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        txt = "\n".join([r["name"] for r in data["rewards"]])
        q.edit_message_text(txt, reply_markup=menu())

    elif q.data == "msg_admin":
        admin_state[uid] = "msg_admin"
        q.edit_message_text("💬 Send message to admin")

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
                    [InlineKeyboardButton("📦 Send Prize", callback_data="a_send")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ])
            )
            return

        elif q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")
            return

        elif q.data == "a_rewards":
            q.edit_message_text("\n".join([r["name"] for r in data["rewards"]]))
            return

        elif q.data == "a_add":
            admin_state[uid] = "add"
            q.edit_message_text("Send: name weight")
            return

        elif q.data == "a_remove":
            admin_state[uid] = "remove"
            q.edit_message_text("Send reward name")
            return

        elif q.data == "a_keys":
            admin_state[uid] = "keys"
            q.edit_message_text("Send: user_id amount")
            return

        elif q.data == "a_give":
            admin_state[uid] = "give"
            q.edit_message_text("Send giveaway limit")
            return

        elif q.data == "a_send":
            admin_state[uid] = "send"
            q.edit_message_text("Send user_id")
            return

        elif q.data == "back":
            q.edit_message_text("🏠 Menu", reply_markup=menu())
            return

# ================= TEXT =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    # USER MSG TO ADMIN
    if admin_state.get(uid) == "msg_admin":
        context.bot.send_message(ADMIN_ID, f"💬 MSG {uid}:\n{msg}")
        update.message.reply_text("✅ Sent")
        admin_state.pop(uid)
        return

    if uid != str(ADMIN_ID):
        return

    state = admin_state.get(uid)

    if state == "add":
        name, weight = msg.split()
        data["rewards"].append({"name": name, "weight": int(weight)})
        save()

    elif state == "remove":
        data["rewards"] = [r for r in data["rewards"] if r["name"] != msg]
        save()

    elif state == "keys":
        u, a = msg.split()
        get_user(u)["keys"] += int(a)
        save()

    elif state == "give":
        data["giveaway"] = {"active": True, "limit": int(msg), "users": []}
        save()

    elif state == "send":
        pending_send["user"] = msg
        update.message.reply_text("Now send file or text to forward")
        admin_state[uid] = "send_file"
        return

    admin_state.pop(uid, None)

# ================= FILE SEND =================
def file_handler(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)

    if uid != str(ADMIN_ID):
        return

    if admin_state.get(uid) == "send_file":
        user = pending_send.get("user")

        if update.message.document:
            context.bot.send_document(user, update.message.document.file_id)
        else:
            context.bot.send_message(user, update.message.text)

        update.message.reply_text("✅ Sent")
        admin_state.pop(uid, None)
        pending_send.clear()

# ================= ADMIN COMMAND =================
def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Panel", callback_data="admin")]
        ])
    )

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))

    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text | Filters.document, file_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("admin", "Admin panel")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
