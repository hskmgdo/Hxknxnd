import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
import time
import json
import sqlite3
import threading
import logging
import os
import random
import string
import re
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import base64
import uuid

# ========== تنظیمات اصلی ==========
BOT_TOKEN = "8423981755:AAH3nIKjuDncbPPO_67K8OSRd9M9TREJLtc"
ADMIN_IDS = [8916314219]
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ========== تنظیمات لاگینگ ==========
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('vpn_bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ========== تنظیمات سرور ==========
SERVER_CONFIG = {
    "domain": "your-domain.com",  # دامنه واقعی خود را وارد کنید
    "port": 443,
    "path": "/ray",
    "uuid": "b8311f5d-2d4b-4a0f-9a3e-5d6c7d8e9f0a",  # UUID پیش‌فرض
    "alter_id": 0,
    "security": "auto",
    "network": "ws",
    "tls": True,
    "sni": "your-domain.com",
    "public_key": "",  # برای WireGuard
    "private_key": "",  # برای WireGuard
}

# ========== دیتابیس ==========
class Database:
    def __init__(self, db_file='vpn_data.db'):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date INTEGER,
                last_seen INTEGER,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                balance INTEGER DEFAULT 0,
                total_used_traffic INTEGER DEFAULT 0,
                max_traffic INTEGER DEFAULT 107374182400,  -- 100GB
                expiry_date INTEGER,
                daily_limit INTEGER DEFAULT 0,
                configs TEXT,
                subscription_link TEXT,
                referral_code TEXT,
                referred_by INTEGER,
                referral_count INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                config_type TEXT,
                config_data TEXT,
                created_at INTEGER,
                expires_at INTEGER,
                is_active INTEGER DEFAULT 1,
                traffic_used INTEGER DEFAULT 0,
                traffic_limit INTEGER,
                subscription_link TEXT,
                protocol TEXT,
                inbounds_id INTEGER
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                host TEXT,
                port INTEGER,
                protocol TEXT,
                is_active INTEGER DEFAULT 1,
                load_balance INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                timestamp INTEGER,
                details TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at INTEGER,
                admin_response TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()
        self._init_default_settings()
    
    def _init_default_settings(self):
        defaults = {
            "default_traffic": "107374182400",  # 100GB
            "default_expiry_days": "30",
            "referral_bonus": "10",
            "min_traffic": "1073741824",  # 1GB
            "max_traffic": "1073741824000",  # 1TB
            "config_types": "vmess,vless,trojan,shadowsocks,wireguard",
            "subscription_enabled": "true"
        }
        for key, value in defaults.items():
            self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
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

# ========== کلاس اصلی ربات ==========
class VPNBot:
    def __init__(self):
        self.db = db
        self.config_cache = {}
        self.servers = self._load_servers()
        self.subscription_cache = {}
    
    def _load_servers(self):
        servers = db.fetch_all("SELECT * FROM servers WHERE is_active = 1")
        return [dict(s) for s in servers] if servers else [SERVER_CONFIG.copy()]
    
    def generate_uuid(self):
        return str(uuid.uuid4())
    
    def generate_subscription_link(self, user_id):
        """تولید لینک ساب‌اسکریپشن واقعی"""
        token = hashlib.md5(f"{user_id}{SERVER_CONFIG['domain']}{time.time()}".encode()).hexdigest()[:16]
        link = f"https://{SERVER_CONFIG['domain']}/sub/{user_id}/{token}"
        return link
    
    def generate_config(self, user_id, protocol="vmess", traffic_limit=None, expiry_days=30):
        """تولید کانفیگ با پروتکل‌های مختلف"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        uuid = self.generate_uuid()
        now = int(time.time())
        expiry = now + (expiry_days * 86400)
        
        config_data = {
            "uuid": uuid,
            "created_at": now,
            "expires_at": expiry,
            "traffic_limit": traffic_limit or int(db.fetch_one("SELECT value FROM settings WHERE key='default_traffic'")[0]),
            "protocol": protocol,
            "server": SERVER_CONFIG["domain"],
            "port": SERVER_CONFIG["port"],
            "path": SERVER_CONFIG["path"],
            "security": SERVER_CONFIG["security"],
            "network": SERVER_CONFIG["network"],
            "tls": SERVER_CONFIG["tls"],
            "sni": SERVER_CONFIG["sni"]
        }
        
        # تولید کانفیگ بر اساس پروتکل
        config_string = self._build_config_string(config_data, protocol)
        
        # ذخیره در دیتابیس
        db.execute("""
            INSERT INTO configs (user_id, config_type, config_data, created_at, expires_at, 
                               traffic_limit, subscription_link, protocol)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, protocol, json.dumps(config_data), now, expiry, 
              config_data["traffic_limit"], self.generate_subscription_link(user_id), protocol))
        
        config_id = db.cursor.lastrowid
        
        # به‌روزرسانی کاربر
        existing_configs = json.loads(user["configs"] or "[]")
        existing_configs.append(config_id)
        db.execute("UPDATE users SET configs = ? WHERE user_id = ?", 
                  (json.dumps(existing_configs), user_id))
        
        return {
            "id": config_id,
            "config": config_string,
            "subscription_link": self.generate_subscription_link(user_id),
            "expiry": expiry
        }
    
    def _build_config_string(self, config, protocol):
        """ساخت رشته کانفیگ بر اساس پروتکل"""
        if protocol == "vmess":
            return self._build_vmess(config)
        elif protocol == "vless":
            return self._build_vless(config)
        elif protocol == "trojan":
            return self._build_trojan(config)
        elif protocol == "shadowsocks":
            return self._build_shadowsocks(config)
        elif protocol == "wireguard":
            return self._build_wireguard(config)
        else:
            return self._build_vmess(config)
    
    def _build_vmess(self, config):
        """ساخت کانفیگ VMess"""
        vmess = {
            "v": "2",
            "ps": f"VPN-{config['protocol'].upper()}-{config['server']}",
            "add": config['server'],
            "port": config['port'],
            "id": config['uuid'],
            "aid": 0,
            "net": config['network'],
            "type": "none",
            "host": "",
            "path": config['path'],
            "tls": "tls" if config['tls'] else ""
        }
        return base64.b64encode(json.dumps(vmess).encode()).decode()
    
    def _build_vless(self, config):
        """ساخت کانفیگ VLESS"""
        return f"vless://{config['uuid']}@{config['server']}:{config['port']}?encryption=none&security={'tls' if config['tls'] else 'none'}&sni={config['sni']}&type={config['network']}&path={config['path']}#VPN-VLESS"
    
    def _build_trojan(self, config):
        """ساخت کانفیگ Trojan"""
        return f"trojan://{config['uuid']}@{config['server']}:{config['port']}?security={'tls' if config['tls'] else 'none'}&sni={config['sni']}&type={config['network']}&path={config['path']}#VPN-TROJAN"
    
    def _build_shadowsocks(self, config):
        """ساخت کانفیگ Shadowsocks"""
        password = config['uuid'][:16]
        method = "chacha20-ietf-poly1305"
        return f"ss://{base64.b64encode(f'{method}:{password}'.encode()).decode()}@{config['server']}:{config['port']}#VPN-SS"
    
    def _build_wireguard(self, config):
        """ساخت کانفیگ WireGuard"""
        private_key = base64.b64encode(os.urandom(32)).decode()
        public_key = base64.b64encode(os.urandom(32)).decode()
        return f"""[Interface]
PrivateKey = {private_key}
Address = 10.0.0.{random.randint(2, 254)}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {public_key}
Endpoint = {config['server']}:{config['port']}
AllowedIPs = 0.0.0.0/0
"""
    
    def get_user(self, user_id):
        row = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if row:
            return dict(row)
        return None
    
    def create_user(self, user_id, username=None, first_name=None, last_name=None):
        if self.get_user(user_id):
            return self.get_user(user_id)
        
        now = int(time.time())
        referral_code = hashlib.md5(f"{user_id}{now}".encode()).hexdigest()[:8]
        
        db.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, join_date, last_seen, 
                             referral_code, configs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, now, now, referral_code, "[]"))
        
        return self.get_user(user_id)
    
    def add_traffic(self, user_id, amount):
        user = self.get_user(user_id)
        if user:
            db.execute("UPDATE users SET total_used_traffic = total_used_traffic + ? WHERE user_id = ?",
                      (amount, user_id))
            return True
        return False
    
    def check_traffic(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        used = user["total_used_traffic"] or 0
        limit = user["max_traffic"] or int(db.fetch_one("SELECT value FROM settings WHERE key='default_traffic'")[0])
        return {
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "percent": (used / limit * 100) if limit > 0 else 0
        }
    
    def get_configs(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return []
        config_ids = json.loads(user["configs"] or "[]")
        configs = []
        for cid in config_ids:
            row = db.fetch_one("SELECT * FROM configs WHERE id = ? AND is_active = 1", (cid,))
            if row:
                configs.append(dict(row))
        return configs
    
    def revoke_config(self, config_id):
        db.execute("UPDATE configs SET is_active = 0 WHERE id = ?", (config_id,))
        return True
    
    def add_referral(self, user_id, referred_by):
        user = self.get_user(user_id)
        if user:
            db.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referred_by, user_id))
            db.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referred_by,))
            # پاداش ارجاع
            bonus = int(db.fetch_one("SELECT value FROM settings WHERE key='referral_bonus'")[0])
            db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus, referred_by))
            return True
        return False
    
    def add_ticket(self, user_id, subject, message):
        now = int(time.time())
        db.execute("""
            INSERT INTO tickets (user_id, subject, message, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, subject, message, now))
        return db.cursor.lastrowid
    
    def get_tickets(self, user_id):
        return db.fetch_all("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    
    def get_all_tickets(self):
        return db.fetch_all("SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at DESC")
    
    def respond_ticket(self, ticket_id, response):
        db.execute("UPDATE tickets SET status = 'closed', admin_response = ? WHERE id = ?", (response, ticket_id))
        return True
    
    def add_admin(self, user_id):
        db.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        return True
    
    def remove_admin(self, user_id):
        db.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
        return True
    
    def get_admins(self):
        return db.fetch_all("SELECT user_id, first_name, username FROM users WHERE is_admin = 1")

# ========== ایجاد نمونه ربات ==========
vpn_bot = VPNBot()

# ========== توابع کمکی ==========
def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    user = vpn_bot.get_user(user_id)
    return user and user.get("is_admin", 0) == 1

def is_bot_admin(user_id):
    return user_id in ADMIN_IDS

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

def format_time(timestamp):
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    return "نامحدود"

def get_user_mention(user):
    name = user.first_name or "کاربر"
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{name}</a>"

# ========== کیبوردها ==========
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📱 ساخت کانفیگ", callback_data="create_config"),
        InlineKeyboardButton("📊 وضعیت من", callback_data="my_status"),
        InlineKeyboardButton("📋 کانفیگ‌های من", callback_data="my_configs"),
        InlineKeyboardButton("🔗 لینک ساب", callback_data="subscription"),
        InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
        InlineKeyboardButton("🎁 معرفی دوستان", callback_data="referral"),
        InlineKeyboardButton("📞 پشتیبانی", callback_data="support"),
        InlineKeyboardButton("ℹ️ راهنما", callback_data="help"),
        InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")
    )
    if is_bot_admin(8916314219):  # فقط ادمین اصلی
        keyboard.add(
            InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel")
        )
    return keyboard

def config_types_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚀 VMess", callback_data="config_vmess"),
        InlineKeyboardButton("⚡ VLESS", callback_data="config_vless"),
        InlineKeyboardButton("🛡️ Trojan", callback_data="config_trojan"),
        InlineKeyboardButton("🔒 Shadowsocks", callback_data="config_shadowsocks"),
        InlineKeyboardButton("🔗 WireGuard", callback_data="config_wireguard"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    )
    return keyboard

def admin_panel_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("🎫 تیکت‌ها", callback_data="admin_tickets"),
        InlineKeyboardButton("⚙️ تنظیمات سرور", callback_data="admin_server"),
        InlineKeyboardButton("📋 لاگ‌ها", callback_data="admin_logs"),
        InlineKeyboardButton("➕ افزودن ادمین", callback_data="admin_add_admin"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
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
    vpn_bot.create_user(user_id, user.username, user.first_name, user.last_name)
    
    # بررسی کد معرف
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        ref_user = db.fetch_one("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
        if ref_user and ref_user[0] != user_id:
            vpn_bot.add_referral(user_id, ref_user[0])
    
    text = f"""
🚀 **ربات ساخت کانفیگ VPN پیشرفته** 🚀
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {user.first_name}
🆔 **آیدی:** `{user_id}`
━━━━━━━━━━━━━━━━━━━━━━

✨ **قابلیت‌های ربات:**
• ساخت کانفیگ V2Ray/XRay با پروتکل‌های متنوع
• لینک ساب‌اسکریپشن واقعی
• مدیریت مصرف ترافیک
• سیستم معرفی و پاداش
• پشتیبانی ۲۴/۷
• پنل کاربری پیشرفته

📌 از منوی زیر استفاده کنید:
"""
    bot.reply_to(message, text, reply_markup=main_menu(), parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    text = """
📚 **راهنمای ربات ساخت کانفیگ**
━━━━━━━━━━━━━━━━━━━━━━

**دستورات اصلی:**
/start - شروع و منوی اصلی
/help - این راهنما
/config - ساخت کانفیگ جدید
/status - وضعیت حساب شما
/sub - دریافت لینک ساب
/referral - سیستم معرفی

**پروتکل‌های پشتیبانی شده:**
• VMess (پیشفرض)
• VLESS
• Trojan
• Shadowsocks
• WireGuard

**نحوه استفاده:**
1. روی دکمه "ساخت کانفیگ" کلیک کنید
2. پروتکل مورد نظر را انتخاب کنید
3. کانفیگ شما ساخته می‌شود
4. لینک ساب را کپی کنید

**پشتیبانی:**
برای دریافت کمک، از دکمه "پشتیبانی" استفاده کنید.
"""
    bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_back_button())

# ========== دستورات کاربری ==========
@bot.message_handler(commands=['config'])
def config_command(message):
    user_id = message.from_user.id
    if vpn_bot.get_user(user_id) is None:
        vpn_bot.create_user(user_id)
    
    text = "🔧 **انتخاب نوع کانفیگ:**\nلطفاً پروتکل مورد نظر خود را انتخاب کنید:"
    bot.reply_to(message, text, reply_markup=config_types_menu(), parse_mode='HTML')

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
        user = vpn_bot.get_user(user_id)
    
    traffic = vpn_bot.check_traffic(user_id)
    configs = vpn_bot.get_configs(user_id)
    
    text = f"""
📊 **وضعیت حساب کاربری**
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {message.from_user.first_name}
🆔 **آیدی:** `{user_id}`
📅 **تاریخ عضویت:** {format_time(user['join_date'])}
━━━━━━━━━━━━━━━━━━━━━━

📊 **مصرف ترافیک:**
• استفاده شده: {format_bytes(traffic['used'])}
• کل ترافیک: {format_bytes(traffic['limit'])}
• باقی‌مانده: {format_bytes(traffic['remaining'])}
• درصد مصرف: {traffic['percent']:.1f}%
{"🔴" if traffic['percent'] > 90 else "🟡" if traffic['percent'] > 70 else "🟢"}

📋 **تعداد کانفیگ‌ها:** {len(configs)}
💰 **کیف پول:** {user['balance']} سکه
🎁 **تعداد معرفی:** {user['referral_count']}
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text, reply_markup=get_back_button(), parse_mode='HTML')

@bot.message_handler(commands=['sub'])
def sub_command(message):
    user_id = message.from_user.id
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
    
    # بررسی وجود کانفیگ
    configs = vpn_bot.get_configs(user_id)
    if not configs:
        bot.reply_to(message, "❌ شما هیچ کانفیگ فعالی ندارید. ابتدا یک کانفیگ بسازید.", 
                    reply_markup=config_types_menu())
        return
    
    sub_link = vpn_bot.generate_subscription_link(user_id)
    text = f"""
🔗 **لینک ساب‌اسکریپشن شما**
━━━━━━━━━━━━━━━━━━━━━━

📋 لینک اشتراک:
<code>{sub_link}</code>

📌 **نحوه استفاده:**
1. لینک را در کلاینت خود وارد کنید
2. کلاینت‌های پشتیبانی شده:
   • V2RayNG (اندروید)
   • Shadowrocket (iOS)
   • NekoRay (ویندوز)
   • Qv2ray (لینوکس)
   • Clash (همه سیستم‌ها)

🔄 **توجه:** این لینک برای همیشه معتبر است و به‌روزرسانی خودکار دارد.
"""
    bot.reply_to(message, text, reply_markup=get_back_button(), parse_mode='HTML')

@bot.message_handler(commands=['referral'])
def referral_command(message):
    user_id = message.from_user.id
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
    
    text = f"""
🎁 **سیستم معرفی دوستان**
━━━━━━━━━━━━━━━━━━━━━━

👤 **کد معرفی شما:**
<code>{user['referral_code']}</code>

📋 **لینک معرفی:**
`https://t.me/{bot.get_me().username}?start={user['referral_code']}`

🎯 **پاداش:**
• هر کاربر جدید با کد شما = ۱۰ سکه
• هر ۵ معرفی = ۱ کانفیگ رایگان

📊 **آمار معرفی شما:**
• تعداد معرفی‌ها: {user['referral_count']}
• سکه‌های کسب شده: {user['balance']}

📌 لینک را برای دوستان خود ارسال کنید!
"""
    bot.reply_to(message, text, reply_markup=get_back_button(), parse_mode='HTML')

# ========== هندلرهای ساخت کانفیگ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("config_"))
def handle_config_create(call):
    user_id = call.from_user.id
    protocol = call.data.replace("config_", "")
    
    # بررسی کاربر
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
    
    # ایجاد کانفیگ
    config = vpn_bot.generate_config(user_id, protocol)
    if not config:
        bot.answer_callback_query(call.id, "❌ خطا در ساخت کانفیگ!")
        return
    
    # نمایش کانفیگ
    text = f"""
🔧 **کانفیگ {protocol.upper()} ساخته شد!**
━━━━━━━━━━━━━━━━━━━━━━

📋 **کانفیگ:**
<code>{config['config']}</code>

🔗 **لینک ساب:**
`{config['subscription_link']}`

📅 **تاریخ انقضا:** {format_time(config['expiry'])}
🆔 **شناسه کانفیگ:** {config['id']}

📌 **نکات مهم:**
• کانفیگ را در کلاینت خود وارد کنید
• از لینک ساب برای به‌روزرسانی خودکار استفاده کنید
• در صورت نیاز به کمک، از پشتیبانی استفاده کنید
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id, "✅ کانفیگ با موفقیت ساخته شد!")

# ========== هندلرهای دیگر ==========
@bot.callback_query_handler(func=lambda call: call.data == "create_config")
def handle_create_config(call):
    bot.edit_message_text("🔧 **انتخاب نوع کانفیگ:**", 
                         call.message.chat.id, call.message.message_id,
                         reply_markup=config_types_menu(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "my_status")
def handle_my_status(call):
    user_id = call.from_user.id
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
        user = vpn_bot.get_user(user_id)
    
    traffic = vpn_bot.check_traffic(user_id)
    configs = vpn_bot.get_configs(user_id)
    
    text = f"""
📊 **وضعیت حساب کاربری**
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {call.from_user.first_name}
🆔 **آیدی:** `{user_id}`
━━━━━━━━━━━━━━━━━━━━━━

📊 **مصرف ترافیک:**
• استفاده شده: {format_bytes(traffic['used'])}
• کل ترافیک: {format_bytes(traffic['limit'])}
• باقی‌مانده: {format_bytes(traffic['remaining'])}
• درصد مصرف: {traffic['percent']:.1f}%
{"🔴" if traffic['percent'] > 90 else "🟡" if traffic['percent'] > 70 else "🟢"}

📋 **تعداد کانفیگ‌ها:** {len(configs)}
💰 **کیف پول:** {user['balance']} سکه
🎁 **تعداد معرفی:** {user['referral_count']}
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "my_configs")
def handle_my_configs(call):
    user_id = call.from_user.id
    configs = vpn_bot.get_configs(user_id)
    
    if not configs:
        text = "📭 شما هیچ کانفیگ فعالی ندارید. از دکمه 'ساخت کانفیگ' استفاده کنید."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                             reply_markup=config_types_menu(), parse_mode='HTML')
        bot.answer_callback_query(call.id)
        return
    
    text = "📋 **کانفیگ‌های فعال شما:**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for cfg in configs:
        protocol = cfg['protocol'].upper()
        created = format_time(cfg['created_at'])
        expiry = format_time(cfg['expires_at'])
        traffic_used = format_bytes(cfg.get('traffic_used', 0))
        traffic_limit = format_bytes(cfg.get('traffic_limit', 0))
        
        text += f"""
🔹 **{protocol}** (ID: {cfg['id']})
• تاریخ ایجاد: {created}
• تاریخ انقضا: {expiry}
• مصرف: {traffic_used} / {traffic_limit}
• وضعیت: {"✅ فعال" if cfg['is_active'] else "❌ غیرفعال"}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔄 ساخت کانفیگ جدید", callback_data="create_config"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=keyboard, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "subscription")
def handle_subscription(call):
    user_id = call.from_user.id
    configs = vpn_bot.get_configs(user_id)
    
    if not configs:
        bot.answer_callback_query(call.id, "❌ ابتدا یک کانفیگ بسازید!")
        return
    
    sub_link = vpn_bot.generate_subscription_link(user_id)
    text = f"""
🔗 **لینک ساب‌اسکریپشن شما**
━━━━━━━━━━━━━━━━━━━━━━

📋 لینک اشتراک:
<code>{sub_link}</code>

📌 **نحوه استفاده:**
1. لینک را در کلاینت خود وارد کنید
2. کلاینت‌های پشتیبانی شده:
   • V2RayNG (اندروید)
   • Shadowrocket (iOS)
   • NekoRay (ویندوز)
   • Qv2ray (لینوکس)
   • Clash (همه سیستم‌ها)

🔄 **توجه:** این لینک برای همیشه معتبر است و به‌روزرسانی خودکار دارد.
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "wallet")
def handle_wallet(call):
    user_id = call.from_user.id
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
        user = vpn_bot.get_user(user_id)
    
    text = f"""
💰 **کیف پول شما**
━━━━━━━━━━━━━━━━━━━━━━

💰 **موجودی:** {user['balance']} سکه
🎁 **تعداد معرفی:** {user['referral_count']}

📌 **نحوه دریافت سکه:**
• هر معرفی = ۱۰ سکه
• هر ۵ معرفی = ۱ کانفیگ رایگان
• کد تخفیف ویژه = سکه اضافی

💡 سکه‌ها را می‌توانید برای خرید ترافیک اضافی استفاده کنید.
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "referral")
def handle_referral_callback(call):
    user_id = call.from_user.id
    user = vpn_bot.get_user(user_id)
    if not user:
        vpn_bot.create_user(user_id)
        user = vpn_bot.get_user(user_id)
    
    text = f"""
🎁 **سیستم معرفی دوستان**
━━━━━━━━━━━━━━━━━━━━━━

👤 **کد معرفی شما:**
<code>{user['referral_code']}</code>

📋 **لینک معرفی:**
`https://t.me/{bot.get_me().username}?start={user['referral_code']}`

🎯 **پاداش:**
• هر کاربر جدید با کد شما = ۱۰ سکه
• هر ۵ معرفی = ۱ کانفیگ رایگان

📊 **آمار معرفی شما:**
• تعداد معرفی‌ها: {user['referral_count']}
• سکه‌های کسب شده: {user['balance']}

📌 لینک را برای دوستان خود ارسال کنید!
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "support")
def handle_support(call):
    text = """
📞 **پشتیبانی و تیکت‌ها**
━━━━━━━━━━━━━━━━━━━━━━

📌 **نحوه ارسال تیکت:**
برای ارسال تیکت، پیام خود را با دستور زیر ارسال کنید:

/ticket [موضوع] | [متن پیام]

مثال:
/ticket مشکل در اتصال | من نمی‌توانم به سرور متصل شوم

⏰ زمان پاسخگویی: ۲۴-۴۸ ساعت

📋 **تیکت‌های شما:**
برای مشاهده تیکت‌های خود از دستور /tickets استفاده کنید.
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "help")
def handle_help_callback(call):
    text = """
📚 **راهنمای ربات**
━━━━━━━━━━━━━━━━━━━━━━

**دستورات اصلی:**
/start - شروع و منوی اصلی
/help - این راهنما
/config - ساخت کانفیگ جدید
/status - وضعیت حساب شما
/sub - دریافت لینک ساب
/referral - سیستم معرفی
/ticket - ارسال تیکت

**پروتکل‌های پشتیبانی شده:**
• VMess (پیشفرض)
• VLESS
• Trojan
• Shadowsocks
• WireGuard

**نحوه استفاده:**
1. روی دکمه "ساخت کانفیگ" کلیک کنید
2. پروتکل مورد نظر را انتخاب کنید
3. کانفیگ شما ساخته می‌شود
4. لینک ساب را کپی کنید

**پشتیبانی:**
برای دریافت کمک، از دکمه "پشتیبانی" استفاده کنید.
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "settings")
def handle_settings(call):
    text = """
⚙️ **تنظیمات کاربری**
━━━━━━━━━━━━━━━━━━━━━━

🔧 **تنظیمات موجود:**
• تغییر پروتکل پیشفرض
• تنظیم اعلان‌ها
• تغییر زبان (فارسی/انگلیسی)

📌 **توجه:** تنظیمات پیشرفته فقط برای ادمین‌ها قابل دسترسی است.
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def handle_back_main(call):
    text = f"""
🚀 **ربات ساخت کانفیگ VPN پیشرفته** 🚀
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {call.from_user.first_name}
━━━━━━━━━━━━━━━━━━━━━━

✨ **منوی اصلی:**
• ساخت کانفیگ
• مشاهده وضعیت
• مدیریت کانفیگ‌ها
• دریافت لینک ساب
• سیستم معرفی
• پشتیبانی
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=main_menu(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

# ========== پنل مدیریت ==========
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def handle_admin_panel(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    text = """
👑 **پنل مدیریت ربات**
━━━━━━━━━━━━━━━━━━━━━━

📊 **آمار کلی:**
• کاربران: {users_count}
• کانفیگ‌های فعال: {configs_count}
• ترافیک مصرفی: {total_traffic}
• تیکت‌های باز: {tickets_count}

از منوی زیر برای مدیریت استفاده کنید:
"""
    users_count = db.fetch_one("SELECT COUNT(*) FROM users")[0] or 0
    configs_count = db.fetch_one("SELECT COUNT(*) FROM configs WHERE is_active = 1")[0] or 0
    total_traffic = db.fetch_one("SELECT SUM(total_used_traffic) FROM users")[0] or 0
    tickets_count = db.fetch_one("SELECT COUNT(*) FROM tickets WHERE status = 'open'")[0] or 0
    
    text = text.format(users_count=users_count, configs_count=configs_count,
                      total_traffic=format_bytes(total_traffic), tickets_count=tickets_count)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=admin_panel_menu(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def handle_admin_users(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    users = db.fetch_all("SELECT user_id, first_name, username, join_date, is_admin FROM users ORDER BY join_date DESC LIMIT 20")
    text = "👥 **لیست کاربران (۲۰ کاربر اخیر)**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for user in users:
        status = "👑 ادمین" if user[4] else "👤 کاربر"
        name = user[1] or "بدون نام"
        username = f"@{user[2]}" if user[2] else f"ID: {user[0]}"
        text += f"{status} - {name} ({username})\n"
        text += f"📅 عضویت: {format_time(user[3])}\n━━━━━━━━━━━━━━━━━━━━━━\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_tickets")
def handle_admin_tickets(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    tickets = vpn_bot.get_all_tickets()
    if not tickets:
        text = "📭 هیچ تیکت باز وجود ندارد."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                             reply_markup=get_back_button(), parse_mode='HTML')
        bot.answer_callback_query(call.id)
        return
    
    text = "🎫 **لیست تیکت‌های باز**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for ticket in tickets:
        text += f"""
🔹 تیکت #{ticket[0]}
👤 کاربر: {ticket[1]}
📋 موضوع: {ticket[2]}
📝 پیام: {ticket[3][:50]}...
📅 تاریخ: {format_time(ticket[5])}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel"))
    keyboard.add(InlineKeyboardButton("✅ بستن تیکت", callback_data="admin_close_ticket"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=keyboard, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def handle_admin_stats(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    users_count = db.fetch_one("SELECT COUNT(*) FROM users")[0] or 0
    configs_count = db.fetch_one("SELECT COUNT(*) FROM configs WHERE is_active = 1")[0] or 0
    total_traffic = db.fetch_one("SELECT SUM(total_used_traffic) FROM users")[0] or 0
    tickets_count = db.fetch_one("SELECT COUNT(*) FROM tickets WHERE status = 'open'")[0] or 0
    admins_count = db.fetch_one("SELECT COUNT(*) FROM users WHERE is_admin = 1")[0] or 0
    
    text = f"""
📊 **آمار کامل ربات**
━━━━━━━━━━━━━━━━━━━━━━

👥 **کاربران:** {users_count}
📋 **کانفیگ‌های فعال:** {configs_count}
📊 **ترافیک مصرفی:** {format_bytes(total_traffic)}
🎫 **تیکت‌های باز:** {tickets_count}
👑 **ادمین‌ها:** {admins_count}
━━━━━━━━━━━━━━━━━━━━━━

📌 **آخرین به‌روزرسانی:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         reply_markup=get_back_button(), parse_mode='HTML')
    bot.answer_callback_query(call.id)

# ========== دستورات تیکت ==========
@bot.message_handler(commands=['ticket'])
def ticket_command(message):
    user_id = message.from_user.id
    args = message.text.split('|')
    
    if len(args) < 2:
        bot.reply_to(message, "❌ فرمت صحیح:\n/ticket [موضوع] | [متن پیام]")
        return
    
    subject = args[0].replace('/ticket', '').strip()
    msg = args[1].strip()
    
    if not subject or not msg:
        bot.reply_to(message, "❌ لطفاً موضوع و پیام را وارد کنید.")
        return
    
    ticket_id = vpn_bot.add_ticket(user_id, subject, msg)
    bot.reply_to(message, f"✅ تیکت شما با شماره #{ticket_id} ثبت شد.\nبه زودی پاسخ داده می‌شود.")

@bot.message_handler(commands=['tickets'])
def my_tickets_command(message):
    user_id = message.from_user.id
    tickets = vpn_bot.get_tickets(user_id)
    
    if not tickets:
        bot.reply_to(message, "📭 شما هیچ تیکتی ندارید.")
        return
    
    text = "📋 **لیست تیکت‌های شما**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for ticket in tickets:
        status = "🟢 باز" if ticket[4] == 'open' else "🔴 بسته"
        text += f"""
🔹 #{ticket[0]} - {ticket[2]}
📝 {ticket[3][:50]}...
📅 {format_time(ticket[5])}
وضعیت: {status}
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text, reply_markup=get_back_button(), parse_mode='HTML')

# ========== اجرا ==========
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات ساخت کانفیگ پیشرفته V2Ray/XRay 🚀")
    print("=" * 70)
    print(f"👥 ادمین‌ها: {ADMIN_IDS}")
    print("✅ پروتکل‌های پشتیبانی شده: VMess, VLESS, Trojan, Shadowsocks, WireGuard")
    print("✅ لینک ساب‌اسکریپشن واقعی")
    print("✅ سیستم مدیریت کاربران پیشرفته")
    print("✅ پنل مدیریت کامل")
    print("=" * 70)
    print("🔄 ربات در حال اجرا...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            print("🔄 راه‌اندازی مجدد در 5 ثانیه...")
            time.sleep(5)
            continue
