import asyncio
import json
import hashlib
import os
from playwright.async_api import async_playwright
from telegram import Bot

# ============ CONFIG (ENV) ============
BOT_TOKEN = os.getenv("7643831340:AAGieuPJND4MekAutSf3xzta1qdoKo5mbZU")
TARGET_CHAT = os.getenv("@SwissWatch9585")

MARKET_URL = "https://marketapp.ws/gifts/"
CHECK_INTERVAL = 20
# ====================================

bot = Bot(BOT_TOKEN)

# Load seen gifts
try:
    with open("seen.json", "r") as f:
        SEEN = set(json.load(f))
except:
    SEEN = set()

def make_uid(text):
    return hashlib.md5(text.encode()).hexdigest()

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

async def scan_market():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(MARKET_URL, timeout=60000)

        # Page fully load
        await page.wait_for_timeout(5000)

        cards = await page.query_selector_all("a")

        for card in cards:
            try:
                text = await card.inner_text()
                if "Price" not in text:
                    continue

                link = await card.get_attribute("href")
                lines = [l.strip() for l in text.splitlines() if l.strip()]

                name = lines[0]
                price = next((l.replace("Price:", "").strip() for l in lines if "Price" in l), "N/A")
                backdrop = next((l.replace("Backdrop:", "").strip() for l in lines if "Backdrop" in l), "Unknown")

                uid = make_uid(name + price + backdrop)
                if uid in SEEN:
                    continue

                SEEN.add(uid)
                await send_alert(name, price, backdrop, link)

            except:
                continue

        await browser.close()

        with open("seen.json", "w") as f:
            json.dump(list(SEEN), f)

async def main():
    print("✅ Gift Watcher Bot Running")
    while True:
        try:
            await scan_market()
        except Exception as e:
            print("ERROR:", e)
        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())
