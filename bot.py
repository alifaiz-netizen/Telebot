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
        "rewards": [
            {"name": "🔥 Smooth Config", "weight": 60},
            {"name": "💎 Paid File", "weight": 30},
            {"name": "👑 VIP Access", "weight": 10}
        ],
        "vip_queue": [],
        "config_queue": [],
        "cooldowns": {},
        "vip_limit": 5
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

# ================= SPAM PROTECTION =================
def is_spam(uid):
    now = time.time()
    last = data["cooldowns"].get(uid, 0)

    if now - last < 4:
        return True

    data["cooldowns"][uid] = now
    return False

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
        time.sleep(0.2)

    context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=final)

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 My Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards Info", callback_data="rewards")],
        [InlineKeyboardButton("⏳ Daily (Soon)", callback_data="daily")]
    ])

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    get_user(uid)

    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            data["referrals"][uid] = ref
            if ref in data["users"]:
                data["users"][ref]["keys"] += 1
            save()

    update.message.reply_text("🔥 Welcome Bot", reply_markup=main_menu())

# ================= REWARD ENGINE =================
def pick_reward():
    total = sum(r["weight"] for r in data["rewards"])
    r = random.randint(1, total)

    upto = 0
    for reward in data["rewards"]:
        if upto + reward["weight"] >= r:
            return reward["name"]
        upto += reward["weight"]

# ================= CALLBACKS =================
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # SPAM CHECK
    if is_spam(uid):
        q.edit_message_text("⚠️ Slow down bro (anti-spam)")
        return

    # ================= USER =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ No keys")
            return

        user["keys"] -= 1
        save()

        msg = q.message
        loading(context, msg.chat_id, msg.message_id, "🎁 Opening Done!")

        reward = pick_reward()

        if "VIP" in reward:
            if len(data["vip_queue"]) < data["vip_limit"]:
                data["vip_queue"].append(uid)

        if "Config" in reward:
            data["config_queue"].append(uid)

        save()
        context.bot.send_message(uid, f"🎁 You got: {reward}")

    elif q.data == "keys":
        q.edit_message_text(f"🔑 Keys: {user['keys']}", reply_markup=main_menu())

    elif q.data == "refer":
        bot = context.bot.username
        link = f"https://t.me/{bot}?start={uid}"
        q.edit_message_text(f"🔗 Invite Link:\n{link}", reply_markup=main_menu())

    elif q.data == "rewards":
        text = "\n".join([f"{r['name']} - {r['weight']}%" for r in data["rewards"]])
        q.edit_message_text(text, reply_markup=main_menu())

    elif q.data == "daily":
        q.edit_message_text("⏳ Coming soon...", reply_markup=main_menu())

    elif q.data == "back":
        q.edit_message_text("🏠 Menu", reply_markup=main_menu())

    # ================= ADMIN =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "admin":
            q.edit_message_text(
                "🛠 Admin Panel",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 Users", callback_data="a_users")],
                    [InlineKeyboardButton("🎁 Rewards", callback_data="a_rewards")],
                    [InlineKeyboardButton("➕ Add Reward", callback_data="a_add")],
                    [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                    [InlineKeyboardButton("🔑 Add Keys", callback_data="a_keys")],
                    [InlineKeyboardButton("📦 Queue", callback_data="a_queue")],
                    [InlineKeyboardButton("⚙️ VIP Limit", callback_data="a_vip")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ])
            )

        elif q.data == "a_users":
            q.edit_message_text(f"👥 Users: {len(data['users'])}")

        elif q.data == "a_rewards":
            text = "\n".join([f"{r['name']} ({r['weight']}%)" for r in data["rewards"]])
            q.edit_message_text(text)

        elif q.data == "a_queue":
            q.edit_message_text(
                f"📦 VIP: {len(data['vip_queue'])}\n💎 Config: {len(data['config_queue'])}"
            )

        elif q.data == "a_add":
            admin_state[ADMIN_ID] = "add"
            q.edit_message_text("Send: name weight (example VIP 10)")

        elif q.data == "a_remove":
            admin_state[ADMIN_ID] = "remove"
            q.edit_message_text("Send reward name")

        elif q.data == "a_keys":
            admin_state[ADMIN_ID] = "keys"
            q.edit_message_text("Send: user_id amount")

        elif q.data == "a_vip":
            admin_state[ADMIN_ID] = "vip"
            q.edit_message_text("Send VIP limit number")

# ================= ADMIN TEXT =================
def text(update: Update, context: CallbackContext):
    uid = update.message.from_user.id
    if uid != ADMIN_ID:
        return

    state = admin_state.get(uid)
    msg = update.message.text

    if state == "add":
        name, weight = msg.split()
        data["rewards"].append({"name": name, "weight": int(weight)})
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

    elif state == "vip":
        data["vip_limit"] = int(msg)
        save()
        update.message.reply_text("📊 VIP limit set")

    admin_state.pop(uid, None)

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
