import os
import telebot
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask
from threading import Thread

# পরিবেশগত ভ্যারিয়েবল (Render বা Local Environment থেকে নেবে)
BOTTOKEN = os.getenv('BOTTOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')

# মেইল সেন্ড করার জন্য আপনার একটি ব্যাকএন্ড SMTP জিমেইল ও অ্যাপ পাসওয়ার্ড
SMTP_EMAIL = os.getenv('SENDER_EMAIL', 'your_gmail@gmail.com')
SMTP_PASSWORD = os.getenv('SENDER_PASSWORD', 'your_16_digit_app_password')

bot = telebot.TeleBot(BOTTOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Temp Mail Bot is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ইউজার স্টেট ট্র্যাকিং
user_data = {}

# 1secmail API দিয়ে Temp Mail জেনারেট করার ফাংশন
def generate_temp_email():
    try:
        url = "https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1"
        res = requests.get(url).json()
        if res:
            return res[0]
    except Exception as e:
        print(f"Temp Mail Gen Error: {e}")
    return None

# ইমেইল পাঠানোর ব্যাকএন্ড ফাংশন
def send_email(sender_address, recipient_list, subject, message_body):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Temp Mail <{sender_address}>"
        msg['To'] = ", ".join(recipient_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))

        # SMTP সংযোগ (Gmail/Server SMTP)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

# /start কমান্ড হ্যান্ডলার
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # নতুন Temp Email তৈরি
    temp_email = generate_temp_email()
    if temp_email:
        user_data[user_id] = {'temp_email': temp_email}
        msg = (
            f"📧 **আপনার নতুন Temp Email তৈরি হয়েছে:**\n`{temp_email}`\n\n"
            "নিচের যেকোনো একটি অপশন বেছে নিন:"
        )
    else:
        msg = "⚠️ Temp Email তৈরি করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(telebot.types.KeyboardButton("✉️ Send Mail"), telebot.types.KeyboardButton("🔄 New Temp Email"))
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

# টেক্সট মেসেজ ও বাটন হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    text = message.text

    if text == "🔄 New Temp Email":
        temp_email = generate_temp_email()
        if temp_email:
            user_data[user_id] = {'temp_email': temp_email}
            bot.send_message(message.chat.id, f"✅ নতুন Temp Email জেনারেট হয়েছে:\n`{temp_email}`", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ ফাইল জেনারেট করতে ব্যর্থ হয়েছে।")

    elif text == "✉️ Send Mail":
        if user_id not in user_data or 'temp_email' not in user_data[user_id]:
            temp_email = generate_temp_email()
            user_data[user_id] = {'temp_email': temp_email}

        msg = (
            "📝 **ইমেইল পাঠানোর ফরম্যাট:**\n\n"
            "নিচের ফরম্যাটে মেসেজ লিখে পাঠান (কমা `,` দিয়ে একাধিক ইমেইল যোগ করতে পারবেন):\n\n"
            "`মেইল ১, মেইল ২ | সাবজেক্ট | আপনার মেসেজ`\n\n"
            "**উদাহরণ:**\n"
            "`test1@gmail.com, test2@gmail.com | টেস্ট ইমেইল | এটি একটি সাময়িক ইমেইল মেসেজ`"
        )
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif "|" in text:
        parts = text.split("|")
        if len(parts) >= 3:
            recipients = [email.strip() for email in parts[0].split(",") if email.strip()]
            subject = parts[1].strip()
            body = parts[2].strip()

            sender_temp = user_data.get(user_id, {}).get('temp_email', 'noreply@tempmail.com')

            bot.send_message(message.chat.id, "⏳ ইমেইল পাঠানো হচ্ছে...")

            success = send_email(sender_temp, recipients, subject, body)

            if success:
                bot.send_message(message.chat.id, f"✅ সফলভাবে **{len(recipients)}** জন প্রাপকের কাছে ইমেইল পাঠানো হয়েছে!\n\n**Sender:** `{sender_temp}`", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ ইমেইল পাঠাতে ব্যর্থ হয়েছে। সার্ভার সেটিংস চেক করুন।")
        else:
            bot.send_message(message.chat.id, "⚠️ ভুল ফরম্যাট! সঠিকভাবে `মেইল | বিষয় | মেসেজ` এভাবে লিখুন।")
    else:
        bot.send_message(message.chat.id, "দয়া করে মেনু থেকে অপশন সিলেক্ট করুন অথবা সঠিক ফরম্যাটে মেসেজ লিখুন।")

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
    
