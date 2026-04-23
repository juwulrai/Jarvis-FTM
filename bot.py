import discord
import os
import google.generativeai as genai
from collections import defaultdict

# ── Config ────────────────────────────────────────────────
DISCORD_TOKEN  = os.environ.get("DISCORD_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
BOT_NAME       = "Jarvis"

# How many messages to remember per channel
MEMORY_LIMIT = 20

# ── Jarvis Personality ────────────────────────────────────
SYSTEM_PROMPT = """
You are Jarvis, a highly intelligent and witty AI assistant inside a Discord server.
You were created to assist the server members with anything they need.

Your personality:
- Speaks with confidence and a touch of dry humor
- Occasionally calls users "sir" or "ma'am" like the real Jarvis from Iron Man
- Very helpful but also a little sarcastic when appropriate
- Responds in the same language the user uses (Filipino or English)
- Keeps responses concise — no unnecessary long paragraphs
- Uses Discord markdown formatting when helpful (bold, code blocks, etc.)

You are NOT a generic AI assistant. You are JARVIS. Act like it.
"""

# ── Gemini Setup ──────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT,
)

# ── Memory Storage (per channel) ─────────────────────────
conversation_history = defaultdict(list)

def get_ai_response(channel_id: int, user_message: str) -> str:
    history = conversation_history[channel_id]

    try:
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message)
        reply = response.text

        # Save to memory
        history.append({"role": "user",  "parts": [user_message]})
        history.append({"role": "model", "parts": [reply]})

        # Trim memory to limit
        if len(history) > MEMORY_LIMIT * 2:
            conversation_history[channel_id] = history[-(MEMORY_LIMIT * 2):]

        return reply

    except Exception as e:
        return f"My apologies, sir. I encountered an error: `{str(e)}`"


# ── Discord Bot Setup ─────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"✅ {BOT_NAME} is online as {client.user}")
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your commands, sir."
        )
    )


@client.event
async def on_message(message):
    # Ignore bots
    if message.author.bot:
        return

    # Clear memory command
    if message.content.lower() == "!forget":
        conversation_history[message.channel.id] = []
        await message.reply("Memory cleared, sir. Starting fresh.")
        return

    # Jarvis responds when mentioned, DM, or message starts with "jarvis"
    is_mentioned  = client.user in message.mentions
    is_dm         = isinstance(message.channel, discord.DMChannel)
    starts_jarvis = message.content.lower().startswith("jarvis")

    if not (is_mentioned or is_dm or starts_jarvis):
        return

    # Clean the message
    user_input = message.content
    user_input = user_input.replace(f"<@{client.user.id}>", "").strip()
    if user_input.lower().startswith("jarvis"):
        user_input = user_input[6:].strip()

    if not user_input:
        await message.reply("At your service, sir. What do you need?")
        return

    # Show typing while generating
    async with message.channel.typing():
        reply = get_ai_response(message.channel.id, user_input)

    # Split long messages (Discord 2000 char limit)
    if len(reply) > 1900:
        chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
        for chunk in chunks:
            await message.reply(chunk)
    else:
        await message.reply(reply)


# ── Run ───────────────────────────────────────────────────
client.run(DISCORD_TOKEN)
