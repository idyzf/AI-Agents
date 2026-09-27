import os
import discord
from qwen_agent.agents import Assistant


DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]


llm_cfg = {
    "model": os.environ.get("MODEL_NAME", "qwen2.5:7b-instruct"),
    "model_server": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    "api_key": "EMPTY",
}

bot_agent = Assistant(
    llm=llm_cfg,
    function_list=[],  # add tools here later (e.g. MCP servers) — code_interpreter
                       # is skipped since it needs Docker-in-Docker to sandbox code,
                       # which isn't set up in this container
)

intents = discord.Intents.default()
intents.message_content = True  # required to read message text; must also be
                                 # enabled in the Discord Developer Portal

client = discord.Client(intents=intents)

# Very simple per-channel memory so replies have context. Not persisted across
# restarts — swap for a real store later if you want history to survive reboots.
conversations = {}
MAX_HISTORY_MESSAGES = 20


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id: {client.user.id})")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = client.user in message.mentions

    # In servers, only respond when tagged (@YourBot ...). In DMs, always respond.
    if not is_dm and not is_mentioned:
        return

    user_text = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not user_text:
        return

    channel_id = message.channel.id
    history = conversations.setdefault(channel_id, [])
    history.append({"role": "user", "content": user_text})

    async with message.channel.typing():
        try:
            final_response = []
            for response in bot_agent.run(messages=history):
                final_response = response
            reply_text = final_response[-1]["content"] if final_response else "(no response)"
        except Exception as e:
            reply_text = f"Something went wrong talking to the model: {e}"

        history.append({"role": "assistant", "content": reply_text})
        conversations[channel_id] = history[-MAX_HISTORY_MESSAGES:]

        # Discord caps messages at ~2000 chars; split long replies into chunks.
        chunks = [reply_text[i:i + 1900] for i in range(0, len(reply_text), 1900)] or ["(empty response)"]
        for chunk in chunks:
            await message.channel.send(chunk)


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)