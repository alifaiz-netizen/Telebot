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

# ================= LOAD DATA =================
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
            {"name": "💎 Paid Config", "weight": 30},
            {"name": "👑 VIP Access", "weight": 10}
        ],
        "limits": {
            "VIP Access": 1,
            "🔥 Smooth Config": 6,
            "💎 Paid Config": 6
        },
        "winners": {},
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
    if now - data["cooldowns"].get(uid, 0) < 3:
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
    for rw in data["rewards"]:
        upto += rw["weight"]
        if upto >= r:
            return rw["name"]

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    user = get_user(uid)

    if not is_member(context.bot, uid):
        update.message.reply_text(
            "❌ Join channel first",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
                [InlineKeyboardButton("♻️ I Joined", callback_data="check_join")]
            ])
        )
        return

    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            if is_member(context.bot, uid):
                data["referrals"][uid] = ref
                if ref in data["users"]:
                    data["users"][ref]["keys"] += 1
                    context.bot.send_message(ref, "🎉 Referral +1 key")
                update.message.reply_text("🎉 Referral success")

    save()
    update.message.reply_text("🔥 Welcome", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # JOIN CHECK FIXED
    if q.data == "check_join":
        if is_member(context.bot, uid):
            q.edit_message_text("✅ Verified!")
            context.bot.send_message(uid, "🏠 Menu", reply_markup=menu())
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
        reward = pick_reward()

        # LIMIT CHECK
        if reward in data["limits"]:
            data["winners"].setdefault(reward, [])

            if len(data["winners"][reward]) >= data["limits"][reward]:
                reward = "😢 Better luck next time"
            else:
                data["winners"][reward].append(uid)

        save()

        context.bot.send_message(uid, f"🎁 You got: {reward}")
        context.bot.send_message(ADMIN_ID, f"🏆 WINNER: {uid} → {reward}")

        if CHANNEL_ID and "Better luck" not in reward:
            context.bot.send_message(
                CHANNEL_ID,
                f"🏆 WINNER\nUser: {uid}\nPrize: {reward}"
            )

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

# ================= TEXT =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    if admin_state.get(uid) == "msg_admin":
        context.bot.send_message(ADMIN_ID, f"💬 MSG {uid}:\n{msg}")
        update.message.reply_text("✅ Sent")
        admin_state.pop(uid, None)
        return

    if uid != str(ADMIN_ID):
        return

    # ADMIN GIFT SEND
    if msg.startswith("/gift"):
        parts = msg.split(" ", 2)
        if len(parts) < 3:
            update.message.reply_text("Usage: /gift user_id message")
            return

        user_id = parts[1]
        gift = parts[2]
        context.bot.send_message(user_id, f"🎁 GIFT:\n{gift}")
        update.message.reply_text("Sent")

# ================= ADMIN =================
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
        BotCommand("admin", "Admin panel"),
        BotCommand("gift", "Send gift")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
