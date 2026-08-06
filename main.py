import os
import telebot
from telebot import types
from supabase import create_client, Client
from flask import Flask
from threading import Thread

BOTTOKEN = os.getenv('BOTTOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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
        # ১. আগের 'users' টেবিল হ্যান্ডেল করা
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

        # ২. নতুন 'Userdata' টেবিল হ্যান্ডেল করা (আপনার টেবিলের কলাম অনুযায়ী)
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

    if referrer_id:
        if str(referrer_id) != str(user_id):
            try:
                ref_user_data = get_or_create_user(referrer_id)
                current_bal = int(ref_user_data.get("balance", 0))
                current_refs = int(ref_user_data.get("total_refs", 0))
                
                # users টেবিলে আপডেট
                supabase.table("users").update({
                    "balance": current_bal + 1, 
                    "total_refs": current_refs + 1
                }).eq("user_id", str(referrer_id)).execute()

                # নতুন Userdata টেবিলেও ব্যালেন্স আপডেট করা
                try:
                    ud_res = supabase.table("Userdata").select("*").eq("user_history", int(referrer_id)).execute()
                    if ud_res.data:
                        old_tb = int(ud_res.data[0].get("total_balace", 0))
                        supabase.table("Userdata").update({"total_balace": old_tb + 1}).eq("user_history", int(referrer_id)).execute()
                except:
                    pass
                
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
            
            if user_id in pending_referrals:
                referrer_id = pending_referrals.pop(user_id)
                if str(referrer_id) != str(user_id):
                    try:
                        ref_user_data = get_or_create_user(referrer_id)
                        current_bal = int(ref_user_data.get("balance", 0))
                        current_refs = int(ref_user_data.get("total_refs", 0))
                        
                        supabase.table("users").update({
                            "balance": current_bal + 1, 
                            "total_refs": current_refs + 1
                        }).eq("user_id", str(referrer_id)).execute()
                        
                        try:
                            ud_res = supabase.table("Userdata").select("*").eq("user_history", int(referrer_id)).execute()
                            if ud_res.data:
                                old_tb = int(ud_res.data[0].get("total_balace", 0))
                                supabase.table("Userdata").update({"total_balace": old_tb + 1}).eq("user_history", int(referrer_id)).execute()
                        except:
                            pass

                        bot.send_message(referrer_id, "💰 আপনার বটে নতুন ১টি রেফার হয়েছে এবং আপনার ব্যালেন্স এ ১ টাকা যোগ করা হয়েছে 💰")
                    except Exception as e:
                        print(f"Pending Referral Error: {e}")

            bot.send_message(call.message.chat.id, "✨ মূল মেনুতে স্বাগতম:", reply_markup=get_reply_keyboard())
        else:
            bot.answer_callback_query(call.id, "⚠️ আগে সব চ্যানেলগুলোতে জয়েন করুন!", show_alert=True)
            
    elif call.data == "change_wallet":
        user_states[user_id] = "waiting_for_wallet"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📞 আপনার বিকাশ বা নগদ নম্বরটি এখন চ্যাটে লিখে পাঠান:")
        
    elif call.data == "reset_referrals":
        try:
            # উভয় টেবিল থেকেই ইউজারের ডাটা ডিলিট বা রিসেট করা
            supabase.table("users").delete().eq("user_id", str(user_id)).execute()
            supabase.table("Userdata").delete().eq("user_history", int(user_id)).execute()
            
            bot.answer_callback_query(call.id, "সফলভাবে রিসেট করা হয়েছে!")
            bot.send_message(call.message.chat.id, "🔄 আপনার অ্যাকাউন্ট সফলভাবে রিসেট করা হয়েছে। নতুন করে শুরু করতে /start কমান্ড দিন।", reply_markup=types.ReplyKeyboardRemove())
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
            supabase.table("users").update({"wallet": wallet_number}).eq("user_id", str(user_id)).execute()
            bot.send_message(message.chat.id, "✅ সফলভাবে আপনার ওয়ালেট নম্বর সেভ করা হয়েছে!", reply_markup=get_reply_keyboard())
        except Exception as e:
            bot.send_message(message.chat.id, "❌ ওয়ালেট সেভ করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।", reply_markup=get_reply_keyboard())
            print(f"Wallet Save Error: {e}")
        return

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
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Reset Referrals", callback_data="reset_referrals"))
        
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
    
    print("Bot is running with Flask and Supabase (Dual Tables)...")
    bot.infinity_polling()
