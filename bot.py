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
        "giveaway": {"active": False, "limit": 0, "users": []},
        "msg_map": {}  # user ↔ admin reply tracking
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

# ================= CHANNEL CHECK =================
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

    if CHANNEL_ID and not is_member(context.bot, uid):
        update.message.reply_text(
            "❌ Join channel first",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
                [InlineKeyboardButton("I Joined", callback_data="check_join")]
            ])
        )
        return

    # referral
    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
                context.bot.send_message(ref, "🎉 +1 Key Referral Reward!")

            data["referrals"][uid] = ref
            update.message.reply_text("🎉 You got +1 key!")

    save()
    update.message.reply_text("🔥 Welcome", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # JOIN CHECK
    if q.data == "check_join":
        if is_member(context.bot, uid):
            q.edit_message_text("✅ Verified!")
            context.bot.send_message(uid, "🏠 Main Menu", reply_markup=menu())
        else:
            q.answer("❌ Not joined", show_alert=True)
        return

    # SPAM BLOCK
    if q.from_user.id != ADMIN_ID and is_spam(uid):
        q.answer("⚠️ Slow down", show_alert=True)
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

        if CHANNEL_ID:
            context.bot.send_message(CHANNEL_ID, f"🏆 Winner: {uid} got {reward}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 {link}", reply_markup=menu())

    elif q.data == "rewards":
        q.edit_message_text("\n".join([r["name"] for r in data["rewards"]]), reply_markup=menu())

    elif q.data == "msg_admin":
        admin_state[uid] = "msg"
        q.edit_message_text("💬 Send message to admin")

    # ================= ADMIN PANEL FIX =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "admin":
            q.edit_message_text(
                "🛠 ADMIN PANEL",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Users", callback_data="a_users")],
                    [InlineKeyboardButton("Rewards", callback_data="a_rewards")],
                    [InlineKeyboardButton("Add Keys", callback_data="a_keys")],
                    [InlineKeyboardButton("Send Gift", callback_data="a_gift")],
                    [InlineKeyboardButton("Giveaway", callback_data="a_give")],
                    [InlineKeyboardButton("Back", callback_data="back")]
                ])
            )
            return

        elif q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")

        elif q.data == "a_rewards":
            q.edit_message_text("\n".join([r["name"] for r in data["rewards"]]))

        elif q.data == "a_keys":
            admin_state[uid] = "keys"
            q.edit_message_text("Send: user_id amount")

        elif q.data == "a_gift":
            admin_state[uid] = "gift"
            q.edit_message_text("Send: user_id message/file")

        elif q.data == "a_give":
            admin_state[uid] = "give"
            q.edit_message_text("Send giveaway limit")

        elif q.data == "back":
            q.edit_message_text("🏠 Menu", reply_markup=menu())

# ================= TEXT =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    # USER → ADMIN MESSAGE
    if admin_state.get(uid) == "msg":
        data["msg_map"][uid] = True
        context.bot.send_message(ADMIN_ID, f"💬 MSG FROM {uid}:\n{msg}")
        update.message.reply_text("✅ Sent")
        admin_state.pop(uid, None)
        return

    if uid != str(ADMIN_ID):
        return

    state = admin_state.get(uid)

    if state == "keys":
        u, a = msg.split()
        get_user(u)["keys"] += int(a)
        update.message.reply_text("✅ Keys added")

    elif state == "gift":
        u, *gift = msg.split()
        gift_text = " ".join(gift)
        context.bot.send_message(u, f"🎁 Gift from Admin:\n{gift_text}")
        update.message.reply_text("🎁 Gift sent")

    elif state == "give":
        data["giveaway"]["active"] = True
        data["giveaway"]["limit"] = int(msg)
        data["giveaway"]["users"] = []
        update.message.reply_text("🎉 Giveaway started")

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
