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

# /start দিলে সরাসরি ডিসপ্লে চ্যাটে ইনলাইন বাটন আসবে
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn_email = types.InlineKeyboardButton("✉️ Send Email Option", callback_data="btn_send_email")
    markup.add(btn_email)
    
    # লোকেশন বাটনের জন্য রিপ্লাই কীবোর্ড
    reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reply_markup.add(types.KeyboardButton("📍 Share Location", request_location=True))

    bot.send_message(
        message.chat.id, 
        "✨ **Welcome!**\n\nইমেইল পাঠাতে নিচের **Send Email Option** বাটনে চাপ দিন এবং লোকেশন পাঠাতে নিচের কীবোর্ড বাটন ব্যবহার করুন।", 
        parse_mode="Markdown",
        reply_markup=markup
    )
    
    bot.send_message(
        message.chat.id,
        "👇 লোকেশন সেন্ড করার বাটন নিচে দেওয়া হলো:",
        reply_markup=reply_markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "btn_send_email")
def callback_send_email(call):
    msg_text = (
        "📝 **ইমেইল পাঠানোর নিয়ম:**\n\n"
        "নিচের ফরম্যাটে চ্যাটে লিখুন:\n"
        "`target@gmail.com | বিষয় | আপনার মেসেজ`\n\n"
        "*(একাধিক মেইলের জন্য কমা ব্যবহার করুন: `email1, email2 | subject | text`)*"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")

@bot.message_handler(content_types=['location'])
def handle_location(message):
    lat = message.location.latitude
    lon = message.location.longitude
    user_name = message.from_user.first_name
    username = message.from_user.username
    user_ref = f"@{username}" if username else "No Username"

    bot.send_message(message.chat.id, "✅ লোকেশন সফলভাবে এডমিনের কাছে পাঠানো হয়েছে!")

    try:
        admin_text = (
            f"🚨 **New Location!**\n\n"
            f"👤 **User:** {user_name} ({user_ref})\n"
            f"🗺️ **Maps:** https://maps.google.com/?q={lat},{lon}"
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        bot.send_location(ADMIN_ID, lat, lon)
    except Exception as e:
        print(f"Admin Error: {e}")

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
            bot.send_message(message.chat.id, "❌ ইমেইল পাঠাতে সমস্যা হয়েছে।")
    else:
        bot.send_message(message.chat.id, "⚠️ ভুল ফরম্যাট! সঠিকভাবে `email | subject | message` লিখুন।", parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
    
