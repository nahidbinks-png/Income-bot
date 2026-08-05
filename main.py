import os
import telebot
from telebot import types

# Render-এর Environment Variable থেকে সঠিক নামে টোকেন নেওয়া হলো
BOTTOKEN = os.getenv('BOTTOKEN')
bot = telebot.TeleBot(BOTTOKEN)

# ডাটাবেসের ডেমো স্টোরেজ
users = {}
balances = {}
wallets = {}

# বাধ্যতামূলক চ্যানেলগুলোর লিস্ট
CHANNELS = ["@YourChannel1", "@YourChannel2"]

def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']:
                return False
        except:
            pass
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # চ্যানেল সাবস্ক্রাইব করা আছে কিনা চেক করা
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton("Join Channel ↗", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("Claim 🟢", callback_data="check_sub"))
        
        bot.send_message(message.chat.id, f"👋 Hello, 🇧🇩\n**{message.from_user.first_name}** !\n\n📢 Join All Channels To Continue.", reply_markup=markup, parse_mode="Markdown")
        return

    # রেফারেল হ্যান্ডেলিং
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if str(referrer_id) != str(user_id) and user_id not in users:
            balances[referrer_id] = balances.get(referrer_id, 0) + 1
            bot.send_message(referrer_id, "💰 আপনার ব্যালেন্স এ ১ টাকা যোগ করা হয়েছে 💰")

    users[user_id] = True
    main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    # সাবস্ক্রাইব চেক বাটন
    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "Verification Successful!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            users[user_id] = True
            main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "⚠️ আগে সব চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            
    # ব্যালেন্স চেক বাটন
    elif call.data == "my_balance":
        bal = balances.get(str(user_id), 0)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"💳 Your Current Balance: {bal} টাকা")
        
    # রেফার এন্ড আর্ন বাটন
    elif call.data == "refer_earn":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            "🎖️ Per Referral: 1 টাকা\n\n"
            f"🔗 Your Referral Link: {ref_link}\n\n"
            "📊 Your Total Referrals: None 📉\n\n"
            "🚫 Fake and cheat referrals will not be paid"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text)
        
    # সেট ওয়ালেট বাটন
    elif call.data == "set_wallet":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📞 আপনার বিকাশ বা নগদ নম্বরটি লিখুন:")
        bot.register_next_step_handler(msg, save_wallet)
        
    # ক্যাশআউট বাটন
    elif call.data == "cash_out":
        bal = balances.get(str(user_id), 0)
        bot.answer_callback_query(call.id)
        if bal < 10:
            bot.send_message(call.message.chat.id, "⚠️ আপনার ব্যালেন্স কম আছে। টাকা উত্তোলনের জন্য কমপক্ষে আপনার ব্যালেন্সের 10 টাকা থাকতে হবে ⚠️")
        else:
            bot.send_message(call.message.chat.id, "✅ আপনার ক্যাশআউট রিকোয়েস্ট সফলভাবে জমা হয়েছে!")

def main_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("My Balance Ω", callback_data="my_balance"),
        types.InlineKeyboardButton("Refer & Earn 👯", callback_data="refer_earn")
    )
    markup.row(
        types.InlineKeyboardButton("Set Wallet 💎", callback_data="set_wallet"),
        types.InlineKeyboardButton("Cash Out 💡", callback_data="cash_out")
    )
    bot.send_message(chat_id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=markup)

def save_wallet(message):
    user_id = str(message.from_user.id)
    wallets[user_id] = message.text
    bot.send_message(message.chat.id, "✅ সফলভাবে আপনার ওয়ালেট নম্বর সেভ করা হয়েছে!")
    main_menu(message.chat.id)

if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
