from pyrogram import Client, filters

app = Client(
    "userbot",
    api_id=24526311,
    api_hash="717d5df262e474f88d86c537a787c98d"
)

@app.on_message(filters.me & filters.regex(r"^🎲$"))
async def send_dice(client, message):
    msg = await message.reply_dice()
    result = msg.dice.value
    print(f"🎲 Dice Result: {result}")
    await client.send_message("me", f"🎲 Dice Result: {result}")

app.run()
