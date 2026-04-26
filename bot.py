import os
import json
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
        "giveaway": {"active": False, "limit": 0, "users": [], "keys": 1}
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

# ================= LOADING BAR =================
def loading_bar(percent):
    filled = int(percent / 10)
    empty = 10 - filled
    bar = "▓" * filled + "░" * empty
    return f"[{bar}] {percent}%"

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Open Box", callback_data="open")],
        [InlineKeyboardButton("🔑 My Keys", callback_data="keys")],
        [InlineKeyboardButton("🔗 Invite", callback_data="refer")],
        [InlineKeyboardButton("🎁 Rewards", callback_data="rewards")],
        [InlineKeyboardButton("💬 Message Admin", callback_data="msg_admin")]
    ])

# ================= PICK REWARD =================
# Always picks from ALL rewards using weights (including limited ones).
# If the picked reward is fully claimed → show "Better luck next time"
# This way limited rewards feel rare and fair
def pick_reward():
    rewards = data["rewards"]
    if not rewards:
        return None, False

    total = sum(r["weight"] for r in rewards)
    rand = random.randint(1, total)
    upto = 0
    picked = None
    for rw in rewards:
        upto += rw["weight"]
        if upto >= rand:
            picked = rw["name"]
            break

    if picked is None:
        return None, False

    # Check if this reward has a limit and is fully claimed
    limit = data["limits"].get(picked)
    if limit is not None:
        claimed = len(data["winners"].get(picked, []))
        if claimed >= limit:
            # Reward is sold out → better luck next time
            return "😢 Better luck next time!", False

    # Valid win
    return picked, True

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    user = get_user(uid)

    if CHANNEL_ID and not is_member(context.bot, uid):
        update.message.reply_text(
            "❌ Join our channel first to use the bot!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                [InlineKeyboardButton("♻️ I Joined", callback_data="check_join")]
            ])
        )
        return

    # GIVEAWAY CHECK — first N users who /start get free keys
    giveaway = data["giveaway"]
    if giveaway["active"] and uid not in giveaway["users"]:
        if len(giveaway["users"]) < giveaway["limit"]:
            giveaway["users"].append(uid)
            keys_given = giveaway.get("keys", 1)
            user["keys"] += keys_given
            joined = len(giveaway["users"])
            limit = giveaway["limit"]
            pct = int((joined / limit) * 100)
            bar = loading_bar(pct)
            update.message.reply_text(
                f"🎉 You got {keys_given} free key(s) from the Giveaway!\n\n"
                f"📊 Giveaway Progress:\n{bar}\n"
                f"👥 {joined}/{limit} users claimed"
            )
            # Auto-stop giveaway when limit is reached
            if joined >= limit:
                data["giveaway"]["active"] = False
                update.message.reply_text("🏁 Giveaway is now over! All slots have been claimed.")
            save()

    # REFERRAL CHECK
    if context.args:
        ref = context.args[0]
        if ref != uid and uid not in data["referrals"]:
            if is_member(context.bot, uid):
                data["referrals"][uid] = ref
                if ref in data["users"]:
                    data["users"][ref]["keys"] += 1
                    # Notify referrer
                    context.bot.send_message(
                        ref,
                        f"🎉 You got +1 Key from a Referral!\n"
                        f"🔑 Your total keys: {data['users'][ref]['keys']}"
                    )
                update.message.reply_text(
                    f"🎉 Referral success!\n"
                    f"🔑 Your friend got +1 Key!"
                )

    save()
    update.message.reply_text("🔥 Welcome to the Bot!", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # JOIN CHECK
    if q.data == "check_join":
        if is_member(context.bot, uid):
            q.edit_message_text("✅ Verified! You're in.")
            context.bot.send_message(uid, "🏠 Home Menu", reply_markup=menu())
        else:
            q.answer("❌ You haven't joined yet!", show_alert=True)
        return

    # SPAM
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
                [InlineKeyboardButton("🔑 Add Keys to User", callback_data="a_keys")],
                [InlineKeyboardButton("🎁 Add Reward", callback_data="a_add")],
                [InlineKeyboardButton("❌ Remove Reward", callback_data="a_remove")],
                [InlineKeyboardButton("📊 Set Limit", callback_data="a_limit")],
                [InlineKeyboardButton("📋 View Rewards", callback_data="a_rewards")],
                [InlineKeyboardButton("🎯 Start Giveaway", callback_data="a_give")],
                [InlineKeyboardButton("🛑 Stop Giveaway", callback_data="a_give_stop")],
                [InlineKeyboardButton("📈 Giveaway Status", callback_data="a_give_status")],
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
            lines = []
            for r in data["rewards"]:
                name = r["name"]
                weight = r["weight"]
                limit = data["limits"].get(name, "∞")
                claimed = len(data["winners"].get(name, []))
                lines.append(f"{name}\n   Weight: {weight} | Claimed: {claimed}/{limit}")
            q.edit_message_text("📋 Rewards:\n\n" + "\n\n".join(lines))
            return

        if q.data == "a_add":
            admin_state[uid] = "add"
            q.edit_message_text("➕ Send reward details:\nFormat: name weight\nExample: 🎁 New Reward 20")
            return

        if q.data == "a_remove":
            admin_state[uid] = "remove"
            q.edit_message_text("🗑 Send the reward name to remove:")
            return

        if q.data == "a_limit":
            admin_state[uid] = "limit"
            q.edit_message_text(
                "📊 Send: reward_name limit\n"
                "Example: 👑 VIP Access 1\n\n"
                "This means only 1 user can ever win that reward."
            )
            return

        if q.data == "a_keys":
            admin_state[uid] = "addkeys"
            q.edit_message_text("🔑 Send: user_id amount\nExample: 123456789 5")
            return

        if q.data == "a_give":
            admin_state[uid] = "giveaway"
            q.edit_message_text(
                "🎯 Start a Giveaway!\n\n"
                "Send: limit keys\n"
                "Example: 10 3\n\n"
                "First 10 users who start the bot will get 3 free keys each."
            )
            return

        if q.data == "a_give_stop":
            data["giveaway"]["active"] = False
            save()
            q.edit_message_text("🛑 Giveaway stopped!")
            return

        if q.data == "a_give_status":
            g = data["giveaway"]
            if not g["active"]:
                q.edit_message_text("ℹ️ No active giveaway right now.")
            else:
                joined = len(g["users"])
                limit = g["limit"]
                pct = int((joined / limit) * 100) if limit > 0 else 100
                bar = loading_bar(pct)
                q.edit_message_text(
                    f"🎯 Giveaway Active!\n\n"
                    f"📊 Progress:\n{bar}\n"
                    f"👥 {joined}/{limit} claimed\n"
                    f"🔑 Keys per user: {g.get('keys', 1)}"
                )
            return

        if q.data == "back":
            q.edit_message_text("🏠 Home Menu", reply_markup=menu())
            return

    # ================= OPEN BOX =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("❌ You have no keys left!", reply_markup=menu())
            return

        # Animated loading bar
        msg = context.bot.send_message(uid, f"🎰 Opening your box...\n{loading_bar(0)}")
        for pct in [20, 40, 60, 80, 100]:
            time.sleep(0.4)
            context.bot.edit_message_text(
                f"🎰 Opening your box...\n{loading_bar(pct)}",
                chat_id=uid,
                message_id=msg.message_id
            )

        user["keys"] -= 1
        reward, is_real_win = pick_reward()

        if reward is None:
            context.bot.edit_message_text(
                "😔 No rewards available right now. Check back later!",
                chat_id=uid,
                message_id=msg.message_id
            )
            save()
            return

        if is_real_win:
            data["winners"].setdefault(reward, [])
            data["winners"][reward].append(uid)

        save()

        # Show result
        context.bot.edit_message_text(
            f"🎁 Result: {reward}\n\n🔑 Remaining Keys: {user['keys']}",
            chat_id=uid,
            message_id=msg.message_id
        )

        # Notify admin + channel ONLY on real win
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
        q.edit_message_text(
            f"🔗 Your Referral Link:\n{link}\n\n"
            f"Share this link — when someone joins via your link you get +1 Key!",
            reply_markup=menu()
        )

    elif q.data == "rewards":
        lines = []
        for r in data["rewards"]:
            name = r["name"]
            limit = data["limits"].get(name)
            claimed = len(data["winners"].get(name, []))
            if limit is not None:
                remaining = limit - claimed
                if remaining > 0:
                    lines.append(f"{name} — {remaining} left")
                else:
                    lines.append(f"{name} — 🔴 Fully Claimed")
            else:
                lines.append(f"{name}")
        q.edit_message_text(
            "🎁 Rewards:\n\n" + "\n".join(lines),
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

    # ADMIN STATES
    admin_uid = str(ADMIN_ID)
    if uid == admin_uid:
        state = admin_state.get(admin_uid)

        # Admin replying to user
        if isinstance(state, dict) and state.get("action") == "reply":
            target_uid = state["target"]
            context.bot.send_message(target_uid, f"💬 Message from Admin:\n\n{msg}")
            update.message.reply_text("✅ Reply sent!")
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
                update.message.reply_text(
                    f"✅ Limit set!\n"
                    f"🎁 {name} → max {limit} winner(s)"
                )
            except Exception:
                update.message.reply_text("❌ Wrong format! Use: reward_name limit\nExample: 👑 VIP Access 1")

        elif state == "addkeys":
            try:
                parts = msg.split()
                target_uid, amount = parts[0], int(parts[1])
                target_user = get_user(target_uid)
                target_user["keys"] += amount
                save()
                update.message.reply_text(
                    f"✅ Added {amount} key(s) to User {target_uid}\n"
                    f"🔑 They now have {target_user['keys']} key(s)"
                )
                context.bot.send_message(
                    target_uid,
                    f"🎉 Admin added {amount} key(s) to your account!\n"
                    f"🔑 You now have {target_user['keys']} key(s)"
                )
            except Exception:
                update.message.reply_text("❌ Wrong format! Use: user_id amount\nExample: 123456789 5")

        elif state == "giveaway":
            try:
                parts = msg.split()
                limit, keys = int(parts[0]), int(parts[1])
                data["giveaway"] = {
                    "active": True,
                    "limit": limit,
                    "users": [],
                    "keys": keys
                }
                save()
                update.message.reply_text(
                    f"✅ Giveaway started!\n"
                    f"🎯 First {limit} users who start the bot get {keys} free key(s) each!\n\n"
                    f"📊 Progress:\n{loading_bar(0)}\n"
                    f"👥 0/{limit} claimed"
                )
            except Exception:
                update.message.reply_text("❌ Wrong format! Use: limit keys\nExample: 10 3")

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
    q.edit_message_text(q.message.text + "\n\n✏️ Now type your reply below:")

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
