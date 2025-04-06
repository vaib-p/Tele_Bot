
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import blockcypher

TELEGRAM_BOT_TOKEN = "8078833919:AAEACT_P-brRnjeG1RR9Jt-zPcuaZDPHUcI"
BLOCKCYPHER_API_TOKEN = "2aca70ab478543c1ad20735e34e79c02"
BTC_WALLET_ADDRESS = "bc1qljp7auq2tgxycx5jl953kyuggwe8w3lwutpvqy"
USER_DATA_FILE = "users.json"

def load_users():
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as f:
            json.dump({}, f)
    with open(USER_DATA_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

users = load_users()

def get_user_profile(user_id, full_name):
    if str(user_id) not in users:
        users[str(user_id)] = {
            "user_id": str(user_id),
            "name": full_name,
            "unique_id": f"GP-{user_id}-{int(time.time())}",
            "joined": time.ctime(),
            "selected_options": [],
            "payment_status": "Pending",
            "transaction_hash": ""
        }
        save_users(users)
    return users[str(user_id)]

def verify_btc_transaction(tx_hash, destination_address, min_confirmations=1):
    try:
        tx_details = blockcypher.get_transaction_details(tx_hash, coin_symbol='btc', api_key=BLOCKCYPHER_API_TOKEN)
        if tx_details.get('confirmations', 0) < min_confirmations:
            return False
        for output in tx_details.get('outputs', []):
            if destination_address in output.get('addresses', []):
                return True
        return False
    except Exception as e:
        print(f"Error verifying transaction: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile = get_user_profile(user.id, user.full_name)
    keyboard = [
        [InlineKeyboardButton("My Profile", callback_data="profile")],
        [InlineKeyboardButton("Google Play Console", callback_data="console")],
        [InlineKeyboardButton("Google AdSense", callback_data="adsense")],
    ]
    await update.message.reply_text("Welcome to Google Play Services Store!",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    profile = get_user_profile(user.id, user.full_name)
    await query.answer()
    data = query.data
    profile["selected_options"].append(data)
    save_users(users)

    if data == "profile":
        msg = (
            f"Name: {profile['name']}\n"
            f"User ID: {profile['user_id']}\n"
            f"Unique ID: {profile['unique_id']}\n"
            f"Joined: {profile['joined']}\n"
            f"Payment Status: {profile['payment_status']}"
        )
        await query.edit_message_text(msg)

    elif data == "console":
        keyboard = [
            [InlineKeyboardButton("Individual", callback_data="type_individual")],
            [InlineKeyboardButton("Company", callback_data="type_company")],
            [InlineKeyboardButton("With AdMob", callback_data="type_admob")],
            [InlineKeyboardButton("Back", callback_data="main_menu")],
        ]
        await query.edit_message_text("Choose Account Type:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("type_"):
        keyboard = [
            [InlineKeyboardButton("2022 Console", callback_data="year_2022")],
            [InlineKeyboardButton("2023 Console", callback_data="year_2023")],
            [InlineKeyboardButton("2024 Console", callback_data="year_2024")],
            [InlineKeyboardButton("Back", callback_data="console")],
        ]
        await query.edit_message_text("Choose Console Year:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("year_"):
        keyboard = [
            [InlineKeyboardButton("Payment Done", callback_data="payment_done")],
            [InlineKeyboardButton("Back", callback_data="console")],
        ]
        await query.edit_message_text(
            f"Send BTC to this wallet:\n`{BTC_WALLET_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "payment_done":
        keyboard = [
            [InlineKeyboardButton("Verify Payment", callback_data="verify_payment")],
            [InlineKeyboardButton("Resend Wallet Address", callback_data="resend_wallet")],
            [InlineKeyboardButton("Other Payment Options", callback_data="other_options")],
            [InlineKeyboardButton("Back", callback_data="console")],
        ]
        await query.edit_message_text(
            "Please reply with your *transaction hash* using /hash <your_tx_hash>",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "verify_payment":
        if profile["transaction_hash"]:
            is_valid = verify_btc_transaction(profile["transaction_hash"], BTC_WALLET_ADDRESS)
            if is_valid:
                profile["payment_status"] = "Confirmed"
                await query.edit_message_text("Payment confirmed! Thank you.")
            else:
                await query.edit_message_text("Payment not verified. Try again later.")
            save_users(users)
        else:
            await query.edit_message_text("No transaction hash found. Please send using /hash <tx_hash>")

    elif data == "resend_wallet":
        await query.edit_message_text(f"BTC Wallet:\n`{BTC_WALLET_ADDRESS}`", parse_mode="Markdown")

    elif data == "other_options":
        await query.edit_message_text("Currently only BTC accepted. UPI/ETH coming soon!")

    elif data == "adsense":
        await query.edit_message_text("AdSense Section Coming Soon!")

    elif data == "main_menu":
        await start(update, context)

async def hash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile = get_user_profile(user.id, user.full_name)
    if not context.args:
        await update.message.reply_text("Usage: /hash <your_transaction_hash>")
        return
    tx_hash = context.args[0]
    profile["transaction_hash"] = tx_hash
    is_valid = verify_btc_transaction(tx_hash, BTC_WALLET_ADDRESS)
    if is_valid:
        profile["payment_status"] = "Confirmed"
        await update.message.reply_text("Payment confirmed! Thank you.")
    else:
        profile["payment_status"] = "Pending"
        await update.message.reply_text("Transaction not found or not confirmed yet. Please try again later.")
    save_users(users)

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("hash", hash_command))
app.add_handler(CallbackQueryHandler(button_handler))
print("Bot is running...")
app.run_polling()
