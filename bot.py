from pyrogram import Client, filters

app = Client(
    "userbot",
    api_id=24526311,          
    api_hash="717d5df262e474f88d86c537a787c98d",  
)

@app.on_message(filters.command("dice") & filters.me)
async def dice_handler(client, message):
    # dice send
    msg = await message.reply_dice()

    # dice ka result
    result = msg.dice.value

    # heroku logs me print
    print(f"🎲 Dice Result: {result}")

    # optional: apne saved message me bhejna ho toh
    await client.send_message("me", f"🎲 Dice Result: {result}")

app.run()
