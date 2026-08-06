import os
import telebot
from telebot import types
from supabase import create_client, Client
from flask import Flask
from threading import Thread

# Render-এর Environment Variable থেকে টোকেন এবং সুপাবেজ ক্রিপডেনশিয়াল নেওয়া
BOTTOKEN = os.getenv('BOTTOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

bot = telebot.TeleBot(BOTTOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ফ্লাস্ক সার্ভার তৈরি (রেন্ডারের পোর্ট প্রবলেম সমাধানের জন্য)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# বাধ্যতামূলক চ্যানেলগুলোর লিস্ট
CHANNELS = ["@YourChannel1", "@YourChannel2"]

# ইউজার স্টেট ট্র্যাক করার জন্য ডিকশনারি
user_states = {}

def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']:
                return False
        except:
            pass
    return True

# সুপাবেজ থেকে ইউজারের ডাটা আনা বা না থাকলে তৈরি করা (সুপাবেজে সেভ রাখার জন্য)
def get_or_create_user(user_id):
    user_id_str = str(user_id)
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id_str).execute()
        if response.data:
            return response.data[0]
        else:
            new_data = {
                "user_id": user_id_str, 
                "balance": 0, 
                "wallet": "Not Set!!", 
                "total_refs": 0
            }
            supabase.table("users").insert(new_data).execute()
            return new_data
    except Exception as e:
        print(f"Supabase Error: {e}")
        return {"user_id": user_id_str, "balance": 0, "wallet": "Not Set!!", "total_refs": 0}

# স্থায়ী নিচের মেনু কিবোর্ড (Reply Keyboard) - সঠিকভাবে সারিতে সাজানো
def get_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("💳 My Balance"),
        types.KeyboardButton("👯 Refer & Earn")
    )
    markup.row(
        types.KeyboardButton("💎 Set Wallet"),
        types.KeyboardButton("💡 Cash Out")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    
    # চ্যানেল সাবস্ক্রাইব করা আছে কিনা চেক করা
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton("Join Channel ↗", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("Claim 🟢", callback_data="check_sub"))
        
        bot.send_message(message.chat.id, f"👋 Hello, 🇧🇩\n**{message.from_user.first_name}** !\n\n📢 Join All Channels To Continue.", reply_markup=markup, parse_mode="Markdown")
        return

    get_or_create_user(user_id)

    # রেফারেল হ্যান্ডেলিং
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if str(referrer_id) != str(user_id):
            try:
                ref_user = supabase.table("users").select("*").eq("user_id", referrer_id).execute()
                if ref_user.data:
                    current_data = ref_user.data[0]
                    current_bal = current_data.get("balance", 0)
                    current_refs = current_data.get("total_refs", 0)
                    
                    new_bal = current_bal + 1
                    new_refs = current_refs + 1
                    
                    # সুপাবেজে ইউজারের ব্যালেন্স এবং রেফার আপডেট করা
                    supabase.table("users").update({"balance": new_bal, "total_refs": new_refs}).eq("user_id", referrer_id).execute()
                    bot.send_message(referrer_id, "💰 আপনার বটে নতুন ১টি রেফার হয়েছে এবং আপনার ব্যালেন্স এ ১ টাকা যোগ করা হয়েছে 💰")
            except Exception as e:
                print(f"Referral Error: {e}")

    bot.send_message(message.chat.id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=get_reply_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "Verification Successful!")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            get_or_create_user(user_id)
            bot.send_message(call.message.chat.id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=get_reply_keyboard())
        else:
            bot.answer_callback_query(call.id, "⚠️ আগে সব চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            
    elif call.data == "change_wallet":
        user_states[user_id] = "waiting_for_wallet"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📞 আপনার বিকাশ বা নগদ নম্বরটি এখন চ্যাটে লিখে পাঠান:")
        
    elif call.data == "reset_data":
        # সুপাবেজ থেকে ইউজারের ডেটা রিসেট বা জিরো করা
        try:
            supabase.table("users").update({"balance": 0, "total_refs": 0, "wallet": "Not Set!!"}).eq("user_id", str(user_id)).execute()
            bot.answer_callback_query(call.id, "ডেটা সফলভাবে রিসেট করা হয়েছে!")
            bot.send_message(call.message.chat.id, "🔄 আপনার অ্যাকাউন্ট ডেটা (ব্যালেন্স ও রেফার) সফলভাবে রিসেট করা হয়েছে।", reply_markup=get_reply_keyboard())
        except Exception as e:
            bot.answer_callback_query(call.id, "রিসেট করতে সমস্যা হয়েছে!", show_alert=True)
            print(f"Reset Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    if user_states.get(user_id) == "waiting_for_wallet":
        wallet_number = text
        user_states.pop(user_id, None)
        
        try:
            # সুপাবেজে ওয়ালেট নম্বর সেভ করা
            supabase.table("users").update({"wallet": wallet_number}).eq("user_id", str(user_id)).execute()
            bot.send_message(message.chat.id, "✅ সফলভাবে আপনার ওয়ালেট নম্বর সুপাবেজে সেভ করা হয়েছে!", reply_markup=get_reply_keyboard())
        except Exception as e:
            bot.send_message(message.chat.id, "❌ ওয়ালেট সেভ করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", reply_markup=get_reply_keyboard())
            print(f"Wallet Save Error: {e}")
        return

    # নিচের Reply Keyboard এর বাটনগুলোর টেক্সট হ্যান্ডেলিং
    if text == "💳 My Balance":
        user_data = get_or_create_user(user_id)
        bal = user_data.get("balance", 0)
        bot.send_message(message.chat.id, f"💳 Your Current Balance: {bal} টাকা", reply_markup=get_reply_keyboard())
        
    elif text == "👯 Refer & Earn":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        user_data = get_or_create_user(user_id)
        total_refs = user_data.get("total_refs", 0)
        user_wallet = user_data.get("wallet", "Not Set!!")
        
        ref_text = (
            f"🆔 Your User ID: `{user_id}`\n"
            f"💼 Connected Wallet: {user_wallet}\n"
            "🎖️ Per Referral: 1 টাকা\n\n"
            f"🔗 Your Referral Link: {ref_link}\n\n"
            f"📊 Your Total Referrals: {total_refs} 📈\n\n"
            "🚫 Fake and cheat referrals will not be paid"
        )
        
        # রিসেট করার জন্য ইনলাইন বাটন যুক্ত করা হলো
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Reset Data", callback_data="reset_data"))
        
        bot.send_message(message.chat.id, ref_text, reply_markup=markup, parse_mode="Markdown")
        
    elif text == "💎 Set Wallet":
        user_data = get_or_create_user(user_id)
        current_w = user_data.get("wallet", "Not Set!!")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⚙️ Change Wallet", callback_data="change_wallet"))
        
        bot.send_message(message.chat.id, f"📝 Current Wallet: {current_w}", reply_markup=markup)
        
    elif text == "💡 Cash Out":
        user_data = get_or_create_user(user_id)
        bal = user_data.get("balance", 0)
        if bal < 10:
            bot.send_message(message.chat.id, "⚠️ আপনার ব্যালেন্স কম আছে। টাকা উত্তোলনের জন্য কমপক্ষে আপনার ব্যালেন্সের 10 টাকা থাকতে হবে ⚠️", reply_markup=get_reply_keyboard())
        else:
            bot.send_message(message.chat.id, "✅ আপনার ক্যাশআউট রিকোয়েস্ট সফলভাবে জমা হয়েছে!", reply_markup=get_reply_keyboard())
    else:
        bot.send_message(message.chat.id, "দয়া করে নিচের মেনু থেকে অপশন বেছে নিন:", reply_markup=get_reply_keyboard())

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    
    print("Bot is running with Flask and Supabase...")
    bot.infinity_polling()
