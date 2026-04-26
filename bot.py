import os
import json
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATA_FILE = "data.json"

# ================= DATA =================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},
        "referrals": {},
        "rewards": ["🔥 Smooth Config", "💎 Paid File", "👑 VIP Access"],
        "vip_queue": [],
        "config_queue": []
    }

admin_state = {}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}
    return data["users"][uid]

# ================= LOADING =================
def loading(context, chat_id, msg_id, final):
    steps = [
        "🟦░░░░░░░░░ 10%",
        "🟦🟦🟦░░░░░ 30%",
        "🟦🟦🟦🟦🟦░ 60%",
        "🟦🟦🟦🟦🟦🟦🟦 90%",
        "🟦🟦🟦🟦🟦🟦🟦🟦🟦 100%"
    ]

    for s in steps:
        context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"⏳ Opening...\n\n{s}")
        time.sleep(0.3)

    context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=final)

# ================= MAIN MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 My Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite Friends", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards Info", callback_data="rewards")],
        [InlineKeyboardButton("⏳ Daily (Soon)", callback_data="daily")]
    ])

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"keys": 0}

    # referral system (safe)
    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            data["referrals"][uid] = ref
            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
            save()

    update.message.reply_text(
        "🔥 Welcome to Mystery Drop Bot",
        reply_markup=main_menu()
    )

# ================= BUTTONS =================
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # ============ USER ACTIONS ============
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys. Invite friends to earn keys.")
            return

        user["keys"] -= 1
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
        q.edit_message_text(
            f"🔑 Keys: {user['keys']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(
            f"🔗 Share this link:\n{link}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )

    elif q.data == "rewards":
        q.edit_message_text(
            "\n".join(data["rewards"]),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )

    elif q.data == "daily":
        q.edit_message_text(
            "⏳ Coming Soon...\n🎁 Daily rewards under development",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )

    elif q.data == "back":
        q.edit_message_text(
            "🏠 Main Menu",
            reply_markup=main_menu()
        )

    # ============ ADMIN PANEL ============
    if q.from_user.id == ADMIN_ID:

        if q.data == "admin":
            keyboard = [
                [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                [InlineKeyboardButton("🎁 Rewards", callback_data="a_rewards")],
                [InlineKeyboardButton("➕ Add Reward", callback_data="a_add")],
                [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                [InlineKeyboardButton("📦 Queue", callback_data="a_queue")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]

            q.edit_message_text("🛠 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

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

# ================= ADMIN TEXT INPUT =================
def text(update: Update, context: CallbackContext):
    uid = update.message.from_user.id

    if uid != ADMIN_ID:
        return

    state = admin_state.get(uid)
    msg = update.message.text

    if state == "add":
        data["rewards"].append(msg)
        save()
        update.message.reply_text("✅ Reward added")
        admin_state.pop(uid)

    elif state == "remove":
        if msg in data["rewards"]:
            data["rewards"].remove(msg)
            save()
            update.message.reply_text("❌ Reward removed")
        else:
            update.message.reply_text("⚠️ Not found")
        admin_state.pop(uid)

    elif state == "keys":
        try:
            user_id, amt = msg.split()
            get_user(user_id)["keys"] += int(amt)
            save()
            update.message.reply_text("✅ Keys added")
        except:
            update.message.reply_text("❌ Format: user_id amount")
        admin_state.pop(uid)

# ================= ADMIN COMMAND =================
def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    update.message.reply_text(
        "🛠 Admin Access",
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
