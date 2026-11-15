import asyncio
import datetime as dt
import os
import urllib.request

import discord
from discord.ext import tasks

import briefing
from agent import AGENTS, MODEL_NAME, OLLAMA_BASE_URL, make_agent, run_agent

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

# Optional: comma-separated Discord user IDs allowed to use the bot. Empty means
# anyone who can message it. Set it so others can't use your Mac's GPU.
ALLOWED_USER_IDS = {
    int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x
}

MAX_HISTORY_MESSAGES = 20

# Who gets the calendar/email briefings by DM. Defaults to the owner of the
# Discord application (you), so nobody else can ever receive or request them.
OWNER_USER_ID = int(os.environ["OWNER_USER_ID"]) if os.environ.get("OWNER_USER_ID") else None
BRIEFING_HOUR, BRIEFING_MINUTE = (int(x) for x in os.environ.get("BRIEFING_TIME", "07:00").split(":"))
BRIEFING_COMMANDS = {
    "!hoje": lambda: [f"{briefing._safe(briefing.events_today)}\n\n{briefing._safe(briefing.emails_summary)}"],
    "!semana": lambda: [briefing._safe(briefing.events_week)],
    "!emails": lambda: [briefing._safe(briefing.emails_summary)],
    "!bomdia": briefing.morning_messages,
}

agents = {name: make_agent(name) for name in AGENTS}

intents = discord.Intents.default()
intents.message_content = True  # must also be enabled in the Discord Developer Portal
client = discord.Client(intents=intents)

# Per-channel, per-agent memory. In RAM only: cleared on restart.
conversations: dict[tuple[int, str], list] = {}
# One request at a time so a 16 GB Mac isn't overloaded by parallel generations.
model_lock = asyncio.Lock()


def check_ollama() -> None:
    url = OLLAMA_BASE_URL.rstrip("/") + "/models"
    try:
        urllib.request.urlopen(url, timeout=5)
        print(f"Ollama OK em {OLLAMA_BASE_URL} (modelo: {MODEL_NAME})")
    except Exception as e:
        print(
            f"AVISO: não consegui falar com o Ollama em {OLLAMA_BASE_URL} ({e}). "
            "Verifique se o Ollama está aberto no Mac e se o modelo foi baixado "
            f"com: ollama pull {MODEL_NAME}"
        )


def parse_command(text: str) -> tuple[str, str]:
    """'!nome mensagem' picks an agent; anything else goes to 'default'."""
    if text.startswith("!"):
        name, _, rest = text[1:].partition(" ")
        if name in AGENTS:
            return name, rest.strip()
    return "default", text


async def send_chunks(channel, text: str) -> None:
    # Discord caps messages at 2000 chars.
    for i in range(0, len(text), 1900):
        await channel.send(text[i:i + 1900])


async def build_messages(fn) -> list[str]:
    async with model_lock:
        return await asyncio.to_thread(fn)


@tasks.loop(time=dt.time(BRIEFING_HOUR, BRIEFING_MINUTE, tzinfo=briefing.TZ))
async def morning_briefing():
    owner = await client.fetch_user(OWNER_USER_ID)
    for text in await build_messages(briefing.morning_messages):
        await send_chunks(owner, text)
    print(f"Resumo da manhã enviado ({dt.datetime.now(briefing.TZ):%d/%m %H:%M})")


@client.event
async def on_ready():
    global OWNER_USER_ID
    print(f"Logged in as {client.user} (id: {client.user.id})")
    print(f"Agentes disponíveis: {', '.join(AGENTS)}")
    if OWNER_USER_ID is None:
        OWNER_USER_ID = (await client.application_info()).owner.id
    if not morning_briefing.is_running():
        morning_briefing.start()
        print(f"Resumos agendados para {BRIEFING_HOUR:02d}:{BRIEFING_MINUTE:02d} ({briefing.TZ}), DM para {OWNER_USER_ID}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user or message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    if not is_dm and client.user not in message.mentions:
        return  # in servers, only respond when tagged
    if ALLOWED_USER_IDS and message.author.id not in ALLOWED_USER_IDS:
        return

    text = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()
    if not text:
        return

    if text in BRIEFING_COMMANDS:
        # Your calendar and emails: only for you, and only in a private DM.
        if message.author.id != OWNER_USER_ID or not is_dm:
            await message.channel.send("Esse comando só funciona na DM do dono do bot.")
            return
        async with message.channel.typing():
            for part in await build_messages(BRIEFING_COMMANDS[text]):
                await send_chunks(message.channel, part)
        return

    if text == "!reset":
        for key in [k for k in conversations if k[0] == message.channel.id]:
            del conversations[key]
        await message.channel.send("Memória desta conversa apagada.")
        return

    agent_name, user_text = parse_command(text)
    if not user_text:
        return

    key = (message.channel.id, agent_name)
    history = conversations.setdefault(key, [])
    history.append({"role": "user", "content": user_text})

    async with message.channel.typing():
        try:
            async with model_lock:
                # run_agent is blocking; run it in a thread so the Discord
                # connection stays alive while the model is generating.
                reply_text = await asyncio.to_thread(run_agent, agents[agent_name], list(history))
        except Exception as e:
            history.pop()
            await message.channel.send(f"Erro ao falar com o modelo: {e}")
            return

    history.append({"role": "assistant", "content": reply_text})
    conversations[key] = history[-MAX_HISTORY_MESSAGES:]

    await send_chunks(message.channel, reply_text)


if __name__ == "__main__":
    check_ollama()
    client.run(DISCORD_TOKEN)
