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
            {"name": "ðŸ”¥ Smooth Config", "weight": 60},
            {"name": "ðŸ’Ž Paid Config", "weight": 30},
            {"name": "ðŸ‘‘ VIP Access", "weight": 10}
        ],
        "limits": {
            "ðŸ‘‘ VIP Access": 1,
            "ðŸ”¥ Smooth Config": 6,
            "ðŸ’Ž Paid Config": 6
        },
        "winners": {},
        "giveaway": {"active": False, "limit": 0, "users": []}
    }

# admin_state tracks both user msg flow and admin reply flow
# For users:  admin_state[uid] = "msg_admin"
# For admin:  admin_state[str(ADMIN_ID)] = {"action": "reply", "target": uid}
#             admin_state[str(ADMIN_ID)] = "add" | "remove" | "limit"
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
        [InlineKeyboardButton("ðŸŽ Open Box", callback_data="open")],
        [InlineKeyboardButton("ðŸ”‘ Keys", callback_data="keys")],
        [InlineKeyboardButton("ðŸ”— Invite", callback_data="refer")],
        [InlineKeyboardButton("ðŸŽ Rewards", callback_data="rewards")],
        [InlineKeyboardButton("ðŸ’¬ Message Admin", callback_data="msg_admin")]
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
            "âŒ Join channel first",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ðŸ“¢ Join", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
                [InlineKeyboardButton("â™»ï¸ I Joined", callback_data="check_join")]
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
                    context.bot.send_message(ref, "ðŸŽ‰ +1 Key from Referral!")
                update.message.reply_text("ðŸŽ‰ Referral success!")

    save()
    update.message.reply_text("ðŸ”¥ Welcome!", reply_markup=menu())

# ================= CALLBACK =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid)

    # JOIN CHECK
    if q.data == "check_join":
        if is_member(context.bot, uid):
            q.edit_message_text("âœ… Verified!")
            context.bot.send_message(uid, "ðŸ  Menu", reply_markup=menu())
        else:
            q.answer("âŒ Not joined yet", show_alert=True)
        return

    # SPAM (skip for admin)
    if q.from_user.id != ADMIN_ID and is_spam(uid):
        q.answer("âš ï¸ Slow down", show_alert=True)
        return

    # ================= ADMIN DASHBOARD =================
    if q.data == "admin":
        if q.from_user.id != ADMIN_ID:
            return

        q.edit_message_text(
            "ðŸ›  ADMIN DASHBOARD",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ðŸ‘¥ Users", callback_data="a_users")],
                [InlineKeyboardButton("ðŸ”‘ Add Keys", callback_data="a_keys")],
                [InlineKeyboardButton("ðŸŽ Add Reward", callback_data="a_add")],
                [InlineKeyboardButton("âŒ Remove Reward", callback_data="a_remove")],
                [InlineKeyboardButton("ðŸ“Š Set Limit", callback_data="a_limit")],
                [InlineKeyboardButton("ðŸ“‹ View Rewards", callback_data="a_rewards")],
                [InlineKeyboardButton("ðŸŽ¯ Giveaway", callback_data="a_give")],
                [InlineKeyboardButton("ðŸ”™ Back", callback_data="back")]
            ])
        )
        return

    # ================= ADMIN ACTIONS =================
    if q.from_user.id == ADMIN_ID:

        if q.data == "a_users":
            q.edit_message_text(f"ðŸ‘¥ Total Users: {len(data['users'])}")
            return

        if q.data == "a_rewards":
            q.edit_message_text("\n".join([r["name"] for r in data["rewards"]]))
            return

        if q.data == "a_add":
            admin_state[uid] = "add"
            q.edit_message_text("Send: name weight\nExample: ðŸŽNewReward 20")
            return

        if q.data == "a_remove":
            admin_state[uid] = "remove"
            q.edit_message_text("Send reward name to remove")
            return

        if q.data == "a_limit":
            admin_state[uid] = "limit"
            q.edit_message_text("Send: reward_name limit\nExample: ðŸ‘‘ VIP Access 3")
            return

        if q.data == "back":
            q.edit_message_text("ðŸ  Menu", reply_markup=menu())
            return

    # ================= OPEN BOX =================
    if q.data == "open":
        if user["keys"] <= 0:
            q.edit_message_text("âŒ No keys left!", reply_markup=menu())
            return

        user["keys"] -= 1
        reward = pick_reward()
        is_real_win = True

        if reward in data["limits"]:
            data["winners"].setdefault(reward, [])
            if len(data["winners"][reward]) >= data["limits"][reward]:
                reward = "ðŸ˜¢ Better luck next time"
                is_real_win = False
            else:
                data["winners"][reward].append(uid)

        save()

        # Tell the user their result
        context.bot.send_message(uid, f"ðŸŽ {reward}", reply_markup=menu())

        # FIX 1: Only notify admin + channel if it's a REAL win (not "Better luck")
        if is_real_win:
            username = q.from_user.username
            display = f"@{username}" if username else f"User {uid}"

            # Notify admin privately
            context.bot.send_message(
                ADMIN_ID,
                f"ðŸ† NEW WINNER!\nðŸ‘¤ {display} (ID: {uid})\nðŸŽ Prize: {reward}"
            )

            # Post to channel
            if CHANNEL_ID:
                context.bot.send_message(
                    CHANNEL_ID,
                    f"ðŸ† We have a winner!\nðŸ‘¤ {display}\nðŸŽ Prize: {reward}"
                )

    elif q.data == "keys":
        q.edit_message_text(f"ðŸ”‘ Your Keys: {user['keys']}", reply_markup=menu())

    elif q.data == "refer":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        q.edit_message_text(f"ðŸ”— Your Referral Link:\n{link}", reply_markup=menu())

    elif q.data == "rewards":
        q.edit_message_text(
            "ðŸŽ Available Rewards:\n" + "\n".join([r["name"] for r in data["rewards"]]),
            reply_markup=menu()
        )

    # FIX 2: User taps "Message Admin" â€” sets their state
    elif q.data == "msg_admin":
        admin_state[uid] = "msg_admin"
        q.edit_message_text("ðŸ’¬ Type your message to the admin:")

# ================= TEXT =================
def text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    msg = update.message.text

    # â”€â”€ USER â†’ ADMIN MESSAGE â”€â”€
    if admin_state.get(uid) == "msg_admin":
        username = update.message.from_user.username
        display = f"@{username}" if username else f"User {uid}"

        # Forward message to admin WITH a reply button
        context.bot.send_message(
            ADMIN_ID,
            f"ðŸ’¬ Message from {display} (ID: {uid}):\n\n{msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"â†©ï¸ Reply to {display}", callback_data=f"reply_{uid}")]
            ])
        )
        update.message.reply_text("âœ… Message sent to admin!")
        admin_state.pop(uid, None)
        return

    # â”€â”€ ADMIN REPLY STATE â”€â”€
    # FIX 3: Admin is in reply mode â€” send their text back to the user
    admin_uid = str(ADMIN_ID)
    if uid == admin_uid:
        state = admin_state.get(admin_uid)

        if isinstance(state, dict) and state.get("action") == "reply":
            target_uid = state["target"]
            context.bot.send_message(
                target_uid,
                f"ðŸ’¬ Message from Admin:\n\n{msg}"
            )
            update.message.reply_text("âœ… Reply sent!")
            admin_state.pop(admin_uid, None)
            return

        # â”€â”€ OTHER ADMIN STATES â”€â”€
        if state == "add":
            try:
                parts = msg.rsplit(" ", 1)  # split from right so name can have spaces
                name, weight = parts[0], int(parts[1])
                data["rewards"].append({"name": name, "weight": weight})
                save()
                update.message.reply_text(f"âœ… Added: {name} (weight {weight})")
            except Exception:
                update.message.reply_text("âŒ Format: name weight\nExample: ðŸŽNewReward 20")

        elif state == "remove":
            before = len(data["rewards"])
            data["rewards"] = [r for r in data["rewards"] if r["name"] != msg]
            save()
            if len(data["rewards"]) < before:
                update.message.reply_text(f"âœ… Removed: {msg}")
            else:
                update.message.reply_text("âŒ Reward not found")

        elif state == "limit":
            try:
                parts = msg.rsplit(" ", 1)
                name, limit = parts[0], int(parts[1])
                data["limits"][name] = limit
                save()
                update.message.reply_text(f"âœ… Limit set: {name} â†’ {limit}")
            except Exception:
                update.message.reply_text("âŒ Format: reward_name limit")

        admin_state.pop(admin_uid, None)
        return

    # Non-admin, non-state messages â€” ignore silently
    # (FIX: removed the old /reply command which was visible to users)

# ================= REPLY CALLBACK (Admin taps Reply button) =================
def reply_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()

    # Only admin can use this
    if q.from_user.id != ADMIN_ID:
        return

    # Extract target user ID from callback data "reply_{uid}"
    target_uid = q.data.split("_", 1)[1]
    admin_uid = str(ADMIN_ID)

    admin_state[admin_uid] = {"action": "reply", "target": target_uid}
    q.edit_message_text(
        q.message.text + f"\n\nâœï¸ Type your reply now (sending to {target_uid}):"
    )

# ================= ADMIN COMMAND =================
def admin_cmd(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    update.message.reply_text(
        "ðŸ›  ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Dashboard", callback_data="admin")]
        ])
    )

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_cmd))

    # FIX: Separate handler for reply_ callbacks so it doesn't clash with button()
    dp.add_handler(CallbackQueryHandler(reply_callback, pattern=r"^reply_"))
    dp.add_handler(CallbackQueryHandler(button))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
