# ============================================================
# TARTIL BOT - بـ ـؤت ديـ ـنـ ـي
# Single File Professional Telegram Bot
# Bendary
# ============================================================

# ==================== IMPORTS ====================
import os
import sys
import json
import asyncio
import logging
import sqlite3
import random
from html import escape
from datetime import datetime, time as dt_time
from typing import Optional, Dict, Any

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ChatMemberHandler
)
from telegram.constants import ParseMode, ChatType
from telegram.error import (
    TelegramError, Forbidden, BadRequest, RetryAfter, NetworkError
)

import aiohttp
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    "9120181201:AAELFnm1OzkPT4p9qOmtIe_HJy3KQcSeOCc"
)

ADMIN_IDS_RAW = os.environ.get("ADMIN_IDS", "7138192280")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

DB_PATH = os.environ.get("DB_PATH", "t88artil.db")
DEFAULT_TZ = "Africa/Cairo"
DEFAULT_CITY = "Cairo"
DEFAULT_COUNTRY = "Egypt"
DEFAULT_METHOD = 5

# Banner URL (غيّرها لصورة البوت)
BANNER_URL = os.environ.get("BANNER_URL", "https://i.ibb.co/393Z7W2K/8740e380-c43a-11f1-b51e-a53d235a3c9e.jpg")

# Developer & Channel URLs (عدّلهم)
DEVELOPER_URL = os.environ.get("DEVELOPER_URL", "https://t.me/a_l_k_h_m_o_r_g_y")
BOT_CHANNEL_URL = os.environ.get("BOT_CHANNEL_URL", "https://t.me/hhgghjoh")

# ==================== CONSTANTS ====================
PRAYER_METHODS = {
    "0": "Jafari / Shia Ithna-Ashari",
    "1": "University of Islamic Sciences, Karachi",
    "2": "Islamic Society of North America",
    "3": "Muslim World League",
    "4": "Umm Al-Qura University, Makkah",
    "5": "Egyptian General Authority",
    "7": "Institute of Geophysics, University of Tehran",
    "8": "Gulf Region",
    "9": "Kuwait",
    "10": "Qatar",
    "11": "Majlis Ugama Islam Singapura",
    "12": "Union Organization Islamic de France",
    "13": "Diyanet İşleri Başkanlığı, Turkey",
    "16": "Dubai",
    "18": "Tunisia",
    "19": "Algeria",
    "20": "KEMENAG Indonesia",
    "21": "Morocco",
}

PRAYERS = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]
PRAYER_AR = {
    "Fajr": "الفجر", "Sunrise": "الشروق", "Dhuhr": "الظهر",
    "Asr": "العصر", "Maghrib": "المغرب", "Isha": "العشاء",
}

# ==================== LOGGING ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("TartilBot")



# ==================== DATABASE ====================

class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(
            self.path, check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()

        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_admin INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                notifications_enabled INTEGER DEFAULT 1,
                city TEXT DEFAULT 'Cairo',
                country TEXT DEFAULT 'Egypt',
                timezone TEXT DEFAULT 'Africa/Cairo',
                created_at TEXT DEFAULT (datetime('now')),
                last_seen TEXT
            );

            CREATE TABLE IF NOT EXISTS channels (
                channel_id INTEGER PRIMARY KEY,
                channel_username TEXT,
                channel_title TEXT,
                owner_id INTEGER,
                city TEXT DEFAULT 'Cairo',
                country TEXT DEFAULT 'Egypt',
                timezone TEXT DEFAULT 'Africa/Cairo',
                prayer_method INTEGER DEFAULT 5,
                madhab INTEGER DEFAULT 0,
                dua_enabled INTEGER DEFAULT 1,
                azkar_enabled INTEGER DEFAULT 1,
                morning_azkar_enabled INTEGER DEFAULT 0,
                evening_azkar_enabled INTEGER DEFAULT 0,
                prayer_notifications_enabled INTEGER DEFAULT 1,
                posting_interval INTEGER DEFAULT 10,
                posting_start TEXT DEFAULT '08:00',
                posting_end TEXT DEFAULT '23:00',
                last_content_id INTEGER,
                last_content_text TEXT,
                last_prayer_notification TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS duas (
                dua_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                category TEXT DEFAULT 'general',
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS azkar (
                zikr_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                source TEXT DEFAULT 'manual',
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tools (
                tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                button_text TEXT,
                description TEXT,
                type TEXT DEFAULT 'internal',
                callback_data TEXT,
                url TEXT,
                enabled INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS prayer_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                country TEXT,
                date TEXT,
                fajr TEXT,
                sunrise TEXT,
                dhuhr TEXT,
                asr TEXT,
                maghrib TEXT,
                isha TEXT,
                method INTEGER DEFAULT 5,
                fetched_at TEXT DEFAULT (datetime('now')),
                UNIQUE(city, country, date)
            );

            CREATE TABLE IF NOT EXISTS logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                details TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS broadcasts (
                broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                target TEXT,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_duas_enabled
                ON duas(enabled);

            CREATE INDEX IF NOT EXISTS idx_azkar_category
                ON azkar(category);

            CREATE INDEX IF NOT EXISTS idx_prayer_date
                ON prayer_times(date);
        """)

        # إضافة العمود لقواعد البيانات القديمة إذا لم يكن موجودًا
        c.execute("PRAGMA table_info(channels)")
        columns = [row[1] for row in c.fetchall()]

        if "last_content_text" not in columns:
            c.execute(
                "ALTER TABLE channels ADD COLUMN last_content_text TEXT"
            )

        self.conn.commit()
        self._seed_defaults()



    def _seed_defaults(self):
        c = self.conn.cursor()

        defaults = {
            "posting_interval": "60",
            "posting_enabled": "1",
            "posting_start": "08:00",
            "posting_end": "23:00",
            "posting_all_day": "0",
            "dua_enabled": "1",
            "azkar_enabled": "1",
            "morning_azkar_enabled": "0",
            "morning_azkar_time": "07:00",
            "evening_azkar_enabled": "0",
            "evening_azkar_time": "18:00",
            "prayer_notifications_enabled": "1",
            "default_city": DEFAULT_CITY,
            "default_country": DEFAULT_COUNTRY,
            "default_timezone": DEFAULT_TZ,
            "default_method": str(DEFAULT_METHOD),
            "min_content_gap": "20",
            "bot_channel_url": BOT_CHANNEL_URL,
            "developer_url": DEVELOPER_URL,
            "support_url": "",
            "welcome_text": (
                '<b>'
                'السلام عليكم ورحمة الله وبركاته '
                '<tg-emoji emoji-id="5348070818595216445">🌸</tg-emoji>'
                '</b>\n\n'

                '<b>'
                'اهلا بك في بوت بـ ـؤت ديـ ـنـ ـي
               '
                '<tg-emoji emoji-id="5321154125407210430">🤍</tg-emoji>'
                '</b>\n\n'

                '<blockquote>'
                '<b>'
                'البوت يقدم لك إشعارات تلقائية لكل صلاة '
                '<tg-emoji emoji-id="5305313800688254618">🕌</tg-emoji>'
                '</b>\n'
                '<b>'
                'الأدعية والأذكار '
                '<tg-emoji emoji-id="5429327730070009271">🤲</tg-emoji>'
                '</b>\n'
                '<b>'
                'النشر التلقائي في جروبك أو قناتك '
                '<tg-emoji emoji-id="5346152548761868765">📿</tg-emoji>'
                '</b>'
                '</blockquote>'
            ),
        }

        for key, val in defaults.items():
            c.execute(
                """
                INSERT OR IGNORE INTO settings (key, value)
                VALUES (?, ?)
                """,
                (key, str(val))
            )

        self.conn.commit()



    def execute(self, query: str, params: tuple = ()):
        c = self.conn.cursor()
        c.execute(query, params)
        self.conn.commit()
        return c

    def fetchone(self, query: str, params: tuple = ()):
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()


db = Database()

# يتم تعيينه بعد استدعاء get_me() في post_init
BOT_USERNAME = ""





def bot_link_keyboard() -> InlineKeyboardMarkup:
    """زر ثابت يفتح محادثة البوت من الرسائل المنشورة."""

    if not BOT_USERNAME:
        return InlineKeyboardMarkup([])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="بـ ـؤت ديـ ـنـ ـي | Boot Denny ",
                url=f"https://t.me/{BOT_USERNAME}",
                api_kwargs={
                    "icon_custom_emoji_id": "6021690418398239007",
                    "style": "primary"
                }
            )
        ]
    ])






def promote_bot_keyboard(chat_type: str) -> InlineKeyboardMarkup:
    """رابط تيليجرام الذي يفتح إضافة البوت مع شاشة اختيار صلاحيات الأدمن."""
    if chat_type == ChatType.CHANNEL:
        admin_rights = "post_messages+edit_messages+delete_messages"
        url = f"https://t.me/{BOT_USERNAME}?startchannel&admin={admin_rights}"
    else:
        admin_rights = (
            "change_info+delete_messages+ban_users+invite_users+pin_messages"
            "+manage_video_chats+manage_topics"
        )
        url = f"https://t.me/{BOT_USERNAME}?startgroup&admin={admin_rights}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("رفع البوت ادمن", url=url)]
    ])


# ==================== HELPERS ====================
def get_setting(key: str, default: str = "") -> str:
    row = db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str):
    db.execute(
        """INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime('now')""",
        (key, value, value),
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def log_event(level: str, message: str, details: str = ""):
    try:
        db.execute("INSERT INTO logs (level, message, details) VALUES (?, ?, ?)",
                   (level, message, details))
    except Exception as e:
        logger.error(f"Failed to log: {e}")


def now_tz(tz_str: str = DEFAULT_TZ) -> datetime:
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo(DEFAULT_TZ)
    return datetime.now(tz)


def today_str(tz_str: str = DEFAULT_TZ) -> str:
    return now_tz(tz_str).strftime("%d-%m-%Y")


def format_time(time_str: str) -> str:
    try:
        h, m = map(int, time_str.split(":")[:2])
        period = "ص" if h < 12 else "م"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {period}"
    except Exception:
        return time_str


def hijri_date() -> str:
    try:
        from datetime import date
        g = date.today()
        jd = g.toordinal() + 1721425
        l = jd - 1948440 + 10632
        n = (l - 1) // 10631
        l = l - 10631 * n + 354
        j = ((10985 - l) // 5316) * ((50 * l) // 17719) + (l // 5670) * ((43 * l) // 15238)
        l = l - ((30 - j) // 15) * ((17719 * j) // 50) - (j // 16) * ((15238 * j) // 43) + 29
        m = (24 * l) // 709
        d = l - (709 * m) // 24
        y = 30 * n + j - 30
        return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        return ""


def arabic_day_name(dt: datetime) -> str:
    days = {
        "Monday": "الاثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
        "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد",
    }
    return days.get(dt.strftime("%A"), "")



async def safe_edit(query, text: str, kb: InlineKeyboardMarkup = None):
    """Edit message text or caption safely using HTML parse mode."""
    try:
        if query.message.photo or query.message.caption:
            await query.edit_message_caption(
                caption=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )

    except BadRequest as e:
        logger.warning(f"edit failed, sending new: {e}")

        try:
            await query.message.delete()
        except Exception:
            pass

        try:
            await query.message.chat.send_message(
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as ex:
            logger.error(f"failed to send fallback: {ex}")



# ==================== CONTENT PROVIDER ====================

class ContentProvider:
    FALLBACK_DUAS = [
        "اللَّهُمَّ رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
        "رَبَّنَا ظَلَمْنَا أَنفُسَنَا وَإِن لَّمْ تَغْفِرْ لَنَا وَتَرْحَمْنَا لَنَكُونَنَّ مِنَ الْخَاسِرِينَ",
        "حَسْبِيَ اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ",
        "اللَّهُمَّ إِنِّي أَسْأَلُكَ الْهُدَى وَالتُّقَى وَالْعَفَافَ وَالْغِنَى",
        "رَبِّ اجْعَلْنِي مُقِيمَ الصَّلَاةِ وَمِن ذُرِّيَّتِي رَبَّنَا وَتَقَبَّلْ دُعَاءِ",
        "اللَّهُمَّ أَعِنِّي عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِكَ",
        "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا وَهَبْ لَنَا مِن لَّدُنكَ رَحْمَةً إِنَّكَ أَنتَ الْوَهَّابُ",
        "اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا وَرِزْقًا طَيِّبًا وَعَمَلًا مُتَقَبَّلًا",
        "رَبِّ اشْرَحْ لِي صَدْرِي وَيَسِّرْ لِي أَمْرِي",
        "اللَّهُمَّ إِنَّكَ عَفُوٌّ كَرِيمٌ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي",
        "اللَّهُمَّ اجْعَلْنَا مِنَ الْمُحَافِظِينَ عَلَى الصَّلَاةِ وَارْزُقْنَا خُشُوعَهَا وَفَضْلَهَا وَقَبُولَهَا",
        "اللَّهُمَّ اجْعَلْ لَنَا مِنْ رَحْمَتِكَ نَصِيبًا وَارْزُقْنَا سَكِينَةً فِي الْقَلْبِ",
        "اللَّهُمَّ ارْزُقْنَا عِلْمًا نَافِعًا وَقَلْبًا خَاشِعًا وَقَلْبًا سَلِيمًا",
        "اللَّهُمَّ ارْزُقْنَا تَوْبَةً نَصُوحًا وَقَلْبًا سَلِيمًا وَعَمَلًا صَالِحًا",
        "اللَّهُمَّ إِنِّي أَسْأَلُكَ حُبَّكَ وَحُبَّ مَنْ يَنْفَعُنِي حُبُّهُ عِنْدَكَ",
        "رَبَّنَا اغْفِرْ لَنَا وَلِوَالِدَيْنَا وَلِلْمُؤْمِنِينَ يَوْمَ يَقُومُ الْحِسَابُ",
        "اللَّهُمَّ ثَبِّتْ قَلْبِي عَلَى دِينِكَ",
        "اللَّهُمَّ أَنْزِلْ عَلَيْنَا مِنْ بَرَكَاتِ السَّمَاءِ وَأَخْرِجْ لَنَا مِنْ بَرَكَاتِ الْأَرْضِ",
        "اللَّهُمَّ اجْعَلْ خَيْرَ عُمُرِي آخِرَهُ",
        "اللَّهُمَّ أَغْنِنَا بِحَلَالِكَ عَنْ حَرَامِكَ",
        "اللَّهُمَّ يَسِّرْ لَنَا كُلَّ عَسِيرٍ",
    ]

    FALLBACK_AZKAR = [
        "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ",
        "لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ",
        "أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ",
        "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ",
        "سُبْحَانَ اللَّهِ، وَالْحَمْدُ لِلَّهِ، وَلَا إِلَهَ إِلَّا اللَّهُ، وَاللَّهُ أَكْبَرُ",
        "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ",
        "حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ",
        "اللَّهُمَّ أَجِرْنَا مِنَ النَّارِ",
        "اللَّهُمَّ اهْدِنَا فِيمَنْ هَدَيْتَ",
        "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ عَدَدَ خَلْقِهِ وَرِضَا نَفْسِهِ وَزِنَةَ عَرْشِهِ وَمِدَادَ كَلِمَاتِهِ",
    ]

    FALLBACK_MORNING = [
        "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ",
        "اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ",
        "اللَّهُمَّ إِنِّي أَسْأَلُكَ خَيْرَ هَذَا الْيَوْمِ، فَتْحَهُ، وَنَصْرَهُ، وَنُورَهُ، وَبَرَكَتَهُ، وَهُدَاهُ",
    ]

    FALLBACK_EVENING = [
        "أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ",
        "اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ",
        "اللَّهُمَّ إِنِّي أَسْأَلُكَ خَيْرَ هَذِهِ اللَّيْلَةِ، فَتْحَهَا، وَنَصْرَهَا، وَنُورَهَا، وَبَرَكَتَهَا، وَهُدَاهَا",
    ]

    @staticmethod
    async def refresh_from_source() -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://dua-dhikr.vercel.app/categories/doa",
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"Accept-Language": "ar"},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            for item in data[:200]:
                                text = item.get("arabic", "")
                                if text and len(text) > 10:
                                    db.execute(
                                        "INSERT INTO duas (content, source) VALUES (?, ?)",
                                        (text, "api"),
                                    )

                            logger.info("Fetched duas from API")
                            return True

        except Exception as e:
            logger.warning(f"Content API unavailable: {e}")

        count = db.fetchone("SELECT COUNT(*) as c FROM duas")["c"]

        if count == 0:
            for d in ContentProvider.FALLBACK_DUAS:
                db.execute(
                    "INSERT INTO duas (content, source) VALUES (?, ?)",
                    (d, "builtin"),
                )

            for z in ContentProvider.FALLBACK_AZKAR:
                db.execute(
                    "INSERT INTO azkar (content, source, category) VALUES (?, ?, ?)",
                    (z, "builtin", "general"),
                )

            for m in ContentProvider.FALLBACK_MORNING:
                db.execute(
                    "INSERT INTO azkar (content, source, category) VALUES (?, ?, ?)",
                    (m, "builtin", "morning"),
                )

            for e in ContentProvider.FALLBACK_EVENING:
                db.execute(
                    "INSERT INTO azkar (content, source, category) VALUES (?, ?, ?)",
                    (e, "builtin", "evening"),
                )

            logger.info("Seeded built-in content")

        return True

    @staticmethod
    def get_next_dua(
        last_id: Optional[int] = None,
        last_text: Optional[str] = None,
    ) -> Optional[str]:
        query = "SELECT content FROM duas WHERE enabled = 1"
        params = []

        if last_id is not None:
            query += " AND dua_id != ?"
            params.append(last_id)

        if last_text:
            query += " AND content != ?"
            params.append(last_text)

        query += " ORDER BY RANDOM() LIMIT 1"

        rows = db.fetchall(query, tuple(params))

        if rows:
            return rows[0]["content"]

        fallback = [
            dua for dua in ContentProvider.FALLBACK_DUAS
            if dua != last_text
        ]

        if fallback:
            return random.choice(fallback)

        return random.choice(ContentProvider.FALLBACK_DUAS)

    @staticmethod
    def get_next_zikr(
        category: str = "general",
        last_id: Optional[int] = None,
        last_text: Optional[str] = None,
    ) -> Optional[str]:
        query = """
            SELECT content
            FROM azkar
            WHERE enabled = 1 AND category = ?
        """
        params = [category]

        if last_id is not None:
            query += " AND zikr_id != ?"
            params.append(last_id)

        if last_text:
            query += " AND content != ?"
            params.append(last_text)

        query += " ORDER BY RANDOM() LIMIT 1"

        rows = db.fetchall(query, tuple(params))

        if rows:
            return rows[0]["content"]

        fallback = {
            "general": ContentProvider.FALLBACK_AZKAR,
            "morning": ContentProvider.FALLBACK_MORNING,
            "evening": ContentProvider.FALLBACK_EVENING,
        }.get(category, ContentProvider.FALLBACK_AZKAR)

        available = [
            zikr for zikr in fallback
            if zikr != last_text
        ]

        if available:
            return random.choice(available)

        return random.choice(fallback)


# ==================== PRAYER API ====================
class PrayerAPI:
    BASE = "https://api.aladhan.com/v1"

    @staticmethod
    async def fetch_prayer_times(
        city: str,
        country: str,
        method: int = 5,
    ) -> Optional[Dict]:
        url = f"{PrayerAPI.BASE}/timingsByCity"
        params = {
            "city": city,
            "country": country,
            "method": method,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        timings = data.get("data", {}).get("timings", {})

                        return {
                            "fajr": timings.get("Fajr", "").split(" ")[0],
                            "sunrise": timings.get("Sunrise", "").split(" ")[0],
                            "dhuhr": timings.get("Dhuhr", "").split(" ")[0],
                            "asr": timings.get("Asr", "").split(" ")[0],
                            "maghrib": timings.get("Maghrib", "").split(" ")[0],
                            "isha": timings.get("Isha", "").split(" ")[0],
                        }

        except Exception as e:
            logger.error(f"Prayer API error: {e}")
            log_event("ERROR", "Prayer API error", str(e))

        return None

    @staticmethod
    async def get_times_for_date(
        city: str,
        country: str,
        date_str: str,
        method: int = 5,
    ) -> Optional[Dict]:
        row = db.fetchone(
            "SELECT * FROM prayer_times WHERE city = ? AND country = ? AND date = ?",
            (city, country, date_str),
        )

        if row:
            return {
                "fajr": row["fajr"],
                "sunrise": row["sunrise"],
                "dhuhr": row["dhuhr"],
                "asr": row["asr"],
                "maghrib": row["maghrib"],
                "isha": row["isha"],
            }

        times = await PrayerAPI.fetch_prayer_times(
            city,
            country,
            method,
        )

        if times:
            db.execute(
                """
                INSERT OR REPLACE INTO prayer_times
                (city, country, date, fajr, sunrise, dhuhr, asr, maghrib, isha, method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    city,
                    country,
                    date_str,
                    times["fajr"],
                    times["sunrise"],
                    times["dhuhr"],
                    times["asr"],
                    times["maghrib"],
                    times["isha"],
                    method,
                ),
            )

        return times



# ==================== SCHEDULER ====================
class TartilScheduler:
    def __init__(self, app: Application):
        self.app = app
        self.scheduler = AsyncIOScheduler(timezone=DEFAULT_TZ)
        self.jobs: Dict[str, Any] = {}

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def remove_job(self, job_id: str):
        if job_id in self.jobs:
            try:
                self.jobs[job_id].remove()
            except Exception:
                pass
            del self.jobs[job_id]

    def _add(self, func, trigger, job_id: str, **kwargs):
        self.remove_job(job_id)
        job = self.scheduler.add_job(func, trigger, id=job_id, replace_existing=True, **kwargs)
        self.jobs[job_id] = job
        return job

    def rebuild_all(self):
        # لا تسمح لقيمة خاطئة من إعدادات الأدمن بإيقاف بقية الجدولة.
        try:
            interval = max(1, min(1440, int(get_setting("posting_interval", "60"))))
        except (TypeError, ValueError):
            interval = 60
            set_setting("posting_interval", str(interval))

        if get_setting("posting_enabled", "1") == "1":
            self._add(publish_content_job, IntervalTrigger(minutes=interval), "content_publisher")
        else:
            self.remove_job("content_publisher")

        if get_setting("morning_azkar_enabled", "0") == "1":
            t = get_setting("morning_azkar_time", "07:00")
            try:
                h, m = map(int, t.split(":"))
                self._add(morning_azkar_job, CronTrigger(hour=h, minute=m, timezone=DEFAULT_TZ), "morning_azkar")
            except Exception as e:
                logger.error(f"Morning azkar schedule error: {e}")
        else:
            self.remove_job("morning_azkar")

        if get_setting("evening_azkar_enabled", "0") == "1":
            t = get_setting("evening_azkar_time", "18:00")
            try:
                h, m = map(int, t.split(":"))
                self._add(evening_azkar_job, CronTrigger(hour=h, minute=m, timezone=DEFAULT_TZ), "evening_azkar")
            except Exception as e:
                logger.error(f"Evening azkar schedule error: {e}")
        else:
            self.remove_job("evening_azkar")

        self._add(refresh_prayer_times_job, CronTrigger(hour=0, minute=5, timezone=DEFAULT_TZ), "daily_prayer_refresh")
        self._add(check_prayer_notifications_job, IntervalTrigger(minutes=1), "prayer_check")
        logger.info(f"Scheduler rebuilt: {len(self.jobs)} jobs active")


# ==================== BACKGROUND JOBS ====================



async def publish_content_job():
    try:
        if get_setting("posting_enabled", "1") != "1":
            return

        now = now_tz()
        start = get_setting("posting_start", "08:00")
        end = get_setting("posting_end", "23:00")
        all_day = get_setting("posting_all_day", "0") == "1"

        # التحقق من وقت النشر، مع دعم التشغيل طوال اليوم
        try:
            if all_day:
                allowed = True
            else:
                sh, sm = map(int, start.split(":"))
                eh, em = map(int, end.split(":"))

                if not (
                    0 <= sh <= 23 and 0 <= sm <= 59
                    and 0 <= eh <= 23 and 0 <= em <= 59
                ):
                    raise ValueError("Invalid posting time")

                current_time = now.time().replace(tzinfo=None)
                start_time = dt_time(sh, sm)
                end_time = dt_time(eh, em)

                if start_time <= end_time:
                    allowed = start_time <= current_time <= end_time
                else:
                    # دعم فترة النشر التي تتجاوز منتصف الليل
                    allowed = (
                        current_time >= start_time
                        or current_time <= end_time
                    )

            if not allowed:
                log_event(
                    "INFO",
                    f"Auto posting skipped: outside posting hours ({start}-{end})"
                )
                return

        except (ValueError, AttributeError, TypeError) as e:
            log_event(
                "ERROR",
                "Invalid posting time settings",
                str(e)
            )
            return

        # إعدادات أنواع المحتوى
        dua_on = get_setting("dua_enabled", "1") == "1"
        azkar_on = get_setting("azkar_enabled", "1") == "1"

        if not dua_on and not azkar_on:
            log_event(
                "WARN",
                "Auto posting skipped: duas and azkar are both disabled"
            )
            return

        channels = db.fetchall(
            "SELECT * FROM channels WHERE status = 'active'"
        )

        if not channels:
            log_event(
                "WARN",
                "Auto posting skipped: no active channels found"
            )
            return

        bot = scheduler.app.bot

        for ch in channels:
            channel_id = ch["channel_id"]

            try:
                # قراءة آخر محتوى منشور
                try:
                    last_text = ch["last_content_text"]
                except (KeyError, IndexError):
                    last_text = None

                # اختيار نوع المحتوى
                if dua_on and azkar_on:
                    use_dua = random.random() < 0.6
                else:
                    use_dua = dua_on

                if use_dua:
                    content = ContentProvider.get_next_dua(
                        last_text=last_text
                    )
                else:
                    content = ContentProvider.get_next_zikr(
                        category="general",
                        last_text=last_text
                    )

                # تجربة النوع الآخر لو لم يتوفر محتوى
                if not content:
                    if use_dua and azkar_on:
                        content = ContentProvider.get_next_zikr(
                            category="general",
                            last_text=last_text
                        )
                    elif not use_dua and dua_on:
                        content = ContentProvider.get_next_dua(
                            last_text=last_text
                        )

                if not content:
                    log_event(
                        "WARN",
                        f"No content available for channel {channel_id}"
                    )
                    continue

                # تجنب تكرار نفس المحتوى إن أمكن
                if content == last_text:
                    alternative = None

                    if use_dua and azkar_on:
                        alternative = ContentProvider.get_next_zikr(
                            category="general",
                            last_text=last_text
                        )
                    elif not use_dua and dua_on:
                        alternative = ContentProvider.get_next_dua(
                            last_text=last_text
                        )

                    if alternative:
                        content = alternative

                # تنسيق الذكر والإيموجي المميز داخل الاقتباس
                safe_content = escape(content)
                msg = (
                    f"<blockquote><b>﴿ {safe_content} "
                    '<tg-emoji emoji-id="4920656542543381470">✨</tg-emoji>'
                    " ﴾ </b></blockquote>"
                )

                # إرسال المحتوى للقناة
                await bot.send_message(
                    chat_id=channel_id,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=bot_link_keyboard()
                )

                # حفظ آخر محتوى بعد نجاح الإرسال فقط
                db.execute(
                    """
                    UPDATE channels
                    SET last_content_text = ?
                    WHERE channel_id = ?
                    """,
                    (content, channel_id)
                )

                log_event(
                    "INFO",
                    f"Published content to {channel_id}"
                )

            except Forbidden as e:
                log_event(
                    "ERROR",
                    f"Forbidden: cannot post to channel {channel_id}",
                    str(e)
                )

            except Exception as e:
                log_event(
                    "ERROR",
                    f"Publish failed: {channel_id}",
                    f"{type(e).__name__}: {e}"
                )

    except Exception as e:
        log_event(
            "ERROR",
            "publish_content_job failed",
            f"{type(e).__name__}: {e}"
        )


async def morning_azkar_job():
    content = ContentProvider.get_next_zikr("morning")

    if not content:
        log_event("WARN", "No morning azkar content available")
        return

    safe_content = escape(content)
    msg = (
        f"🌅 أذكار الصباح\n\n"
        f"<blockquote><b>﴿ {safe_content} "
        '<tg-emoji emoji-id="4920656542543381470">✨</tg-emoji>'
        " ﴾</b></blockquote>"
    )

    channels = db.fetchall(
        """
        SELECT * FROM channels
        WHERE status = 'active'
          AND morning_azkar_enabled = 1
        """
    )

    for ch in channels:
        channel_id = ch["channel_id"]

        try:
            await scheduler.app.bot.send_message(
                chat_id=channel_id,
                text=msg,
                parse_mode=ParseMode.HTML,
                reply_markup=bot_link_keyboard()
            )

            log_event(
                "INFO",
                f"Morning azkar published to {channel_id}"
            )

        except Exception as e:
            log_event(
                "ERROR",
                f"Morning azkar failed: {channel_id}",
                f"{type(e).__name__}: {e}"
            )



async def evening_azkar_job():
    content = ContentProvider.get_next_zikr("evening")
    if not content:
        return

    safe_content = escape(content)
    msg = (
        "🌙 أذكار المساء\n\n"
        f"<blockquote><b>﴿ {safe_content} "
        '<tg-emoji emoji-id="4920656542543381470">✨</tg-emoji>'
        " ﴾</b></blockquote>"
    )

    channels = db.fetchall(
        "SELECT * FROM channels WHERE status = 'active' AND evening_azkar_enabled = 1"
    )

    for ch in channels:
        try:
            await scheduler.app.bot.send_message(
                chat_id=ch["channel_id"],
                text=msg,
                parse_mode=ParseMode.HTML,
                reply_markup=bot_link_keyboard()
            )
        except Exception as e:
            log_event(
                "ERROR",
                f"Evening azkar failed: {ch['channel_id']}",
                str(e)
            )


async def refresh_prayer_times_job():
    locations = set()

    for row in db.fetchall(
        "SELECT DISTINCT city, country FROM prayer_times"
    ):
        locations.add((row["city"], row["country"]))

    for row in db.fetchall(
        "SELECT DISTINCT city, country FROM channels"
    ):
        locations.add((row["city"], row["country"]))

    locations.add((DEFAULT_CITY, DEFAULT_COUNTRY))

    for city, country in locations:
        try:
            times = await PrayerAPI.fetch_prayer_times(city, country)

            if times:
                db.execute(
                    """
                    INSERT OR REPLACE INTO prayer_times
                    (city, country, date, fajr, sunrise, dhuhr, asr, maghrib, isha, method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        city,
                        country,
                        today_str(),
                        times["fajr"],
                        times["sunrise"],
                        times["dhuhr"],
                        times["asr"],
                        times["maghrib"],
                        times["isha"],
                        DEFAULT_METHOD,
                    ),
                )

                log_event(
                    "INFO",
                    f"Prayer times refreshed: {city}"
                )

        except Exception as e:
            log_event(
                "ERROR",
                f"Prayer refresh failed: {city}",
                str(e)
            )


def build_prayer_notification(prayer: str, city: str) -> str:
    """يبني نفس رسالة الصلاة للخاص والجروب والقناة ومعاينة الأدمن."""
    prayer_name = escape(PRAYER_AR.get(prayer, prayer))
    city_name = escape(city or DEFAULT_CITY)
    return (
        '<blockquote>'
        '<b><tg-emoji emoji-id="5785421278148041684">🕌</tg-emoji> '
        f'حان الآن وقت صلاة {prayer_name}</b>\n\n'
        '<b><tg-emoji emoji-id="5391032818111363540">📍</tg-emoji> '
        f'{city_name}</b>\n\n'
        '<b>اللهم أعنّا على ذكرك وشكرك وحسن عبادتك.</b>\n'
        '<b>نسأل الله أن يتقبل منا ومنكم صالح الأعمال '
        '<tg-emoji emoji-id="5346334956022931910">🌟</tg-emoji></b>'
        '</blockquote>'
    )


async def check_prayer_notifications_job():
    if get_setting("prayer_notifications_enabled", "1") != "1":
        return

    now = now_tz()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%d-%m-%Y")

    times = await PrayerAPI.get_times_for_date(
        DEFAULT_CITY,
        DEFAULT_COUNTRY,
        today
    )

    if not times:
        return

    for prayer in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
        pt = times.get(prayer.lower(), "")

        if not pt or pt != current_time:
            continue

        key = f"last_prayer_{prayer}_{today}"

        if get_setting(key, "") == "sent":
            continue

        set_setting(key, "sent")

        msg = build_prayer_notification(
            prayer,
            get_setting("default_city", DEFAULT_CITY)
        )

        channels = db.fetchall(
            "SELECT * FROM channels WHERE status = 'active' AND prayer_notifications_enabled = 1"
        )

        for ch in channels:
            try:
                await scheduler.app.bot.send_message(
                    chat_id=ch["channel_id"],
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=bot_link_keyboard()
                )
            except Exception as e:
                log_event(
                    "ERROR",
                    f"Prayer notify failed: {ch['channel_id']}",
                    str(e)
                )

        users = db.fetchall(
            "SELECT user_id FROM users WHERE notifications_enabled = 1 AND is_blocked = 0"
        )

        for user in users:
            try:
                user_msg = build_prayer_notification(
                    prayer,
                    get_setting("default_city", DEFAULT_CITY)
                )

                await scheduler.app.bot.send_message(
                    chat_id=user["user_id"],
                    text=user_msg,
                    parse_mode=ParseMode.HTML
                )

            except Forbidden:
                db.execute(
                    "UPDATE users SET is_blocked = 1 WHERE user_id = ?",
                    (user["user_id"],)
                )

            except Exception:
                pass




# اسم البوت يُملأ ديناميكياً من Telegram داخل post_init.


def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="أضفني إلى قناتك / مجموعتك",
                url=f"https://t.me/{BOT_USERNAME}?startgroup&admin=delete_messages+restrict_members+invite_users+pin_messages+manage_topics+manage_video_chats+manage_chat",
                api_kwargs={
                    "icon_custom_emoji_id": "6021690418398239007",
                    "style": "primary"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="مواقيت الصلاة",
                callback_data="prayer_times",
                api_kwargs={
                    "icon_custom_emoji_id": "6034898821517940846",
                    "style": "primary"
                }
            ),
            InlineKeyboardButton(
                text="قناة البوت",
                url=get_setting("bot_channel_url", BOT_CHANNEL_URL),
                api_kwargs={
                    "icon_custom_emoji_id": "6021344879689341042",
                    "style": "primary"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="Developer",
                url=get_setting("developer_url", DEVELOPER_URL),
                api_kwargs={
                    "icon_custom_emoji_id": "5217822164362739968",
                    "style": "primary"
                }
            )
        ]
    ]

    if is_admin(user_id):
        rows.append([
            InlineKeyboardButton(
                text="لوحة التحكم",
                callback_data="admin_panel",
                api_kwargs={
                    "icon_custom_emoji_id": "5368324170671202286",
                    "style": "primary"
                }
            )
        ])

    return InlineKeyboardMarkup(rows)





def admin_panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                " الإحصائيات", callback_data="admin_stats",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5972274023634048924"}
            ),
            InlineKeyboardButton(
                "المستخدمون", callback_data="admin_users",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "6021791869820738130"}
            ),
        ],
        [
            InlineKeyboardButton(
                " القنوات", callback_data="admin_channels",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5215668805199473901"}
            ),
            InlineKeyboardButton(
                " الأدوات", callback_data="admin_tools",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "6024065724291488135"}
            ),
        ],
        [
            InlineKeyboardButton(
                " الأدعية", callback_data="admin_duas",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5915813813784944247"}
            ),
            InlineKeyboardButton(
                " الأذكار", callback_data="admin_azkar",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "6037225104654472335"}
            ),
        ],
        [
            InlineKeyboardButton(
                " أذكار الصباح", callback_data="admin_morning",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5467835496312887311"}
            ),
            InlineKeyboardButton(
                " أذكار المساء", callback_data="admin_evening",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "4920552200607892369"}
            ),
        ],
        [
            InlineKeyboardButton(
                " مواقيت الصلاة", callback_data="admin_prayer",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "6034898821517940846"}
            ),
            InlineKeyboardButton(
                " النشر التلقائي", callback_data="admin_posting",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5382194935057372936"}
            ),
        ],
        [
            InlineKeyboardButton(
                " Broadcast", callback_data="admin_broadcast",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "6019110229680068974"}
            ),
            InlineKeyboardButton(
                " Logs", callback_data="admin_logs",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "6021405408663445899"}
            ),
        ],
        [
            InlineKeyboardButton(
                " الرسائل", callback_data="admin_messages",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5346077597287589711"}
            ),
            InlineKeyboardButton(
                " الروابط", callback_data="admin_links",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5972124464282867897"}
            ),
        ],
        [
            InlineKeyboardButton(
                " الإعدادات", callback_data="admin_settings",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5785028554928430512"}
            ),
        ],
        [
            InlineKeyboardButton(
                " رجوع", callback_data="main_menu",
                api_kwargs={"style": "primary", "icon_custom_emoji_id": "5332819376842226496"}
            ),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def back_keyboard(cb: str = "admin_panel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data=cb,
                api_kwargs={
                    "style": "primary",
                    "icon_custom_emoji_id": "5368324170671202302"
                }
            )
        ]
    ])




# ==================== USER HANDLERS ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # لا نعرض قائمة الخاص داخل الجروبات أو القنوات.
    if not update.effective_chat or update.effective_chat.type != ChatType.PRIVATE:
        return

    user = update.effective_user

    db.execute(
        """INSERT INTO users (user_id, username, first_name, last_name, last_seen)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
        username = ?, first_name = ?, last_name = ?, last_seen = datetime('now')""",
        (
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            user.username,
            user.first_name,
            user.last_name,
        ),
    )

    welcome = get_setting(
        "welcome_text",
        "السلام عليكم ورحمة الله وبركاته 🌸\n\nاهلا بك في بوت بـ ـؤت ديـ ـنـ ـي 🤍"
    )

    try:
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=welcome,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user.id),
        )
    except Exception as e:
        print(f"Welcome photo error: {e}")
        await update.message.reply_text(
            text=welcome,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user.id),
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # أمر المساعدة متاح في الخاص فقط
    if not update.effective_chat or update.effective_chat.type != ChatType.PRIVATE:
        return

    help_text = (
        '<tg-emoji emoji-id="6271360715605414557">👑</tg-emoji> '
        '<b>مساعدة بوت بـ ـؤت ديـ ـنـ ـي</b>\n\n'

        '<blockquote>'
        '<b>رفيقك اليومي إلى الطاعة والذكر</b>\n\n'

        '<tg-emoji emoji-id="5305313800688254618">🕌</tg-emoji> '
        '<b>مواقيت الصلاة</b>\n'
        'عرض مواقيت الصلاة اليومية حسب المدينة والدولة.\n\n'

        '<tg-emoji emoji-id="5429327730070009271">🤲</tg-emoji> '
        '<b>الأدعية والأذكار</b>\n'
        'استمتع بمجموعة متنوعة من الأدعية والأذكار المختارة.\n\n'

        '<tg-emoji emoji-id="5346152548761868765">📿</tg-emoji> '
        '<b>النشر التلقائي</b>\n'
        'أضف البوت إلى جروبك أو قناتك كمشرف، وسيبدأ بنشر الأدعية والأذكار تلقائيًا.\n\n'

        '<tg-emoji emoji-id="5323596140732503697">🌙</tg-emoji> '
        '<b>تنبيهات الصلاة</b>\n'
        'ستصلك تنبيهات الصلاة في الوقت المحدد.\n\n'

        '<tg-emoji emoji-id="5346334956022931910">🌿</tg-emoji> '
        '<b>طريقة البدء</b>\n'
        'اضغط /start لفتح القائمة الرئيسية والتحكم في خدمات البوت.'
        '</blockquote>\n\n'

        '<b>نسأل الله أن يجعلنا وإياكم من أهل الذكر والطاعة 🤍</b>'
    )

    await update.message.reply_text(
        text=help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(update.effective_user.id)
    )



async def callback_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    welcome = get_setting(
        "welcome_text",
        "السلام عليكم ورحمة الله وبركاته 🌸\n\nاهلا بك في بوت بـ ـؤت ديـ ـنـ ـي 🤍"
    )

    try:
        await query.message.delete()
    except Exception as e:
        print(f"Delete old message error: {e}")

    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=BANNER_URL,
            caption=welcome,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(
                update.effective_user.id
            ),
        )
    except Exception as e:
        print(f"Welcome photo error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(
                update.effective_user.id
            ),
        )






async def callback_prayer_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    today = today_str()
    times = await PrayerAPI.get_times_for_date(
        DEFAULT_CITY, DEFAULT_COUNTRY, today
    )

    if not times:
        await safe_edit(
            query,
            "⚠️ تعذّر جلب مواقيت الصلاة حالياً.",
            back_keyboard("main_menu")
        )
        return

    now = now_tz()

    lines = [
        '<tg-emoji emoji-id="5784998399963045811">✨</tg-emoji> '
        '<b>مواقيت الصلاة</b> '
        '<tg-emoji emoji-id="5784998399963045811">✨</tg-emoji>',
        '',
        '<tg-emoji emoji-id="5391032818111363540">📍</tg-emoji> '
        '<b>القاهرة | مصر</b>',
        f'<tg-emoji emoji-id="5274055917766202507">📅</tg-emoji> '
        f'{arabic_day_name(now)} • {now.strftime("%d/%m/%Y")}',
        f'<tg-emoji emoji-id="5323596140732503697">🌙</tg-emoji> '
        f'{hijri_date()}',
        '',
        '━━━━━━━━━━━━━━',
    ]

    prayers = [
        ("fajr", "الفجر", "🌄"),
        ("sunrise", "الشروق", "🌅"),
        ("dhuhr", "الظهر", "☀️"),
        ("asr", "العصر", "🌤️"),
        ("maghrib", "المغرب", "🌇"),
        ("isha", "العشاء", "🌙"),
    ]

    for key, name, icon in prayers:
        value = times.get(key, "--:--")
        lines.append(
            f'<tg-emoji emoji-id="5843618381361581907">{icon}</tg-emoji> '
            f'<b>{name}</b>  <code>{format_time(value)}</code>'
        )

    lines.extend([
        '━━━━━━━━━━━━━━',
        '',
        '<tg-emoji emoji-id="5323744179665260252">🤍</tg-emoji> '
        '<b>حيّ على الصلاة</b>',
        '<tg-emoji emoji-id="5346334956022931910">🌿</tg-emoji> '
        '<i>وِرْد | رفقة إلى الطاعة</i>',
    ])

    text = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=" مواقيت اليوم",
                callback_data="prayer_times",
                api_kwargs={
                    "icon_custom_emoji_id": "5785421278148041684",
                    "style": "danger"
                }
            ),
            InlineKeyboardButton(
                text=" رجوع",
                callback_data="main_menu",
                api_kwargs={
                    "icon_custom_emoji_id": "5348224333611277826",
                    "style": "danger"
                }
            ),
        ],
    ])

    await safe_edit(query, text, kb)





async def callback_prayer_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري التحديث...")
    today = today_str()
    db.execute("DELETE FROM prayer_times WHERE city = ? AND country = ? AND date = ?",
               (DEFAULT_CITY, DEFAULT_COUNTRY, today))
    await callback_prayer_times(update, context)


# ==================== ADMIN HANDLERS ====================
async def callback_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.answer("⛔ غير مصرح", show_alert=True)
        return
    await safe_edit(
    query,
    '<b>Admin control panel</b> <tg-emoji emoji-id="6271360715605414557">👑</tg-emoji>',
    admin_panel_keyboard()
)


async def callback_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    stats = {
        "users": db.fetchone("SELECT COUNT(*) as c FROM users")["c"],
        "channels": db.fetchone("SELECT COUNT(*) as c FROM channels")["c"],
        "active_channels": db.fetchone("SELECT COUNT(*) as c FROM channels WHERE status='active'")["c"],
        "duas": db.fetchone("SELECT COUNT(*) as c FROM duas")["c"],
        "azkar": db.fetchone("SELECT COUNT(*) as c FROM azkar")["c"],
        "tools": db.fetchone("SELECT COUNT(*) as c FROM tools")["c"],
        "logs": db.fetchone("SELECT COUNT(*) as c FROM logs")["c"],
    }
    text = (
        "📊 الإحصائيات\n\n"
        f"👥 المستخدمون: {stats['users']}\n"
        f"📢 القنوات: {stats['channels']} (نشطة: {stats['active_channels']})\n"
        f"🤲 الأدعية: {stats['duas']}\n"
        f"📿 الأذكار: {stats['azkar']}\n"
        f"🧩 الأدوات: {stats['tools']}\n"
        f"📋 Logs: {stats['logs']}\n"
        f"⏰ المهام المجدولة: {len(scheduler.jobs) if scheduler else 0}"
    )
    await safe_edit(query, text, back_keyboard())


async def callback_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    total = db.fetchone("SELECT COUNT(*) as c FROM users")["c"]
    active = db.fetchone("SELECT COUNT(*) as c FROM users WHERE is_blocked = 0")["c"]
    text = f"👥 المستخدمون\n\nالإجمالي: {total}\nالنشطون: {active}\nالمحظورون: {total - active}"
    await safe_edit(query, text, back_keyboard())


async def callback_admin_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    channels = db.fetchall("SELECT * FROM channels ORDER BY created_at DESC LIMIT 20")
    if not channels:
        text = "📢 لا توجد قنوات مسجلة بعد.\n\nأضف البوت لقناة كمشرف ليتم تسجيلها تلقائياً."
    else:
        lines = ["📢 القنوات المسجلة:\n"]
        for ch in channels:
            status = "🟢" if ch["status"] == "active" else "🔴"
            title = ch["channel_title"] or "بدون اسم"
            lines.append(f"{status} {title}\nID: {ch['channel_id']}\n")
        text = "\n".join(lines)
    await safe_edit(query, text, back_keyboard())


async def callback_admin_duas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    count = db.fetchone("SELECT COUNT(*) as c FROM duas WHERE enabled=1")["c"]
    total = db.fetchone("SELECT COUNT(*) as c FROM duas")["c"]
    text = f"🤲 إدارة الأدعية\n\nالمفعلة: {count}\nالإجمالي: {total}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تحديث من المصدر", callback_data="admin_duas_refresh")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_admin_duas_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري التحديث...")
    if not is_admin(update.effective_user.id):
        return
    await ContentProvider.refresh_from_source()
    count = db.fetchone("SELECT COUNT(*) as c FROM duas")["c"]
    await safe_edit(query, f"✅ تم التحديث. إجمالي الأدعية: {count}", back_keyboard("admin_duas"))


async def callback_admin_azkar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    total = db.fetchone("SELECT COUNT(*) as c FROM azkar")["c"]
    text = f"📿 إدارة الأذكار\n\nالإجمالي: {total}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 أذكار صباح", callback_data="admin_morning")],
        [InlineKeyboardButton("🌙 أذكار مساء", callback_data="admin_evening")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_admin_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    enabled = get_setting("morning_azkar_enabled", "0") == "1"
    t = get_setting("morning_azkar_time", "07:00")
    text = f"🌅 أذكار الصباح\n\nالحالة: {'🟢 يعمل' if enabled else '🔴 متوقف'}\nالوقت: {t}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ تشغيل" if not enabled else "⏸ إيقاف", callback_data="admin_toggle_morning")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_admin_toggle_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    current = get_setting("morning_azkar_enabled", "0")
    set_setting("morning_azkar_enabled", "0" if current == "1" else "1")
    scheduler.rebuild_all()
    await callback_admin_morning(update, context)


async def callback_admin_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    enabled = get_setting("evening_azkar_enabled", "0") == "1"
    t = get_setting("evening_azkar_time", "18:00")
    text = f"🌙 أذكار المساء\n\nالحالة: {'🟢 يعمل' if enabled else '🔴 متوقف'}\nالوقت: {t}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ تشغيل" if not enabled else "⏸ إيقاف", callback_data="admin_toggle_evening")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_admin_toggle_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    current = get_setting("evening_azkar_enabled", "0")
    set_setting("evening_azkar_enabled", "0" if current == "1" else "1")
    scheduler.rebuild_all()
    await callback_admin_evening(update, context)


async def callback_admin_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    enabled = get_setting("posting_enabled", "1") == "1"
    interval = get_setting("posting_interval", "60")
    dua_on = get_setting("dua_enabled", "1") == "1"
    azkar_on = get_setting("azkar_enabled", "1") == "1"
    try:
        interval = max(1, min(1440, int(interval or 60)))
    except (TypeError, ValueError):
        interval = 60
    all_day = get_setting("posting_all_day", "0") == "1"
    start = get_setting("posting_start", "08:00")
    end = get_setting("posting_end", "23:00")
    window = "طوال اليوم (00:00 - 23:59)" if all_day else f"من {start} إلى {end}"
    text = (
        f"⏱ <b>إدارة النشر التلقائي</b>\n\n"
        f"الحالة: {'🟢 يعمل' if enabled else '🔴 متوقف'}\n"
        f"النافذة الزمنية: <b>{window}</b>\n"
        f"الفاصل بين المنشورات: <b>{interval} دقيقة</b>\n"
        f"الأدعية: {'🟢 مفعلة' if dua_on else '🔴 متوقفة'}\n"
        f"الأذكار: {'🟢 مفعلة' if azkar_on else '🔴 متوقفة'}\n\n"
        "يمكنك تحديد بداية ونهاية مخصصة، حتى لو كانت الفترة تتجاوز منتصف الليل."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ تشغيل" if not enabled else "⏸ إيقاف", callback_data="admin_toggle_posting")],
        [InlineKeyboardButton("🕐 تغيير بداية النشر", callback_data="admin_change_start")],
        [InlineKeyboardButton("🕚 تغيير نهاية النشر", callback_data="admin_change_end")],
        [InlineKeyboardButton("☀️ طوال اليوم" if not all_day else "🌙 استخدام فترة محددة", callback_data="admin_toggle_all_day")],
        [InlineKeyboardButton("⏱ تغيير الفاصل", callback_data="admin_change_interval")],
        [InlineKeyboardButton("🤲 تشغيل/إيقاف الأدعية", callback_data="admin_toggle_dua")],
        [InlineKeyboardButton("📿 تشغيل/إيقاف الأذكار", callback_data="admin_toggle_azkar")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_admin_toggle_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    current = get_setting("posting_enabled", "1")
    set_setting("posting_enabled", "0" if current == "1" else "1")
    scheduler.rebuild_all()
    await callback_admin_posting(update, context)


async def callback_admin_toggle_dua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    current = get_setting("dua_enabled", "1")
    set_setting("dua_enabled", "0" if current == "1" else "1")
    await callback_admin_posting(update, context)


async def callback_admin_toggle_azkar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    current = get_setting("azkar_enabled", "1")
    set_setting("azkar_enabled", "0" if current == "1" else "1")
    await callback_admin_posting(update, context)


async def callback_admin_change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 دقيقة", callback_data="set_interval_1"),
         InlineKeyboardButton("5 دقائق", callback_data="set_interval_5")],
        [InlineKeyboardButton("10 دقائق", callback_data="set_interval_10"),
         InlineKeyboardButton("15 دقيقة", callback_data="set_interval_15")],
        [InlineKeyboardButton("30 دقيقة", callback_data="set_interval_30"),
         InlineKeyboardButton("ساعة", callback_data="set_interval_60")],
        [InlineKeyboardButton("✍️ إدخال مدة مخصصة", callback_data="admin_custom_interval")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_posting")],
    ])
    await safe_edit(query, "⏱ اختر الفاصل بين المنشورات أو أدخل قيمة من 1 إلى 1440 دقيقة:", kb)


async def callback_admin_custom_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data["posting_input"] = "interval"
    await safe_edit(query, "✍️ أرسل الفاصل بالدقائق (من 1 إلى 1440):\n\nأرسل /cancel للإلغاء.", back_keyboard("admin_posting"))


async def callback_admin_change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    field = "start" if query.data == "admin_change_start" else "end"
    context.user_data["posting_input"] = field
    label = "بداية" if field == "start" else "نهاية"
    await safe_edit(query, f"🕐 أرسل وقت {label} بصيغة 24 ساعة (HH:MM)، مثال: 08:30\n\nأرسل /cancel للإلغاء.", back_keyboard("admin_posting"))


async def callback_admin_toggle_all_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    current = get_setting("posting_all_day", "0")
    set_setting("posting_all_day", "0" if current == "1" else "1")
    scheduler.rebuild_all()
    await callback_admin_posting(update, context)


async def handle_posting_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get("posting_input")
    if not field or not is_admin(update.effective_user.id):
        return
    value = update.message.text.strip()
    if value == "/cancel":
        context.user_data.pop("posting_input", None)
        await update.message.reply_text("تم الإلغاء")
        return

    if field == "interval":
        try:
            minutes = int(value)
            if not 1 <= minutes <= 1440:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ أدخل رقمًا صحيحًا بين 1 و1440 دقيقة.")
            return
        set_setting("posting_interval", str(minutes))
        context.user_data.pop("posting_input", None)
        scheduler.rebuild_all()
        await update.message.reply_text(f"✅ تم ضبط الفاصل على {minutes} دقيقة.")
        return

    try:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        normalized = f"{hour:02d}:{minute:02d}"
    except (TypeError, ValueError):
        await update.message.reply_text("❌ الصيغة غير صحيحة. استخدم HH:MM مثل 08:30.")
        return

    set_setting("posting_start" if field == "start" else "posting_end", normalized)
    set_setting("posting_all_day", "0")
    context.user_data.pop("posting_input", None)
    scheduler.rebuild_all()
    label = "بداية" if field == "start" else "نهاية"
    await update.message.reply_text(f"✅ تم ضبط {label} النشر على {normalized}.")


async def callback_set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    val = query.data.replace("set_interval_", "")
    set_setting("posting_interval", val)
    scheduler.rebuild_all()
    await safe_edit(query, f"✅ تم تعيين المدة: {val} دقيقة", back_keyboard("admin_posting"))


async def callback_admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    rows = db.fetchall("SELECT * FROM logs ORDER BY created_at DESC LIMIT 15")
    if not rows:
        text = "📋 لا توجد سجلات."
    else:
        lines = ["📋 آخر السجلات:\n"]
        for r in rows:
            lines.append(f"[{r['level']}] {r['message'][:60]}")
        text = "\n".join(lines)
    await safe_edit(query, text, back_keyboard())


async def callback_admin_prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    text = (
        f"🕌 إعدادات مواقيت الصلاة\n\n"
        f"المدينة: {get_setting('default_city', DEFAULT_CITY)}\n"
        f"الدولة: {get_setting('default_country', DEFAULT_COUNTRY)}\n"
        f"طريقة الحساب: {PRAYER_METHODS.get(get_setting('default_method', '5'), 'غير محددة')}\n"
        f"المنطقة الزمنية: {get_setting('default_timezone', DEFAULT_TZ)}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 تست رسالة الصلاة", callback_data="admin_test_prayer")],
        [InlineKeyboardButton("🔄 تحديث المواقيت", callback_data="admin_prayer_refresh")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_admin_test_prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري إرسال رسالة الاختبار...")
    if not is_admin(update.effective_user.id):
        return

    test_msg = build_prayer_notification(
        "Dhuhr",
        get_setting("default_city", DEFAULT_CITY)
    )

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=test_msg,
        parse_mode=ParseMode.HTML,
        reply_markup=bot_link_keyboard()
    )
    await safe_edit(
        query,
        "✅ تم إرسال تست رسالة صلاة الظهر إلى الخاص بك.",
        back_keyboard("admin_prayer")
    )


async def callback_admin_prayer_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري التحديث...")
    if not is_admin(update.effective_user.id):
        return
    await refresh_prayer_times_job()
    await safe_edit(query, "✅ تم تحديث مواقيت الصلاة", back_keyboard("admin_prayer"))


async def callback_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await safe_edit(query, "📨 Broadcast\n\nأرسل الرسالة التي تريد بثها:", back_keyboard())
    context.user_data["awaiting_broadcast"] = True


async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_broadcast"):
        return
    if not is_admin(update.effective_user.id):
        return
    context.user_data["awaiting_broadcast"] = False
    msg = update.message.text
    users = db.fetchall("SELECT user_id FROM users WHERE is_blocked = 0")
    sent = 0
    failed = 0
    await update.message.reply_text(f"⏳ جاري الإرسال لـ {len(users)} مستخدم...")
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["user_id"], text=msg)
            sent += 1
            await asyncio.sleep(0.05)
        except Forbidden:
            db.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (u["user_id"],))
            failed += 1
        except Exception:
            failed += 1
    db.execute(
        "INSERT INTO broadcasts (message, target, sent_count, failed_count) VALUES (?, 'users', ?, ?)",
        (msg, sent, failed),
    )
    await update.message.reply_text(f"✅ تم الإرسال\nنجح: {sent}\nفشل: {failed}")


async def callback_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("رسالة الترحيب", callback_data="edit_msg_welcome")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, "📝 إدارة الرسائل", kb)


async def callback_edit_msg_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await safe_edit(query, "أرسل نص رسالة الترحيب الجديد:\n\n(أرسل /cancel للإلغاء)",
                    back_keyboard("admin_messages"))
    context.user_data["edit_welcome"] = True


async def handle_edit_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("edit_welcome"):
        return
    if not is_admin(update.effective_user.id):
        return
    context.user_data["edit_welcome"] = False
    set_setting("welcome_text", update.message.text)
    await update.message.reply_text("✅ تم تحديث رسالة الترحيب")


async def callback_admin_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    text = (
        "🔗 إدارة الروابط\n\n"
        f"قناة البوت: {get_setting('bot_channel_url', 'غير محدد')}\n"
        f"المطور: {get_setting('developer_url', 'غير محدد')}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("تعديل قناة البوت", callback_data="edit_link_channel")],
        [InlineKeyboardButton("تعديل رابط المطور", callback_data="edit_link_dev")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, text, kb)


async def callback_edit_link_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await safe_edit(query, "أرسل رابط قناة البوت الجديد:\n\n(أرسل /cancel للإلغاء)",
                    back_keyboard("admin_links"))
    context.user_data["edit_link"] = "bot_channel_url"


async def callback_edit_link_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await safe_edit(query, "أرسل رابط المطور الجديد:\n\n(أرسل /cancel للإلغاء)",
                    back_keyboard("admin_links"))
    context.user_data["edit_link"] = "developer_url"


async def handle_edit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("edit_link")
    if not key:
        return
    if not is_admin(update.effective_user.id):
        return
    txt = update.message.text.strip()
    if txt == "/cancel":
        context.user_data.pop("edit_link", None)
        await update.message.reply_text("تم الإلغاء")
        return
    set_setting(key, txt)
    context.user_data.pop("edit_link", None)
    await update.message.reply_text("✅ تم تحديث الرابط")


async def callback_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    text = (
        "⚙️ الإعدادات العامة\n\n"
        f"المدينة: {get_setting('default_city', DEFAULT_CITY)}\n"
        f"الدولة: {get_setting('default_country', DEFAULT_COUNTRY)}\n"
        f"المنطقة الزمنية: {get_setting('default_timezone', DEFAULT_TZ)}\n"
        f"طريقة الحساب: {get_setting('default_method', '5')}"
    )
    await safe_edit(query, text, back_keyboard())


async def callback_admin_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    tools = db.fetchall("SELECT * FROM tools ORDER BY sort_order")
    lines = ["🧩 إدارة الأدوات\n"]
    if tools:
        for t in tools:
            status = "🟢" if t["enabled"] else "🔴"
            lines.append(f"{status} {t['name']}")
    else:
        lines.append("لا توجد أدوات ديناميكية بعد.")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة أداة", callback_data="admin_add_tool")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")],
    ])
    await safe_edit(query, "\n".join(lines), kb)


async def callback_admin_add_tool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await safe_edit(query, "➕ أرسل اسم الأداة:\n\n(أرسل /cancel للإلغاء)",
                    back_keyboard("admin_tools"))
    context.user_data["add_tool_step"] = "name"


async def handle_add_tool_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "add_tool_step" not in context.user_data:
        return
    if not is_admin(update.effective_user.id):
        return
    step = context.user_data["add_tool_step"]
    text = update.message.text.strip()
    if text == "/cancel":
        context.user_data.pop("add_tool_step", None)
        await update.message.reply_text("تم الإلغاء")
        return
    if step == "name":
        context.user_data["tool_name"] = text
        context.user_data["add_tool_step"] = "button_text"
        await update.message.reply_text("📝 أرسل نص الزر:")
    elif step == "button_text":
        context.user_data["tool_button"] = text
        context.user_data["add_tool_step"] = "url"
        await update.message.reply_text("🔗 أرسل الرابط (أو /skip):")
    elif step == "url":
        url = None if text == "/skip" else text
        db.execute(
            "INSERT INTO tools (name, button_text, url, type, enabled, sort_order) VALUES (?, ?, ?, 'link', 1, 100)",
            (context.user_data["tool_name"], context.user_data["tool_button"], url),
        )
        name = context.user_data["tool_name"]
        context.user_data.pop("add_tool_step", None)
        await update.message.reply_text(f"✅ تمت إضافة الأداة: {name}")


# ==================== CHANNEL HANDLERS ====================
async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.my_chat_member
    if not cm:
        return

    chat = cm.chat
    new_status = cm.new_chat_member.status
    supported_chat = chat.type in (ChatType.CHANNEL, ChatType.GROUP, ChatType.SUPERGROUP)
    if not supported_chat:
        return

    added_by = cm.from_user.id if cm.from_user else 0
    existing = db.fetchone("SELECT * FROM channels WHERE channel_id = ?", (chat.id,))

    if new_status == "administrator":
        if not existing:
            db.execute(
                """INSERT INTO channels
                (channel_id, channel_username, channel_title, owner_id, status)
                VALUES (?, ?, ?, ?, 'active')""",
                (chat.id, chat.username, chat.title, added_by),
            )
            log_event("INFO", f"Channel activated as administrator: {chat.title} ({chat.id})")
        else:
            db.execute("UPDATE channels SET status = 'active' WHERE channel_id = ?", (chat.id,))

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    "✅ تم تفعيل بوت بـ ـؤت ديـ ـنـ ـي بنجاح\n\n"
                    "سيبدأ البوت بنشر الأدعية والأذكار تلقائياً، "
                    "وسيتم إرسال تنبيهات الصلاة."
                ),
                reply_markup=bot_link_keyboard(),
            )
        except Exception:
            logger.warning("Could not send activation message to %s", chat.id)

    elif new_status == "member":
        # لا نعتبر البوت فعالاً ولا نبدأ النشر قبل منحه صلاحيات الأدمن.
        if not existing:
            db.execute(
                """INSERT INTO channels
                (channel_id, channel_username, channel_title, owner_id, status)
                VALUES (?, ?, ?, ?, 'inactive')""",
                (chat.id, chat.username, chat.title, added_by),
            )
        else:
            db.execute("UPDATE channels SET status = 'inactive' WHERE channel_id = ?", (chat.id,))

        warning = (
            "⚠️ لا يمكن لبوت بـ ـؤت ديـ ـنـ ـي النشر هنا حالياً\n\n"
            "من فضلك ارفع البوت إلى مشرف (Admin) مع صلاحية نشر الرسائل "
            "حتى يعمل النشر التلقائي."
        )
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=warning,
                reply_markup=promote_bot_keyboard(chat.type),
            )
        except Exception:
            # في القنوات أو المجموعات التي تمنع الإرسال، نرسل التنبيه لمن أضاف البوت إن أمكن.
            if added_by:
                try:
                    await context.bot.send_message(
                        chat_id=added_by,
                        text=f"{warning}\n\nاسم المكان: {chat.title or chat.id}",
                        reply_markup=promote_bot_keyboard(chat.type),
                    )
                except Exception:
                    pass
        log_event("WARN", f"Bot added without admin rights: {chat.title} ({chat.id})")

    elif new_status in ("left", "kicked"):
        db.execute("UPDATE channels SET status = 'inactive' WHERE channel_id = ?", (chat.id,))
        log_event("INFO", f"Channel removed: {chat.id}")

# Bevndary
# ==================== INIT ====================
scheduler: Optional[TartilScheduler] = None


async def post_init(app: Application):
    global scheduler, BOT_USERNAME
    me = await app.bot.get_me()
    BOT_USERNAME = me.username
    logger.info(f"Bot username: @{me.username}")

    await app.bot.set_my_commands([
        BotCommand("start", "القائمة الرئيسية"),
        BotCommand("help", "المساعدة"),
    ])

    await ContentProvider.refresh_from_source()

    scheduler = TartilScheduler(app)
    scheduler.start()
    scheduler.rebuild_all()
    logger.info("Bot initialized successfully")

async def post_shutdown(app: Application):
    if scheduler:
        scheduler.shutdown()
    db.close()
    logger.info("Bot shut down")


# ==================== MAIN ====================
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required!")
        sys.exit(1)

    db.connect()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Commands
    # أوامر واجهة المستخدم في الخاص فقط، ولا تستجيب داخل الجروبات أو القنوات.
    app.add_handler(CommandHandler("start", cmd_start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", cmd_help, filters=filters.ChatType.PRIVATE))

    # User callbacks
    app.add_handler(CallbackQueryHandler(callback_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(callback_prayer_times, pattern="^prayer_times$"))
    app.add_handler(CallbackQueryHandler(callback_prayer_refresh, pattern="^prayer_refresh$"))

    # Admin callbacks
    app.add_handler(CallbackQueryHandler(callback_admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(callback_admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(callback_admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(callback_admin_channels, pattern="^admin_channels$"))
    app.add_handler(CallbackQueryHandler(callback_admin_duas, pattern="^admin_duas$"))
    app.add_handler(CallbackQueryHandler(callback_admin_duas_refresh, pattern="^admin_duas_refresh$"))
    app.add_handler(CallbackQueryHandler(callback_admin_azkar, pattern="^admin_azkar$"))
    app.add_handler(CallbackQueryHandler(callback_admin_morning, pattern="^admin_morning$"))
    app.add_handler(CallbackQueryHandler(callback_admin_toggle_morning, pattern="^admin_toggle_morning$"))
    app.add_handler(CallbackQueryHandler(callback_admin_evening, pattern="^admin_evening$"))
    app.add_handler(CallbackQueryHandler(callback_admin_toggle_evening, pattern="^admin_toggle_evening$"))
    app.add_handler(CallbackQueryHandler(callback_admin_posting, pattern="^admin_posting$"))
    app.add_handler(CallbackQueryHandler(callback_admin_toggle_posting, pattern="^admin_toggle_posting$"))
    app.add_handler(CallbackQueryHandler(callback_admin_toggle_dua, pattern="^admin_toggle_dua$"))
    app.add_handler(CallbackQueryHandler(callback_admin_toggle_azkar, pattern="^admin_toggle_azkar$"))
    app.add_handler(CallbackQueryHandler(callback_admin_change_interval, pattern="^admin_change_interval$"))
    app.add_handler(CallbackQueryHandler(callback_admin_custom_interval, pattern="^admin_custom_interval$"))
    app.add_handler(CallbackQueryHandler(callback_admin_change_time, pattern="^admin_change_(start|end)$"))
    app.add_handler(CallbackQueryHandler(callback_admin_toggle_all_day, pattern="^admin_toggle_all_day$"))
    app.add_handler(CallbackQueryHandler(callback_set_interval, pattern="^set_interval_"))
    app.add_handler(CallbackQueryHandler(callback_admin_logs, pattern="^admin_logs$"))
    app.add_handler(CallbackQueryHandler(callback_admin_prayer, pattern="^admin_prayer$"))
    app.add_handler(CallbackQueryHandler(callback_admin_test_prayer, pattern="^admin_test_prayer$"))
    app.add_handler(CallbackQueryHandler(callback_admin_prayer_refresh, pattern="^admin_prayer_refresh$"))
    app.add_handler(CallbackQueryHandler(callback_admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(callback_admin_settings, pattern="^admin_settings$"))
    app.add_handler(CallbackQueryHandler(callback_admin_tools, pattern="^admin_tools$"))
    app.add_handler(CallbackQueryHandler(callback_admin_add_tool, pattern="^admin_add_tool$"))
    app.add_handler(CallbackQueryHandler(callback_admin_messages, pattern="^admin_messages$"))
    app.add_handler(CallbackQueryHandler(callback_edit_msg_welcome, pattern="^edit_msg_welcome$"))
    app.add_handler(CallbackQueryHandler(callback_admin_links, pattern="^admin_links$"))
    app.add_handler(CallbackQueryHandler(callback_edit_link_channel, pattern="^edit_link_channel$"))
    app.add_handler(CallbackQueryHandler(callback_edit_link_dev, pattern="^edit_link_dev$"))

    # Message handlers (different groups to avoid conflicts)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_welcome), group=2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_link), group=3)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_tool_input), group=4)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_posting_input), group=5)

    # Channel/Group member updates
    app.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    logger.info("Starting Tartil Bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
