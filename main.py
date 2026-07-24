import telebot
from telebot.types import Message
import time
import json
import random
import re
from datetime import datetime
import logging

# ========== توکن ربات ==========
BOT_TOKEN = "8423981755:AAFaEYzOefEaxDiuyvKKyyTJzlhDXWSqyRw"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ========== لاگینگ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== اطلاعات ادمین ==========
ADMIN_NAME = "Reza Grootz"
ADMIN_USERNAME = "@Grootz_Support"
ADMIN_ID = 8680457924

# ========== دیتابیس هوشمند پاسخ‌ها ==========
class SmartReplies:
    def __init__(self):
        self.responses = {
            # احوالپرسی
            "سلام": [
                "سلام عزیزم! 😍 چطور می‌تونم امروز بهت کمک کنم؟",
                "سلام رضا جان! 🌟 خوش اومدی، چه کاری برات انجام بدم؟",
                "سلام بر بهترین! 🚀 آماده‌ام تا بهت خدمت کنم",
                "سلام گلم! ❤️ چطوره اوضاع؟",
                "سلام داداش! 🔥 بیا ببینم چیکار می‌تونم برات بکنم"
            ],
            "خوبی": [
                "ممنون که پرسیدی عزیزم! ❤️ من که با دیدن تو عالی شدم! تو چطوری؟",
                "فوق‌العاده‌م داداش! 🌟 حالا که تو اینجایی بهترم شد!",
                "بهترینم! 😎 راستی تو چطوری؟ دلم برات تنگ شده بود",
                "خوبم ممنون رضا جان! 🚀 حالا که پیام دادی عالی تر شدم!"
            ],
            "چطوری": [
                "من که با دیدن تو فوق‌العاده‌م! 😍 تو چطوری رضا جان؟",
                "بهترین حالت ممکن! 🌟 حالا که تو هستی دیگه عالی تر از این نمیشه",
                "خوبم ممنون عزیزم! ❤️ راستی خبر خاصی داری؟",
                "فوق‌العاده‌م! 🚀 حاضرم هر کاری برات بکنم"
            ],
            "ممنون": [
                "خواهش می‌کنم عزیزم! ❤️ همیشه در خدمت شما هستم",
                "قربانت داداش! 🌟 هر وقت نیاز بود در خدمتم",
                "چشمت روشاد! 😎 خوشحالم که تونستم کمکت کنم",
                "افتخار من بود رضا جان! 🚀 هر کاری ازم بربیاد انجام می‌دم"
            ],
            "خدافظ": [
                "خدافظ عزیزم! ❤️ منتظرت هستم، هر وقت نیاز بود بیا",
                "به امید دیدار دوباره! 🌟 مواظب خودت باش رضا جان",
                "خدافظ گلم! 🚀 همیشه برات بهترین‌ها رو آرزو می‌کنم",
                "قربونت برم! ❤️ زود برگرد دلم برات تنگ میشه"
            ],
            
            # خدمات و کانفیگ
            "کانفیگ": [
                "🌐 **کانفیگ‌های WhiteDNS آماده‌ست!**\n\n"
                "۱. `stormdns://eyJzY2hlbWEiOiJ3aGl0ZWRucy5wcm9maWxlIiwidmVyc2lvbiI6MSwicHJvZmlsZSI6eyJuYW1lIjoicmV6YSBncm9vdHoiLCJzZXJ2ZXIiOnsiZG9tYWluIjoidi5hcmFza2hhdGFyZS5nZ2ZmLm5ldCIsImVuY3J5cHRpb25fa2V5IjoiZWQwY2VmMTZiNzE1M2I4ZDgzNWEzMjc4NjE1OTdjNjQiLCJlbmNyeXB0aW9uX21ldGhvZCI6MX19fX0`\n\n"
                "۲. `stormdns://eyJzY2hlbWEiOiJ3aGl0ZWRucy5wcm9maWxlIiwidmVyc2lvbiI6MSwicHJvZmlsZSI6eyJuYW1lIjoicmV6YSBncm9vdHoiLCJzZXJ2ZXIiOnsiZG9tYWluIjoidi5hbm9ueW1vdXMub2JzZXJ2ZXIiLCJlbmNyeXB0aW9uX2tleSI6ImIyNzUwMzkxOTliMWM4YzkiLCJlbmNyeXB0aW9uX21ldGhvZCI6M319fX0`\n\n"
                "📌 این کانفیگ‌ها کاملاً رایگان و بدون محدودیت هستن!",
                
                "🔥 **کانفیگ‌های سفارشی مخصوص تو!**\n\n"
                "همین الان ۲ تا کانفیگ رایگان WhiteDNS برات می‌فرستم:\n"
                "۱. `stormdns://eyJzY2hlbWEiOiJ3aGl0ZWRucy5wcm9maWxlIiwidmVyc2lvbiI6MSwicHJvZmlsZSI6eyJuYW1lIjoicmV6YSBncm9vdHoiLCJzZXJ2ZXIiOnsiZG9tYWluIjoidi5hcmFza2hhdGFyZS5nZ2ZmLm5ldCIsImVuY3J5cHRpb25fa2V5IjoiZWQwY2VmMTZiNzE1M2I4ZDgzNWEzMjc4NjE1OTdjNjQiLCJlbmNyeXB0aW9uX21ldGhvZCI6MX19fX0`\n\n"
                "۲. `stormdns://eyJzY2hlbWEiOiJ3aGl0ZWRucy5wcm9maWxlIiwidmVyc2lvbiI6MSwicHJvZmlsZSI6eyJuYW1lIjoicmV6YSBncm9vdHoiLCJzZXJ2ZXIiOnsiZG9tYWluIjoidi5hbm9ueW1vdXMub2JzZXJ2ZXIiLCJlbmNyeXB0aW9uX2tleSI6ImIyNzUwMzkxOTliMWM4YzkiLCJlbmNyeXB0aW9uX21ldGhvZCI6M319fX0`"
            ],
            
            "سرور اختصاصی": [
                "🪄 **سرور اختصاصی GROOTZ**\n\n"
                "برای دریافت سرور اختصاصی با سرعت بالا و پشتیبانی ۲۴/۷، همین الان با من تماس بگیر:\n"
                f"👤 {ADMIN_NAME}\n"
                f"📱 {ADMIN_USERNAME}",
                
                "🔥 **سرور اختصاصی فوق‌العاده!**\n\n"
                "💎 سرعت بالا\n"
                "🔒 امنیت کامل\n"
                "🛡️ پشتیبانی ویژه\n"
                "📞 برای اطلاعات بیشتر با من تماس بگیر:\n"
                f"{ADMIN_USERNAME}"
            ],
            
            "قیمت": [
                "💰 **تعرفه‌های ویژه GROOTZ**\n\n"
                "🔹 کانفیگ رایگان WhiteDNS: رایگان ♾️\n"
                "🔹 سرور اختصاصی پایه: تماس بگیرید\n"
                "🔹 سرور اختصاصی حرفه‌ای: تماس بگیرید\n"
                "🔹 سرور اختصاصی بیزینس: تماس بگیرید\n\n"
                f"📞 برای مشاوره: {ADMIN_USERNAME}",
                
                "💎 **پکیج‌های ویژه**\n\n"
                "🔸 ماهیانه با تخفیف ویژه\n"
                "🔸 ۳ ماهه با هدیه کانفیگ رایگان\n"
                "🔸 ۶ ماهه با ۲۰٪ تخفیف\n"
                "🔸 ۱۲ ماهه با ۳۰٪ تخفیف + پشتیبانی VIP\n\n"
                f"📞 {ADMIN_USERNAME}"
            ],
            
            "پشتیبانی": [
                f"🛡️ **پشتیبانی ۲۴/۷ GROOTZ**\n\n"
                "ما همیشه در کنار شما هستیم!\n"
                "⏰ پاسخگویی: کمتر از ۵ دقیقه\n"
                "📞 تماس با پشتیبانی:\n"
                f"{ADMIN_USERNAME}",
                
                "🎯 **تیم پشتیبانی حرفه‌ای**\n\n"
                "✅ رفع سریع مشکلات\n"
                "✅ مشاوره رایگان\n"
                "✅ آموزش نصب و راه‌اندازی\n\n"
                f"📞 {ADMIN_USERNAME}"
            ]
        }
        
        # کلمات کلیدی برای تشخیص خودکار
        self.keywords = {
            "سلام": ["سلام", "درود", "هی", "hey", "hi", "hello"],
            "خوبی": ["خوبی", "چطوری", "چطورین", "حالت", "احوالت"],
            "ممنون": ["ممنون", "مرسی", "متشکرم", "thanks", "thank"],
            "خدافظ": ["خدافظ", "خدا حافظ", "بای", "bye", "goodbye"],
            "کانفیگ": ["کانفیگ", "config", "وایت", "whitedns", "رایگان"],
            "سرور اختصاصی": ["سرور", "اختصاصی", "special", "dedicated", "vip"],
            "قیمت": ["قیمت", "هزینه", "پول", "چند", "قیمتش"],
            "پشتیبانی": ["پشتیبانی", "support", "کمک", "راهنما"]
        }
    
    def get_response(self, text):
        """دریافت پاسخ مناسب برای پیام کاربر"""
        text_lower = text.lower()
        
        # بررسی کلمات کلیدی
        for category, words in self.keywords.items():
            for word in words:
                if word in text_lower:
                    response_list = self.responses.get(category, [])
                    if response_list:
                        return random.choice(response_list)
        
        # پاسخ‌های عمومی برای موارد دیگر
        general_responses = [
            "😎 **رضا جان!** سوالت رو کامل‌تر بپرس تا بهترین پاسخ رو بدم!\n\n"
            f"📞 برای مشاوره فوری: {ADMIN_USERNAME}",
            
            "🔥 **عالی!** سوال خوبی پرسیدی!\n\n"
            "💡 می‌تونی درباره این موضوعات بپرسی:\n"
            "• کانفیگ رایگان WhiteDNS\n"
            "• سرور اختصاصی\n"
            "• قیمت و تعرفه‌ها\n"
            "• پشتیبانی",
            
            "🌟 **رضا GROOTZ** همیشه آماده کمک به شماست!\n\n"
            "چیزی که نیاز داری رو بگو تا بهترین راهکار رو بهت بدم.",
            
            f"💎 **سوال عالی!**\n\n"
            f"برای دریافت پاسخ دقیق‌تر، می‌تونی به {ADMIN_USERNAME} پیام بدی.",
            
            "🚀 **خوشحالم که سوال می‌پرسی!**\n\n"
            "هر چیزی که نیاز داری رو بگو، من بهترین پاسخ رو می‌دم."
        ]
        
        return random.choice(general_responses)

# ========== ایجاد نمونه ==========
smart_replies = SmartReplies()

# ========== هندلر پیام‌ها ==========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message: Message):
    """هندلر هوشمند همه پیام‌ها"""
    user = message.from_user
    text = message.text or ""
    
    # لاگ کردن
    logger.info(f"پیام از {user.first_name} (@{user.username}): {text[:50]}")
    
    # دریافت پاسخ هوشمند
    response = smart_replies.get_response(text)
    
    # ارسال پاسخ
    try:
        bot.reply_to(message, response, parse_mode='HTML')
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ: {e}")
        bot.reply_to(message, f"❌ یه مشکلی پیش اومد! لطفاً دوباره تلاش کن یا به {ADMIN_USERNAME} پیام بده.")

# ========== دستورات ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user = message.from_user
    text = f"""
🚀 **به ربات حرفه‌ای {ADMIN_NAME} خوش اومدی!** 🚀
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {user.first_name}
🆔 **آیدی:** `{user.id}`
━━━━━━━━━━━━━━━━━━━━━━

🔥 **من اینجام تا بهترین خدمات رو بهت بدم!**

💡 **چی کار می‌تونم برات بکنم؟**
• 🌐 کانفیگ رایگان WhiteDNS
• 🪄 سرور اختصاصی VIP
• 💰 مشاوره قیمت
• 🛡️ پشتیبانی ۲۴/۷

📌 **فقط کافیه هر چیزی که نیاز داری بپرسی!**

{ADMIN_USERNAME} - منتظرت هستم ❤️
"""
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    text = f"""
📚 **راهنمای ربات {ADMIN_NAME}**
━━━━━━━━━━━━━━━━━━━━━━

🔹 **این ربات چیکار می‌کنه؟**
یه دستیار هوشمند که به تمام سوالات شما درباره خدمات VPN پاسخ می‌ده!

💬 **چی می‌تونم بپرسم؟**
• کانفیگ رایگان WhiteDNS
• سرور اختصاصی
• قیمت‌ها و تخفیف‌ها
• پشتیبانی و راهنما
• هر چیز دیگه‌ای که نیاز دارید!

🎯 **ویژگی‌ها:**
• پاسخ‌دهی هوشمند
• سرعت بالا
• ۲۴/۷ فعال

📞 **پشتیبانی:** {ADMIN_USERNAME}
"""
    bot.reply_to(message, text, parse_mode='HTML')

# ========== اجرا ==========
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات هوشمند Reza Grootz 🚀")
    print("=" * 70)
    print(f"👤 ادمین: {ADMIN_NAME}")
    print(f"📱 {ADMIN_USERNAME}")
    print("=" * 70)
    print("✅ پاسخ‌دهی هوشمند فعال شد!")
    print("✅ آماده پاسخگویی به همه پیام‌ها")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            print("🔄 راه‌اندازی مجدد در 5 ثانیه...")
            time.sleep(5)
            continue
