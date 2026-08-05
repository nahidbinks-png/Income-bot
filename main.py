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

# শুধুমাত্র /start কমান্ডের জন্য এটি কাজ করবে
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

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_query(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "Verification Successful!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        users[user_id] = True
        main_menu(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "⚠️ আগে সব চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)

def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('My Balance Ω', 'Refer & Earn 👯')
    markup.row('Set Wallet 💎', 'Cash Out 💡')
    bot.send_message(chat_id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Refer & Earn 👯')
def refer_earn(message):
    user_id = message.from_user.id
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    text = (
        "🎖️ Per Referral: 1 টাকা\n\n"
        f"🔗 Your Referral Link: {ref_link}\n\n"
        "📊 Your Total Referrals: None 📉\n\n"
        "🚫 Fake and cheat referrals will not be paid"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == 'My Balance Ω')
def my_balance(message):
    user_id = message.from_user.id
    bal = balances.get(str(user_id), 0)
    bot.send_message(message.chat.id, f"💳 Your Current Balance: {bal} টাকা")

@bot.message_handler(func=lambda message: message.text == 'Set Wallet 💎')
def set_wallet(message):
    user_id = str(message.from_user.id)
    current_w = wallets.get(user_id, "Not Set!!")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('⚙️ Set Wallet')
    markup.row('🔙 Back')
    
    bot.send_message(message.chat.id, f"📝 Current Wallet: {current_w}\n\n🔍 ওয়ালেট পরিবর্তন করতে ⚙️ সেট ওয়ালেট বাটনে ক্লিক দেন।", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '⚙️ Set Wallet')
def ask_wallet(message):
    msg = bot.send_message(message.chat.id, "📞 আপনার বিকাশ বা নগদ নম্বরটি লিখুন:")
    bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    user_id = str(message.from_user.id)
    wallets[user_id] = message.text
    bot.send_message(message.chat.id, "✅ সফলভাবে আপনার ওয়ালেট নম্বর সেভ করা হয়েছে!")
    main_menu(message.chat.id)

@bot.message_handler(func=lambda message: message.text == 'Cash Out 💡')
def cash_out(message):
    user_id = str(message.from_user.id)
    bal = balances.get(user_id, 0)
    if bal < 10:
        bot.send_message(message.chat.id, "⚠️ আপনার ব্যালেন্স কম আছে। টাকা উত্তোলনের জন্য কমপক্ষে আপনার ব্যালেন্সের 10 টাকা থাকতে হবে ⚠️")
    else:
        bot.send_message(message.chat.id, "✅ আপনার ক্যাশআউট রিকোয়েস্ট সফলভাবে জমা হয়েছে!")

if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
