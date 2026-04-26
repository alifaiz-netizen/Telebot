import os
import json
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # @channelusername

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

# ================= FORCE JOIN =================
def is_member(bot, uid):
    if not CHANNEL_ID:
        return True
    try:
        m = bot.get_chat_member(CHANNEL_ID, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

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
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("💬 Message Admin", callback_data="msg_admin")]
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
    user = get_user(uid)

    # FORCE JOIN
    if not is_member(context.bot, uid):
        update.message.reply_text(
            "❌ Join channel to continue",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
                [InlineKeyboardButton("♻️ I Joined", callback_data="check_join")]
            ])
        )
        return

    # REFERRAL
    if context.args:
        ref = context.args[0]

        if ref != uid and uid not in data["referrals"]:
            if not is_member(context.bot, uid):
                update.message.reply_text("❌ Join channel first")
                return

            data["referrals"][uid] = ref

            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
                context.bot.send_message(ref, "🎉 +1 Key (Referral)")

            update.message.reply_text("🎉 Referral success +1 key")

    save()
    update.message.reply_text("🔥 Welcome", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # FORCE JOIN CHECK ALWAYS
    if not is_member(context.bot, uid):
        q.answer("❌ Join channel first", show_alert=True)
        return

    # SPAM CHECK (only users)
    if q.from_user.id != ADMIN_ID and is_spam(uid):
        q.answer("⚠️ Slow down bro", show_alert=True)
        return

    # ================= ADMIN PANEL OPEN =================
    if q.data == "admin":
        if q.from_user.id != ADMIN_ID:
            return

        q.edit_message_text(
            "🛠 ADMIN PANEL",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                [InlineKeyboardButton("🎁 Add Reward", callback_data="a_add")],
                [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                [InlineKeyboardButton("🎁 Giveaway", callback_data="a_give")],
                [InlineKeyboardButton("📦 Send Gift", callback_data="a_gift")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        return

    # ================= ADMIN ACTIONS =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")
            return

        if q.data == "a_add":
            admin_state[uid] = "add_reward"
            q.edit_message_text("Send: name weight")
            return

        if q.data == "a_remove":
            admin_state[uid] = "remove_reward"
            q.edit_message_text("Send reward name")
            return

        if q.data == "a_keys":
            admin_state[uid] = "add_keys"
            q.edit_message_text("Send: user_id amount")
            return

        if q.data == "a_give":
            admin_state[uid] = "giveaway"
            q.edit_message_text("Send giveaway limit")
            return

        if q.data == "a_gift":
            admin_state[uid] = "gift"
            q.edit_message_text("Send: user_id gift_text")
            return

        if q.data == "back":
            q.edit_message_text("🏠 Menu", reply_markup=menu())
            return

    # ================= USER OPEN BOX =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys")
            return

        user["keys"] -= 1
        reward = pick_reward()

        if "VIP" in reward:
            data["vip_queue"].append(uid)
            if CHANNEL_ID:
                context.bot.send_message(
                    CHANNEL_ID,
                    f"👑 NEW VIP WINNER\nUser: {uid}"
                )

        if "Config" in reward:
            data["config_queue"].append(uid)

        save()

        context.bot.send_message(uid, f"🎁 You got: {reward}")
        context.bot.send_message(ADMIN_ID, f"🎉 WINNER: {uid} → {reward}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        q.edit_message_text(f"🔗 Invite:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        q.edit_message_text("\n".join([r["name"] for r in data["rewards"]]), reply_markup=menu())

    elif q.data == "msg_admin":
        admin_state[uid] = "msg_admin"
        q.edit_message_text("💬 Send message to admin")

# ================= TEXT HANDLER =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    # USER MESSAGE TO ADMIN
    if admin_state.get(uid) == "msg_admin":
        context.bot.send_message(ADMIN_ID, f"💬 USER {uid}:\n{msg}")
        update.message.reply_text("✅ Sent")
        admin_state.pop(uid, None)
        return

    if uid != str(ADMIN_ID):
        return

    state = admin_state.get(uid)

    # ADD REWARD
    if state == "add_reward":
        name, weight = msg.split()
        data["rewards"].append({"name": name, "weight": int(weight)})
        save()

    # REMOVE REWARD
    elif state == "remove_reward":
        data["rewards"] = [r for r in data["rewards"] if r["name"] != msg]
        save()

    # ADD KEYS
    elif state == "add_keys":
        u, a = msg.split()
        get_user(u)["keys"] += int(a)
        save()

    # GIVEAWAY
    elif state == "giveaway":
        data["giveaway"] = {"active": True, "limit": int(msg), "users": []}
        save()

    # GIFT SEND
    elif state == "gift":
        u, gift = msg.split(maxsplit=1)
        context.bot.send_message(u, f"🎁 Gift from Admin:\n{gift}")

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
