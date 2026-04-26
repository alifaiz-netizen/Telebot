import os
import json
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL = "@RITIK_GAMING_OG"

DATA_FILE = "data.json"

# ---------------- DATA LOAD ----------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "referrals": {},
        "rewards": ["🔥 Smooth Config", "💎 Paid File", "👑 VIP Access"],
        "config_queue": [],
        "vip_queue": []
    }

admin_state = {}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}
    return data["users"][uid]

# ---------------- LOADING BAR ----------------
def loading(context, chat_id, msg_id, final):
    steps = [
        "🟦░░░░░░░░░░ 0%",
        "🟦🟦🟦░░░░░░ 30%",
        "🟦🟦🟦🟦🟦░░ 50%",
        "🟦🟦🟦🟦🟦🟦🟦 80%",
        "🟦🟦🟦🟦🟦🟦🟦🟦🟦 100%"
    ]

    for s in steps:
        context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"⏳ Opening...\n\n{s}")
        time.sleep(0.4)

    context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=final)

# ---------------- START ----------------
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}

    # referral (no abuse)
    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            data["referrals"][uid] = ref
            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
            save()

    keyboard = [
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 My Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("⏳ Daily (Soon)", callback_data="daily")]
    ]

    update.message.reply_text(
        "🔥 Mystery Drop Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- MAIN BUTTON HANDLER ----------------
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    u = user(uid)

    # ---------------- USER ACTIONS ----------------
    if q.data == "open":
        if u["keys"] <= 0:
            q.edit_message_text("❌ No keys! Invite friends.")
            return

        u["keys"] -= 1
        save()

        msg = q.message
        loading(context, msg.chat_id, msg.message_id, "🎉 Box Opened!")

        reward = random.choice(data["rewards"])

        if "VIP" in reward:
            data["vip_queue"].append(uid)
        if "Config" in reward:
            data["config_queue"].append(uid)

        save()
        context.bot.send_message(uid, f"🎁 You got: {reward}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {u['keys']}")

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 Invite link:\n{link}")

    elif q.data == "rewards":
        q.edit_message_text("\n".join(data["rewards"]))

    elif q.data == "daily":
        q.edit_message_text(
            "⏳ Coming Soon...\n\n🎁 Daily rewards under development"
        )

    # ---------------- ADMIN PANEL ----------------
    if q.from_user.id == ADMIN_ID:

        if q.data == "admin":
            keyboard = [
                [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                [InlineKeyboardButton("🎁 Rewards", callback_data="a_rewards")],
                [InlineKeyboardButton("➕ Add Reward", callback_data="a_add")],
                [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                [InlineKeyboardButton("📦 Queue", callback_data="a_queue")]
            ]

            q.edit_message_text(
                "🛠 Admin Panel",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")

        elif q.data == "a_rewards":
            q.edit_message_text("\n".join(data["rewards"]))

        elif q.data == "a_queue":
            q.edit_message_text(
                f"📦 Config: {len(data['config_queue'])}\n💎 VIP: {len(data['vip_queue'])}"
            )

        elif q.data == "a_add":
            admin_state[ADMIN_ID] = "add"
            q.edit_message_text("Send reward name")

        elif q.data == "a_remove":
            admin_state[ADMIN_ID] = "remove"
            q.edit_message_text("Send reward name")

        elif q.data == "a_keys":
            admin_state[ADMIN_ID] = "keys"
            q.edit_message_text("Send: user_id amount")

# ---------------- ADMIN TEXT INPUT ----------------
def text(update: Update, context: CallbackContext):
    uid = update.message.from_user.id
    if uid != ADMIN_ID:
        return

    state = admin_state.get(uid)
    msg = update.message.text

    if state == "add":
        data["rewards"].append(msg)
        save()
        update.message.reply_text("✅ Added reward")

    elif state == "remove":
        if msg in data["rewards"]:
            data["rewards"].remove(msg)
            save()
            update.message.reply_text("❌ Removed reward")

    elif state == "keys":
        try:
            user_id, amt = msg.split()
            user(user_id)["keys"] += int(amt)
            save()
            update.message.reply_text("✅ Keys added")
        except:
            update.message.reply_text("❌ Format: user_id amount")

# ---------------- ADMIN COMMAND ----------------
def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [[InlineKeyboardButton("🛠 Open Panel", callback_data="admin")]]
    update.message.reply_text("Admin Access", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- MAIN ----------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))

    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

    updater.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("admin", "Admin panel")
    ])

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
