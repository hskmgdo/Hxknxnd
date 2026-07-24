import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
import time
import json
import sqlite3
import logging
import os
import random
import hashlib
from datetime import datetime

# ========== تنظیمات اصلی ==========
BOT_TOKEN = "8423981755:AAFaEYzOefEaxDiuyvKKyyTJzlhDXWSqyRw"
ADMIN_ID = 8680457924  # آیدی عددی شما
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ========== تنظیمات لاگینگ ==========
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('vpn_bot.log')``` logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ========== کانفیگ‌های WhiteDNS ==========
WHITEDNS_CONFIGS = [
    """stormdns://eyJzY2hlbWEiOiJ3aGl0ZWRucy5wcm9maWxlIiwidmVyc2lvbiI6MSwicHJvZmlsZSI6eyJuYW1lIjoicmV6YSBncm9vdHoiLCJzZXJ2ZXIiOnsiZG9tYWluIjoidi5hcmFza2hhdGFyZS5nZ2ZmLm5ldCIsImVuY3J5cHRpb25fa2V5IjoiZWQwY2VmMTZiNzE1M2I4ZDgzNWEzMjc4NjE1OTdjNjQiLCJlbmNyeXB0aW9uX21ldGhvZCI6MX19fX0"""```
    
    """stormdns://eyJzY2hlbWEiOiJ3aGl0ZWRucy5wcm9maWxlIiwidmVyc2lvbiI6MSwicHJvZmlsZSI6eyJuYW1lIjoicmV6YSBncm9vdHoiLCJzZXJ2ZXIiOnsiZG9tYWluIjoidi5hbm9ueW1vdXMub2JzZXJ2ZXIiLCJlbmNyeXB0aW9uX2tleSI6ImIyNzUwMzkxOTliMWM4YzkiLCJlbmNyeXB0aW9uX21ldGhvZCI6M319fX0"""
]

# ========== دیتابیس ساده ==========
class Database:
    def __init__(self, db_file='users.db'):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date INTEGER,
                last_seen INTEGER
            )
        ''')
        self.conn.commit()
    
    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor
    
    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()
    
    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def close(self):
        self.conn.close()

db = Database()

# ========== توابع کمکی ==========
def create_user(user_id, username=None, first_name=None):
    """ثبت کاربر جدید در دیتابیس"""
    now = int(time.time())
    db.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, join_date, last_seen)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, first_name, now, now))
    
    # به‌روزرسانی last_seen
    db.execute("UPDATE users SET last_seen = ? WHERE user_id = ?", (now, user_id))

def get_user(user_id):
    """دریافت اطلاعات کاربر"""
    row = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if row:
        return dict(row)
    return None

def format_time(timestamp):
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    return "نامحدود"

def format_bytes(bytes_val):
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1048576:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1073741824:
        return f"{bytes_val / 1048576:.1f} MB"
    elif bytes_val < 1099511627776:
        return f"{bytes_val / 1073741824:.1f} GB"
    else:
        return f"{bytes_val / 1099511627776:.1f} TB"

# ========== کیبوردها ==========
def main_menu():
    """منوی اصلی ربات"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🌐 دریافت کانفیگ WhiteDNS", callback_data="get_whitedns"),
        InlineKeyboardButton("🪄 دریافت سرور اختصاصی GROOTZ", url="https://t.me/Grootz_Support"),
        InlineKeyboardButton("ℹ️ راهنما", callback_data="help"),
        InlineKeyboardButton("📊 وضعیت من", callback_data="my_status")
    )
    return keyboard

def get_back_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return keyboard

# ========== دستورات اصلی ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user = message.from_user
    user_id = user.id
    
    # ثبت کاربر
    create_user(user_id, user.username, user.first_name)
    
    text = f"""
🚀 **ربات VPN WhiteDNS** 🚀
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {user.first_name}
🆔 **آیدی:** `{user_id}`
━━━━━━━━━━━━━━━━━━━━━━

✨ **به ربات خوش آمدید!**

🔹 با کلیک روی دکمه زیر می‌توانید کانفیگ‌های WhiteDNS را دریافت کنید.
🔹 این کانفیگ‌ها کاملاً رایگان و بدون محدودیت هستند.

📌 **نکته:** برای دریافت سرور اختصاصی، از دکمه مخصوص استفاده کنید.
"""
    bot.reply_to(message, text, reply_markup=main_menu(), parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    text = """
📚 **راهنمای ربات WhiteDNS**
━━━━━━━━━━━━━━━━━━━━━━

**دستورات اصلی:**
/start - شروع و منوی اصلی
/help - این راهنما

**نحوه استفاده:**
1. روی دکمه "دریافت کانفیگ WhiteDNS" کلیک کنید
2. دو کانفیگ برای شما ارسال می‌شود
3. کانفیگ را در اپلیکیشن مورد نظر وارد کنید

**پشتیبانی:**
برای دریافت سرور اختصاصی یا سوالات بیشتر، از دکمه "دریافت سرور اختصاصی GROOTZ" استفاده کنید.
"""
    bot.reply_to(message, text, reply_markup=get_back_button(), parse_mode='HTML')

# ========== هندلرهای دکمه‌ها ==========
@bot.callback_query_handler(func=lambda call: call.data == "get_whitedns")
def handle_get_whitedns(call):
    user_id = call.from_user.id
    
    # ثبت کاربر
    create_user(user_id, call.from_user.username, call.from_user.first_name)
    
    text = f"""
🌐 **کانفیگ‌های WhiteDNS شما**
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {call.from_user.first_name}
━━━━━━━━━━━━━━━━━━━━━━

📋 **کانفیگ شماره ۱:**
<code>{WHITEDNS_CONFIGS[0]}</code>

━━━━━━━━━━━━━━━━━━━━━━

📋 **کانفیگ شماره ۲:**
<code>{WHITEDNS_CONFIGS[1]}</code>

━━━━━━━━━━━━━━━━━━━━━━

📌 **نحوه استفاده:**
1. کانفیگ را کپی کنید
2. در اپلیکیشن خود وارد کنید
3. از اتصال مطمئن شوید

✅ این کانفیگ‌ها کاملاً رایگان هستند.
"""
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🪄 دریافت سرور اختصاصی GROOTZ", url="https://t.me/Grootz_Support"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=keyboard, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "my_status")
def handle_my_status(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, call.from_user.username, call.from_user.first_name)
        user = get_user(user_id)
    
    text = f"""
📊 **وضعیت حساب کاربری**
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {call.from_user.first_name}
🆔 **آیدی:** `{user_id}`
📅 **تاریخ عضویت:** {format_time(user['join_date'])}
━━━━━━━━━━━━━━━━━━━━━━

✅ **وضعیت:** فعال
📋 **کانفیگ‌های دریافتی:** ۲ عدد (WhiteDNS)
🚀 **سرور اختصاصی:** در صورت نیاز از پشتیبانی دریافت کنید
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "help")
def handle_help_callback(call):
    text = """
📚 **راهنمای ربات WhiteDNS**
━━━━━━━━━━━━━━━━━━━━━━

🔹 این ربات برای دریافت کانفیگ‌های رایگان WhiteDNS طراحی شده است.

**مراحل استفاده:**
1. روی دکمه "دریافت کانفیگ WhiteDNS" کلیک کنید
2. دو کانفیگ دریافت می‌کنید
3. کانفیگ را در اپلیکیشن خود وارد کنید

**کانفیگ‌ها:**
• کاملاً رایگان
• بدون محدودیت ترافیک
• سرعت بالا

**سرور اختصاصی:**
برای دریافت سرور اختصاصی با سرعت بالاتر، از دکمه "دریافت سرور اختصاصی GROOTZ" استفاده کنید.

📞 **پشتیبانی:** @Grootz_Support
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def handle_back_main(call):
    text = f"""
🚀 **ربات VPN WhiteDNS** 🚀
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {call.from_user.first_name}
━━━━━━━━━━━━━━━━━━━━━━

✨ **منوی اصلی:**
• دریافت کانفیگ WhiteDNS
• دریافت سرور اختصاصی
• راهنما
• وضعیت من
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=main_menu(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

# ========== پیام‌های متنی ==========
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    """هندلر پیام‌های متنی"""
    text = message.text.lower()
    
    if text in ["سلام", "سلامت", "هی", "hi", "hello"]:
        bot.reply_to(message, f"سلام {message.from_user.first_name} 👋\nاز منوی زیر استفاده کنید:", reply_markup=main_menu())
    elif text in ["خوبی", "چطوری"]:
        bot.reply_to(message, "من خوبم ممنون! 😊\nچطور می‌توانم کمکت کنم؟")
    elif "کانفیگ" in text or "وایت" in text or "whitedns" in text:
        bot.reply_to(message, "🌐 برای دریافت کانفیگ‌های WhiteDNS، روی دکمه زیر کلیک کنید:", 
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🌐 دریافت کانفیگ WhiteDNS", callback_data="get_whitedns")
                    ))
    elif "سرور" in text or "اختصاصی" in text or "گروتز" in text or "grootz" in text:
        bot.reply_to(message, "🪄 برای دریافت سرور اختصاصی GROOTZ، روی لینک زیر کلیک کنید:\n@Grootz_Support",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🪄 دریافت سرور اختصاصی GROOTZ", url="https://t.me/Grootz_Support")
                    ))
    elif "راهنما" in text or "help" in text:
        help_command(message)
    else:
        bot.reply_to(message, f"سلام {message.from_user.first_name} 👋\nاز منوی زیر استفاده کنید یا دستور /help را بزنید.", 
                    reply_markup=main_menu())

# ========== اجرا ==========
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات VPN WhiteDNS 🚀")
    print("=" * 70)
    print("✅ کانفیگ‌های WhiteDNS آماده ارسال")
    print("✅ دکمه سرور اختصاصی به پیوی شما متصل است")
    print("=" * 70)
    print("🔄 ربات در حال اجرا...")
    print("👤 ادمین: @Grootz_Support")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            print("🔄 راه‌اندازی مجدد در 5 ثانیه...")
            time.sleep(5)
            continue
