
import logging
import json
import os
import requests
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8078833919:AAEACT_P-brRnjeG1RR9Jt-zPcuaZDPHUcI"
BTC_WALLET_ADDRESS = "bc1qljp7auq2tgxycx5jl953kyuggwe8w3lwutpvqy"
BLOCKCYPHER_API_TOKEN = "2aca70ab478543c1ad20735e34e79c02"

users_file = "users.json"
price_usd = 200

if not os.path.exists(users_file):
    with open(users_file, "w") as f:
        json.dump({}, f)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def convert_usd_to_btc(usd_amount):
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
        response.raise_for_status()  # Raises error for bad response
        btc_price = response.json()["bitcoin"]["usd"]
        btc_amount = round(usd_amount / btc_price, 8)
        return btc_amount, btc_price
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching BTC price: {e}")
        return None, None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = {"id": user_id, "username": update.effective_user.username, "unique_code": str(uuid4())}
    with open(users_file, "r") as f:
        users = json.load(f)
    users[user_id] = user_data
    with open(users_file, "w") as f:
        json.dump(users, f)

    keyboard = [
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")],
        [InlineKeyboardButton("🎮 Google Play Console", callback_data="console")],
        [InlineKeyboardButton("💰 Google AdSense", callback_data="adsense")]
    ]
    await update.message.reply_text("🎉 Welcome to Google Play Services Store!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(query.from_user.id)

    with open(users_file, "r") as f:
        users = json.load(f)
    user_data = users.get(user_id, {"id": user_id, "username": query.from_user.username, "unique_code": str(uuid4())})

    if data == "profile":
        await query.edit_message_text(f"👤 Your Profile\nUser ID: {user_data['id']}\nUsername: @{user_data['username']}\nUnique Code: {user_data['unique_code']}")
    elif data == "console":
        keyboard = [
            [InlineKeyboardButton("👤 Individual", callback_data="type_individual")],
            [InlineKeyboardButton("🏢 Company", callback_data="type_company")],
            [InlineKeyboardButton("📱 With AdMob", callback_data="type_admob")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.edit_message_text("Select Account Type:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("type_"):
        keyboard = [
            [InlineKeyboardButton("📅 2022", callback_data="year_2022")],
            [InlineKeyboardButton("📅 2023", callback_data="year_2023")],
            [InlineKeyboardButton("📅 2024", callback_data="year_2024")],
            [InlineKeyboardButton("🔙 Back", callback_data="console")]
        ]
        await query.edit_message_text("Select Account Year:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("year_"):
        btc_amount, btc_price = convert_usd_to_btc(price_usd)
        if btc_amount:
            keyboard = [
                [InlineKeyboardButton("✅ Payment Done", callback_data="payment_done")],
                [InlineKeyboardButton("🔁 Resend Wallet", callback_data="year_resend")],
                [InlineKeyboardButton("🔍 Verify Payment", callback_data="verify_payment")],
                [InlineKeyboardButton("✏️ Send Hash", callback_data="send_hash")],
                [InlineKeyboardButton("🔙 Back", callback_data="console")]
            ]
            await query.edit_message_text(
                f"💰 *Price*: $200\n"
                f"💱 *BTC Rate*: 1 BTC = ${btc_price}\n"
                f"🪙 *Send Exactly*: `{btc_amount}` BTC\n"
                f"📬 *To Wallet*: `{BTC_WALLET_ADDRESS}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Failed to fetch BTC price. Please try again.")
    elif data == "payment_done":
        await query.edit_message_text("✅ Please send your transaction hash with /hash <tx_hash>")
    elif data == "verify_payment":
        await query.edit_message_text("🔍 Send your transaction hash with /hash <tx_hash> for verification.")
    elif data == "send_hash":
        await query.edit_message_text("✏️ Send transaction hash in format: /hash <tx_hash>")
    elif data == "back_home":
        await start(update, context)

async def hash_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /hash <transaction_hash>")
        return
    tx_hash = context.args[0]
    try:
        url = f"https://api.blockcypher.com/v1/btc/main/txs/{tx_hash}?token={BLOCKCYPHER_API_TOKEN}"
        response = requests.get(url)
        data = response.json()
        if "outputs" in data:
            for output in data["outputs"]:
                if BTC_WALLET_ADDRESS in output["addresses"]:
                    await update.message.reply_text("✅ Payment verified successfully! Thank you.")
                    return
        await update.message.reply_text("❌ Payment not received yet or wrong address.")
    except:
        await update.message.reply_text("⚠️ Error verifying payment. Please check again later.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CommandHandler("hash", hash_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
