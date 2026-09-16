import os
import telebot
from telebot import types
from supabase import create_client, Client
from flask import Flask
from threading import Thread

BOTTOKEN = os.getenv('BOTTOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# এডমিনের টেলিগ্রাম আইডি বা ইউজারনেম
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
        types.KeyboardButton("📍 Send Location", request_location=True)
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=get_reply_keyboard())

# --- ইউজার লোকেশন পাঠালে এডমিনের কাছে যাওয়ার হ্যান্ডলার ---
@bot.message_handler(content_types=['location'])
def handle_location(message):
    lat = message.location.latitude
    lon = message.location.longitude
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username
    user_ref = f"@{username}" if username else "No Username"
    
    # ইউজারকে বার্তা
    bot.send_message(
        message.chat.id, 
        "✅ **আপনার লোকেশন এডমিনের কাছে পাঠানো হয়েছে!**",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )
    
    # এডমিন @Nahid20x এর কাছে অটোমেটিক ডাটা পাঠানো
    try:
        admin_text = (
            f"🚨 **New User Location Received!**\n\n"
            f"👤 **User:** {user_name} ({user_ref})\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📍 **Latitude:** `{lat}`\n"
            f"📍 **Longitude:** `{lon}`\n"
            f"🗺️ **Google Maps:** https://maps.google.com/?q={lat},{lon}"
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        bot.send_location(ADMIN_ID, lat, lon)
    except Exception as e:
        print(f"Admin Send Error: {e}")

# --- ইউজার টেক্সট মেসেজ হ্যান্ডলার ---
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    text = message.text.lower().strip()
    
    # ইউজার 'location' বা লোকেশন সংক্রান্ত কিছু লিখলে সরাসরি লোকেশন বাটনের পপআপ পাঠানো
    if "location" in text or text == "location":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📍 Share Current Location", request_location=True))
        
        bot.send_message(
            message.chat.id, 
            "👇 আপনার লোকেশন পাঠাতে নিচের **📍 Share Current Location** বাটনে ক্লিক করুন:", 
            reply_markup=markup
        )
        return

    bot.send_message(message.chat.id, "দয়া করে মেনু থেকে অপশন বেছে নিন:", reply_markup=get_reply_keyboard())

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
    
