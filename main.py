import os
import telebot
from telebot import types
from supabase import create_client, Client

# Render-এর Environment Variable থেকে টোকেন এবং সুপাবেজ ক্রিপডেনশিয়াল নেওয়া
BOTTOKEN = os.getenv('BOTTOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

bot = telebot.TeleBot(BOTTOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# সুপাবেজ থেকে ইউজারের ডাটা আনা বা না থাকলে তৈরি করা
def get_or_create_user(user_id):
    user_id_str = str(user_id)
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id_str).execute()
        if response.data:
            return response.data[0]
        else:
            new_data = {"user_id": user_id_str, "balance": 0, "wallet": "Not Set!!"}
            supabase.table("users").insert(new_data).execute()
            return new_data
    except Exception as e:
        print(f"Supabase Error: {e}")
        return {"user_id": user_id_str, "balance": 0, "wallet": "Not Set!!"}

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

    # ইউজারকে ডাটাবেজে চেক বা রেজিস্টার করা
    get_or_create_user(user_id)

    # রেফারেল হ্যান্ডেলিং
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if str(referrer_id) != str(user_id):
            try:
                ref_user = supabase.table("users").select("*").eq("user_id", referrer_id).execute()
                if ref_user.data:
                    current_bal = ref_user.data[0].get("balance", 0)
                    new_bal = current_bal + 1
                    supabase.table("users").update({"balance": new_bal}).eq("user_id", referrer_id).execute()
                    bot.send_message(referrer_id, "💰 আপনার ব্যালেন্স এ ১ টাকা যোগ করা হয়েছে 💰")
            except Exception as e:
                print(f"Referral Error: {e}")

    main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    # সাবস্ক্রাইব চেক বাটন
    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "Verification Successful!")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            get_or_create_user(user_id)
            main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "⚠️ আগে সব চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            
    # ব্যালেন্স চেক বাটন
    elif call.data == "my_balance":
        user_data = get_or_create_user(user_id)
        bal = user_data.get("balance", 0)
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
        user_data = get_or_create_user(user_id)
        bal = user_data.get("balance", 0)
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
    # যদি ইউজার ভুলবশত কোনো কমান্ড বা অন্য কিছু পাঠায়
    if message.text and message.text.startswith('/'):
        return
        
    user_id = str(message.from_user.id)
    wallet_number = message.text
    
    try:
        supabase.table("users").update({"wallet": wallet_number}).eq("user_id", user_id).execute()
        bot.send_message(message.chat.id, "✅ সফলভাবে আপনার ওয়ালেট নম্বর সেভ করা হয়েছে!")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ ওয়ালেট সেভ করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
        print(f"Wallet Save Error: {e}")
        
    main_menu(message.chat.id)

if __name__ == '__main__':
    print("Bot is running with Supabase...")
    bot.infinity_polling()
