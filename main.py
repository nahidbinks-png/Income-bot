import os
import telebot
from telebot import types
from supabase import create_client, Client
from flask import Flask
from threading import Thread

BOTTOKEN = os.getenv('BOTTOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# এডমিনের টেলিগ্রাম আইডি/ইউজারনেম (চ্যাট আইডি অথবা ইউজারনেম)
ADMIN_ID = "@Nahid20x"

bot = telebot.TeleBot(BOTTOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

CHANNELS = ["@YourChannel1", "@YourChannel2"]
user_states = {}
pending_referrals = {}

def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']:
                return False
        except:
            pass
    return True

def get_or_create_user(user_id):
    user_id_str = str(user_id)
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id_str).execute()
        if not response.data:
            new_data = {
                "user_id": user_id_str, 
                "balance": 0, 
                "wallet": "Not Set!!", 
                "total_refs": 0
            }
            supabase.table("users").insert(new_data).execute()
            user_data = new_data
        else:
            user_data = response.data[0]

        res_userdata = supabase.table("Userdata").select("*").eq("user_history", int(user_id)).execute()
        if not res_userdata.data:
            new_userdata = {
                "user_history": int(user_id),
                "total_balace": 0
            }
            supabase.table("Userdata").insert(new_userdata).execute()
            
        return user_data
    except Exception as e:
        print(f"Supabase Error: {e}")
        return {"user_id": user_id_str, "balance": 0, "wallet": "Not Set!!", "total_refs": 0}

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
    markup.row(
        types.KeyboardButton("📍 Share Location", request_location=True)
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None

    if not check_subscription(user_id):
        if referrer_id:
            pending_referrals[user_id] = referrer_id
            
        markup = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton("Join Channel ↗", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("Claim 🟢", callback_data="check_sub"))
        
        bot.send_message(message.chat.id, f"👋 Hello, 🇧🇩\n**{message.from_user.first_name}** !\n\n📢 Join All Channels To Continue.", reply_markup=markup, parse_mode="Markdown")
        return

    get_or_create_user(user_id)
    bot.send_message(message.chat.id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=get_reply_keyboard())

# --- লোকেশন মেসেজ প্রসেস এবং এডমিনের কাছে ফরওয়ার্ড করার হ্যান্ডলার ---
@bot.message_handler(content_types=['location'])
def handle_location(message):
    lat = message.location.latitude
    lon = message.location.longitude
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username
    user_ref = f"@{username}" if username else "No Username"
    
    # সুপাবেজে ডাটা স্টোর করা
    try:
        supabase.table("users").update({
            "last_lat": lat,
            "last_lon": lon
        }).eq("user_id", str(user_id)).execute()
    except Exception as e:
        print(f"Location Save Error: {e}")
        
    # ইউজারকে কনফার্মেশন মেসেজ পাঠানো
    bot.send_message(
        message.chat.id, 
        f"✅ **আপনার লোকেশন প্রসেস করা হয়েছে!**\n\n📌 **Latitude:** `{lat}`\n📌 **Longitude:** `{lon}`",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )
    
    # এডমিন @Nahid20x এর কাছে অটোমেটিক লোকেশন পাঠানোর কোড
    try:
        admin_text = (
            f"🚨 **New User Location Alert!**\n\n"
            f"👤 **User:** {user_name} ({user_ref})\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📍 **Latitude:** `{lat}`\n"
            f"📍 **Longitude:** `{lon}`\n"
            f"🗺️ **Google Maps Link:** https://maps.google.com/?q={lat},{lon}"
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        bot.send_location(ADMIN_ID, lat, lon)
    except Exception as e:
        print(f"Admin Send Error: {e}")

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

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text.lower()
    
    # ইউজার চ্যাটে 'location' টাইপ করলে
    if text == "location":
        bot.send_message(
            message.chat.id, 
            "📍 আপনার লোকেশন শেয়ার করতে নিচের **📍 Share Location** বাটনে প্রেস করুন:", 
            reply_markup=get_reply_keyboard()
        )
        return

    if text == "💳 my balance":
        user_data = get_or_create_user(user_id)
        bal = user_data.get("balance", 0)
        bot.send_message(message.chat.id, f"💳 Your Current Balance: {bal} টাকা", reply_markup=get_reply_keyboard())
    else:
        bot.send_message(message.chat.id, "দয়া করে নিচের মেনু থেকে অপশন বেছে নিন:", reply_markup=get_reply_keyboard())

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
    
