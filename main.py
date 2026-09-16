import os
import telebot
from telebot import types
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask
from threading import Thread

BOTTOKEN = os.getenv('BOTTOKEN')
ADMIN_ID = "@Nahid20x"

# ব্যাকএন্ড ইমেইল সেটিংস
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

bot = telebot.TeleBot(BOTTOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# প্রধান মেনু (Reply Keyboard)
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("📍 Share Location", request_location=True))
    markup.row(types.KeyboardButton("✉️ Send Email Option"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "✨ স্বাগতম! নিচের যেকোনো অপশন বেছে নিন:", 
        reply_markup=get_main_keyboard()
    )

# --- ১. লোকেশন হ্যান্ডলার ---
@bot.message_handler(content_types=['location'])
def handle_location(message):
    lat = message.location.latitude
    lon = message.location.longitude
    user_name = message.from_user.first_name
    username = message.from_user.username
    user_ref = f"@{username}" if username else "No Username"

    bot.send_message(message.chat.id, "✅ আপনার লোকেশন সেন্ড করা হয়েছে!", reply_markup=get_main_keyboard())

    try:
        admin_text = (
            f"🚨 **New Location Received!**\n\n"
            f"👤 **User:** {user_name} ({user_ref})\n"
            f"🗺️ **Google Maps:** https://maps.google.com/?q={lat},{lon}"
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        bot.send_location(ADMIN_ID, lat, lon)
    except Exception as e:
        print(f"Admin Error: {e}")

# --- ২. ইমেইল অপশন ফিল্টার ও ডিসপ্লেতে Inline Button শো করা ---
@bot.message_handler(func=lambda message: message.text == "✉️ Send Email Option")
def show_email_button(message):
    # ডিসপ্লে মেসেজের নিচে ইনলাইন বাটন তৈরি
    inline_markup = types.InlineKeyboardMarkup()
    btn_how_to = types.InlineKeyboardButton("📝 ইমেইল পাঠানোর নিয়ম", callback_data="btn_send_instructions")
    inline_markup.add(btn_how_to)

    bot.send_message(
        message.chat.id,
        "✉️ **ইমেইল পাঠানোর জন্য নিচের বাটনে চাপ দিন:**",
        parse_mode="Markdown",
        reply_markup=inline_markup
    )

# ইনলাইন বাটনে চাপ দিলে যা ঘটবে (Callback Query)
@bot.callback_query_handler(func=lambda call: call.data == "btn_send_instructions")
def callback_send_email_instructions(call):
    msg_text = (
        "📝 **ইমেইল পাঠাতে নিচের ফরম্যাটে মেসেজ লিখে পাঠান:**\n\n"
        "`target@gmail.com | বিষয় | মূল মেসেজ`\n\n"
        "*(কমা দিয়ে একাধিক ইমেইলও যোগ করতে পারবেন)*"
    )
    bot.answer_callback_query(call.id, "ফরম্যাট দেখুন")
    bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")

# --- ৩. ইমেইল টেক্সট মেসেজ প্রসেস করা ---
@bot.message_handler(func=lambda message: "|" in message.text)
def handle_email_send(message):
    parts = message.text.split("|")
    if len(parts) >= 3:
        to_emails = [e.strip() for e in parts[0].split(",") if e.strip()]
        subject = parts[1].strip()
        body = parts[2].strip()

        bot.send_message(message.chat.id, "⏳ ইমেইল পাঠানো হচ্ছে...")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()

            bot.send_message(message.chat.id, f"✅ সফলভাবে **{len(to_emails)}** টি ঠিকানায় ইমেইল পাঠানো হয়েছে!", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, "❌ ইমেইল পাঠাতে সমস্যা হয়েছে। পাসওয়ার্ড বা সেটিংস চেক করুন।")
    else:
        bot.send_message(message.chat.id, "⚠️ ভুল ফরম্যাট! সঠিকভাবে `email | subject | message` লিখুন।", parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
    
