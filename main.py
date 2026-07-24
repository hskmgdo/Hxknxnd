from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random

# توکن رباتت رو اینجا بذار
TOKEN = "8423981755:AAFaEYzOefEaxDiuyvKKyyTJzlhDXWSqyRw"

# لیست پاسخ‌های خفن و خاص Reza Grootz
COOL_RESPONSES = [
    "اوه، این سوال بود؟ من تا حالا فکر می‌کردم گروتز هستم، نه گوگل! 😎",
    "ریزات گروتز اینجاست تا بهت بگه: آروم باش، من هندلش می‌کنم! 💪",
    "چه پیام قشنگی! ولی بازم از خود من خفن‌تر نیست 😏",
    "من ربات نیستم، من یک سبک زندگی‌ام! 🚀",
    "این پیام رو خوندم، ولی ترجیح می‌دم یه آهنگ بذارم برات 🎧",
    "اگه دنبال جواب هوشمندانه‌ای، باید صبر کنی تا کافیم تموم شه! ☕",
    "گروتز می‌گه: یا این پیام رو جدی بگیر، یا نه... هر دو خوبه 🤘",
    "من با ۱۰۰ تا ربات دیگه فرق دارم، چون من Reza Grootz هستم! 🦾",
    "خودکار؟ نه عزیزم، من خودِ خودکارم! 😉",
    "این پیام رو به حساب هنر من بذار، نه علم من! 🎨",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من Reza Grootz هستم. بیا ببینیم چقدر خفن می‌تونیم باشیم! 💥")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # انتخاب پاسخ تصادفی از لیست خفن‌ها
    response = random.choice(COOL_RESPONSES)
    await update.message.reply_text(response)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("ربات Reza Grootz روشن شد... 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()
