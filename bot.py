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
            "👑 VIP Access": 1,
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
        data["users"][uid] = {"keys": 1}
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

# ================= PICK REWARD =================
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

    if CHANNEL_ID and not is_member(context.bot, uid):
        update.message.reply_text(
            "❌ Join our channel first to use the bot!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
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
                    context.bot.send_message(ref, "🎉 You got +1 Key from a Referral!")
                update.message.reply_text("🎉 Referral success! Enjoy your bonus!")

    save()
    update.message.reply_text("🔥 Welcome to the Bot!", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    if q.data == "check_join":
        if is_member(context.bot, uid):
            q.edit_message_text("✅ Verified! You're in.")
            context.bot.send_message(uid, "🏠 Home Menu", reply_markup=menu())
        else:
            q.answer("❌ You haven't joined yet!", show_alert=True)
        return

    if q.from_user.id != ADMIN_ID and is_spam(uid):
        q.answer("⚠️ Slow down!", show_alert=True)
        return

    # ================= ADMIN DASHBOARD =================
    if q.data == "admin":
        if q.from_user.id != ADMIN_ID:
            return
        q.edit_message_text(
            "🛠 ADMIN DASHBOARD",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                [InlineKeyboardButton("🎁 Add Reward", callback_data="a_add")],
                [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                [InlineKeyboardButton("📊 Set Limit", callback_data="a_limit")],
                [InlineKeyboardButton("📋 View Rewards", callback_data="a_rewards")],
                [InlineKeyboardButton("🎯 Giveaway", callback_data="a_give")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        return

    # ================= ADMIN ACTIONS =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "a_users":
            q.edit_message_text(f"👥 Total Users: {len(data['users'])}")
            return

        if q.data == "a_rewards":
            q.edit_message_text("📋 Rewards:\n" + "\n".join([r["name"] for r in data["rewards"]]))
            return

        if q.data == "a_add":
            admin_state[uid] = "add"
            q.edit_message_text("➕ Send: name weight\nExample: 🎁 New Reward 20")
            return

        if q.data == "a_remove":
            admin_state[uid] = "remove"
            q.edit_message_text("🗑 Send the reward name to remove:")
            return

        if q.data == "a_limit":
            admin_state[uid] = "limit"
            q.edit_message_text("📊 Send: reward_name limit\nExample: 👑 VIP Access 3")
            return

        if q.data == "back":
            q.edit_message_text("🏠 Home Menu", reply_markup=menu())
            return

    # ================= OPEN BOX =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ You have no keys left!", reply_markup=menu())
            return

        user["keys"] -= 1
        reward = pick_reward()
        is_real_win = True

        if reward in data["limits"]:
            data["winners"].setdefault(reward, [])
            if len(data["winners"][reward]) >= data["limits"][reward]:
                reward = "😢 Better luck next time!"
                is_real_win = False
            else:
                data["winners"][reward].append(uid)

        save()

        context.bot.send_message(uid, f"🎁 Result: {reward}", reply_markup=menu())

        # Only notify admin + channel on real wins
        if is_real_win:
            username = q.from_user.username
            display = f"@{username}" if username else f"User {uid}"

            context.bot.send_message(
                ADMIN_ID,
                f"🏆 NEW WINNER!\n👤 {display} (ID: {uid})\n🎁 Prize: {reward}"
            )

            if CHANNEL_ID:
                context.bot.send_message(
                    CHANNEL_ID,
                    f"🏆 We have a winner!\n👤 {display}\n🎁 Prize: {reward}"
                )

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Your Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        q.edit_message_text(f"🔗 Your Referral Link:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        q.edit_message_text(
            "🎁 Available Rewards:\n" + "\n".join([r["name"] for r in data["rewards"]]),
            reply_markup=menu()
        )

    elif q.data == "msg_admin":
        admin_state[uid] = "msg_admin"
        q.edit_message_text("💬 Type your message to the admin below:")

# ================= TEXT =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    # USER → ADMIN MESSAGE
    if admin_state.get(uid) == "msg_admin":
        username = update.message.from_user.username
        display = f"@{username}" if username else f"User {uid}"

        context.bot.send_message(
            ADMIN_ID,
            f"💬 Message from {display} (ID: {uid}):\n\n{msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"↩️ Reply to {display}", callback_data=f"reply_{uid}")]
            ])
        )
        update.message.reply_text("✅ Your message has been sent to the admin!")
        admin_state.pop(uid, None)
        return

    # ADMIN REPLY / STATES
    admin_uid = str(ADMIN_ID)
    if uid == admin_uid:
        state = admin_state.get(admin_uid)

        if isinstance(state, dict) and state.get("action") == "reply":
            target_uid = state["target"]
            context.bot.send_message(
                target_uid,
                f"💬 Message from Admin:\n\n{msg}"
            )
            update.message.reply_text("✅ Reply sent to user!")
            admin_state.pop(admin_uid, None)
            return

        if state == "add":
            try:
                parts = msg.rsplit(" ", 1)
                name, weight = parts[0], int(parts[1])
                data["rewards"].append({"name": name, "weight": weight})
                save()
                update.message.reply_text(f"✅ Reward added: {name} (weight {weight})")
            except Exception:
                update.message.reply_text("❌ Wrong format! Use: name weight\nExample: 🎁 New Reward 20")

        elif state == "remove":
            before = len(data["rewards"])
            data["rewards"] = [r for r in data["rewards"] if r["name"] != msg]
            save()
            if len(data["rewards"]) < before:
                update.message.reply_text(f"✅ Removed: {msg}")
            else:
                update.message.reply_text("❌ Reward not found!")

        elif state == "limit":
            try:
                parts = msg.rsplit(" ", 1)
                name, limit = parts[0], int(parts[1])
                data["limits"][name] = limit
                save()
                update.message.reply_text(f"✅ Limit set: {name} → {limit}")
            except Exception:
                update.message.reply_text("❌ Wrong format! Use: reward_name limit")

        admin_state.pop(admin_uid, None)
        return

# ================= REPLY CALLBACK =================
def reply_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    target_uid = q.data.split("_", 1)[1]
    admin_uid = str(ADMIN_ID)

    admin_state[admin_uid] = {"action": "reply", "target": target_uid}
    q.edit_message_text(
        q.message.text + f"\n\n✏️ Now type your reply below:"
    )

# ================= ADMIN COMMAND =================
def admin_cmd(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return
    update.message.reply_text(
        "🛠 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Open Dashboard", callback_data="admin")]
        ])
    )

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_cmd))
    dp.add_handler(CallbackQueryHandler(reply_callback, pattern=r"^reply_"))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
