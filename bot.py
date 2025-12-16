import asyncio
import json
import hashlib
from playwright.async_api import async_playwright
from telegram import Bot

# ================= CONFIG =================
BOT_TOKEN = "7643831340:AAGieuPJND4MekAutSf3xzta1qdoKo5mbZU"
TARGET_CHAT = "@SwissWatch9585"

MARKET_URL = "https://marketapp.ws/gifts/"
CHECK_INTERVAL = 15
# ========================================

bot = Bot(BOT_TOKEN)

# Load seen gifts
try:
    with open("seen.json", "r") as f:
        SEEN = set(json.load(f))
except:
    SEEN = set()

def uid(data: str):
    return hashlib.md5(data.encode()).hexdigest()

async def send_alert(name, price, backdrop, link):
    msg = f"""
🎁 <b>Gift Found!</b>

⭐ <b>Price:</b> {price}

🎁 <b>{name}</b>
🎨 <b>Backdrop:</b> {backdrop}

🔗 <a href="{link}">Gift Link</a>
"""
    await bot.send_message(
        chat_id=TARGET_CHAT,
        text=msg,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def check_market():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(MARKET_URL, timeout=60000)

        # Wait till gifts load
        await page.wait_for_selector(".gift-card", timeout=60000)

        cards = await page.query_selector_all(".gift-card")

        for card in cards:
            try:
                name = await card.query_selector_eval(
                    ".gift-title", "el => el.innerText"
                )
                price = await card.query_selector_eval(
                    ".gift-price", "el => el.innerText"
                )
                backdrop = await card.query_selector_eval(
                    ".gift-backdrop", "el => el.innerText"
                )
                link = await card.query_selector_eval(
                    "a", "el => el.href"
                )

                key = uid(name + price + backdrop)
                if key in SEEN:
                    continue

                SEEN.add(key)
                await send_alert(name, price, backdrop, link)

            except:
                continue

        await browser.close()

        with open("seen.json", "w") as f:
            json.dump(list(SEEN), f)

async def main():
    print("✅ Telegram Gift Watcher Bot Started")
    while True:
        try:
            await check_market()
        except Exception as e:
            print("Error:", e)
        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())
