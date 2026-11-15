import asyncio
import os
import urllib.request

import discord

from agent import AGENTS, MODEL_NAME, OLLAMA_BASE_URL, make_agent, run_agent

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

# Optional: comma-separated Discord user IDs allowed to use the bot. Empty means
# anyone who can message it. Set it so others can't use your Mac's GPU.
ALLOWED_USER_IDS = {
    int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x
}

MAX_HISTORY_MESSAGES = 20

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


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id: {client.user.id})")
    print(f"Agentes disponíveis: {', '.join(AGENTS)}")


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

    # Discord caps messages at 2000 chars.
    for i in range(0, len(reply_text), 1900):
        await message.channel.send(reply_text[i:i + 1900])


if __name__ == "__main__":
    check_ollama()
    client.run(DISCORD_TOKEN)
